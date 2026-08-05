"""RBAC 权限点目录与角色解析。

角色模型
--------
- 角色存 ``roles`` 表,``User.role`` 引用 ``Role.id``。
- 内置角色: ``admin``(隐式拥有全部权限,不可删除/修改)与
  ``member``(默认角色,权限可由管理员配置)。
- 自定义角色由管理员创建,自由组合目录中的权限点;删除前须先把名下用户改派。
- 权限判断实时读库(``get_current_user`` 亦每请求重载用户),角色/权限变更即时生效。
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from app.db.models import Role, User

ADMIN_ROLE_ID = "admin"
MEMBER_ROLE_ID = "member"
BUILTIN_ROLE_IDS = (ADMIN_ROLE_ID, MEMBER_ROLE_ID)


@dataclass(frozen=True)
class PermissionDef:
    key: str
    name: str
    group: str
    description: str


# 权限点目录:模块级粒度,前端角色配置页按 group 分组展示
PERMISSION_CATALOG: tuple[PermissionDef, ...] = (
    PermissionDef(
        "accounts.manage",
        "账号管理",
        "系统管理",
        "新建、编辑、删除账号,并为账号分配角色",
    ),
    PermissionDef(
        "roles.manage",
        "角色权限管理",
        "系统管理",
        "新建、编辑、删除角色,并配置角色权限",
    ),
    PermissionDef(
        "model_configs.manage",
        "模型配置",
        "系统管理",
        "新增、修改、删除与验证模型服务配置",
    ),
    PermissionDef(
        "channels.manage",
        "渠道接入",
        "系统管理",
        "管理微信/企业微信等渠道接入与投递审计",
    ),
    PermissionDef(
        "mcp.manage",
        "MCP与工具管理",
        "系统管理",
        "配置与管理 MCP server 及平台工具",
    ),
    PermissionDef(
        "system_settings.manage",
        "系统设置",
        "系统管理",
        "修改人设与 UI 配置等系统级设置",
    ),
    PermissionDef(
        "agents.manage_global",
        "全局数字员工管理",
        "数字员工与任务",
        "创建与管理平台级(全员)数字员工及广场展示",
    ),
    PermissionDef(
        "scheduled_tasks.manage",
        "企业定时任务",
        "数字员工与任务",
        "创建与管理企业级定时任务",
    ),
    PermissionDef(
        "chat_ops.manage",
        "会话管理操作",
        "数字员工与任务",
        "执行转人工、指派、待处理答复等会话管理操作",
    ),
    PermissionDef(
        "oversight.view",
        "监督审计",
        "监督审计",
        "查看全部会话、记忆、反馈与执行记录",
    ),
)

ALL_PERMISSION_KEYS: tuple[str, ...] = tuple(item.key for item in PERMISSION_CATALOG)
PERMISSION_KEY_SET = frozenset(ALL_PERMISSION_KEYS)


def catalog_as_list() -> list[dict[str, str]]:
    """目录的 API 输出形式:按定义顺序输出 key/name/group/description。"""
    return [
        {"key": item.key, "name": item.name, "group": item.group, "description": item.description}
        for item in PERMISSION_CATALOG
    ]


def validate_permission_keys(keys: list[str]) -> list[str]:
    """去重并保持顺序;含未知权限点时抛 ValueError。"""
    seen: list[str] = []
    for key in keys:
        if key not in PERMISSION_KEY_SET:
            raise ValueError(f"Unknown permission key: {key}")
        if key not in seen:
            seen.append(key)
    return seen


def get_role(db: Session, tenant_id: str, role_ref: str | None) -> Role | None:
    """按 id 取角色并校验租户归属;不存在或跨租户返回 None。"""
    if not role_ref:
        return None
    role = db.get(Role, role_ref)
    if role is None or role.tenant_id != tenant_id:
        return None
    return role


def resolve_role_permissions(role: Role | None) -> set[str]:
    """角色实际生效的权限点集合;admin 角色恒为全集。"""
    if role is None:
        return set()
    if role.id == ADMIN_ROLE_ID:
        return set(ALL_PERMISSION_KEYS)
    stored = role.permissions_json or []
    return {key for key in stored if key in PERMISSION_KEY_SET}


def user_is_admin(user: User) -> bool:
    """身份判断:用户是否挂在内置管理员角色上(不查库)。"""
    return user.role == ADMIN_ROLE_ID


def user_has_permission(db: Session, user: User, permission: str) -> bool:
    """用户是否持有指定权限点;admin 角色恒真,其余按角色配置判断。

    存量库中 role 仍为字符串且角色行尚未就位时,admin 判断兜底放行,
    member 一律拒绝,保证与旧的二元权限语义兼容。
    """
    if user.role == ADMIN_ROLE_ID:
        return True
    role = get_role(db, user.tenant_id, user.role)
    return permission in resolve_role_permissions(role)


def ensure_builtin_roles(db: Session, tenant_id: str, commit: bool = False) -> None:
    """幂等创建内置 admin/member 角色,并同步 admin 权限与最新目录。"""
    admin_role = db.get(Role, ADMIN_ROLE_ID)
    if admin_role is None:
        db.add(
            Role(
                id=ADMIN_ROLE_ID,
                tenant_id=tenant_id,
                display_name="管理员",
                description="内置管理员角色,拥有全部权限,不可删除或修改",
                is_builtin=True,
                permissions_json=list(ALL_PERMISSION_KEYS),
            )
        )
    elif admin_role.tenant_id == tenant_id:
        # 目录扩展后保持 admin 与全集一致(仅同步内置 admin,不改租户归属)
        expected = list(ALL_PERMISSION_KEYS)
        if list(admin_role.permissions_json or []) != expected:
            admin_role.permissions_json = expected
            db.add(admin_role)
    member_role = db.get(Role, MEMBER_ROLE_ID)
    if member_role is None:
        db.add(
            Role(
                id=MEMBER_ROLE_ID,
                tenant_id=tenant_id,
                display_name="成员",
                description="内置默认角色,权限可由管理员配置",
                is_builtin=True,
                permissions_json=[],
            )
        )
    if commit:
        db.commit()


def role_read_dict(db: Session, role: Role) -> dict:
    """角色 API 的统一输出结构(含解析后的权限与名下用户数)。"""
    from app.db.models import User

    user_count = len(
        db.exec(select(User.id).where(User.tenant_id == role.tenant_id, User.role == role.id)).all()
    )
    return {
        "id": role.id,
        "tenant_id": role.tenant_id,
        "display_name": role.display_name,
        "description": role.description,
        "is_builtin": role.is_builtin,
        "permissions": sorted(resolve_role_permissions(role)),
        "user_count": user_count,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
    }
