from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from sqlmodel import Session

from app.db import get_session
from app.db.models import AgentProfile, User
from app.security.auth import ensure_current_user_tenant, get_current_user
from app.security.rbac import ADMIN_ROLE_ID, MEMBER_ROLE_ID, user_has_permission, user_is_admin

ADMIN_ROLE = ADMIN_ROLE_ID
MEMBER_ROLE = MEMBER_ROLE_ID

# 权限点常量(与 app.security.rbac.PERMISSION_CATALOG 一致),避免调用处硬编码字符串
PERM_ACCOUNTS = "accounts.manage"
PERM_ROLES = "roles.manage"
PERM_MODEL_CONFIGS = "model_configs.manage"
PERM_CHANNELS = "channels.manage"
PERM_MCP = "mcp.manage"
PERM_SYSTEM_SETTINGS = "system_settings.manage"
PERM_AGENTS_GLOBAL = "agents.manage_global"
PERM_SCHEDULED_TASKS = "scheduled_tasks.manage"
PERM_CHAT_OPS = "chat_ops.manage"
PERM_OVERSIGHT = "oversight.view"


def is_admin_user(current_user: User) -> bool:
    """身份判断:是否为内置管理员角色(不查库)。

    接口鉴权请改用 ensure_permission/require_permission 的权限点判断;
    本函数仅保留给"目标是否管理员身份"这类与角色定义绑定的语义。
    """
    return user_is_admin(current_user)


def ensure_permission(db: Session, tenant_id: str, current_user: User, permission: str) -> User:
    """内联权限守卫:租户校验 + 权限点校验,失败抛 403。"""
    ensure_current_user_tenant(tenant_id, current_user)
    if not user_has_permission(db, current_user, permission):
        raise HTTPException(status_code=403, detail=f"Permission required: {permission}")
    return current_user


def require_permission(permission: str):
    """Depends 守卫工厂:要求查询参数 tenant_id,校验指定权限点。"""

    def dependency(
        tenant_id: str = Query(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_session),
    ) -> User:
        return ensure_permission(db, tenant_id, current_user, permission)

    return dependency


def require_agent_scope_viewer(
    tenant_id: str = Query(...),
    agent_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> User:
    ensure_current_user_tenant(tenant_id, current_user)
    if not agent_id:
        return current_user
    row = db.get(AgentProfile, agent_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    if (
        user_has_permission(db, current_user, PERM_AGENTS_GLOBAL)
        or row.is_overall
        or agent_owned_by_user(row, current_user)
        or (row.metadata_json or {}).get("published_to_gallery") is True
    ):
        return current_user
    raise HTTPException(status_code=403, detail="Cannot access this staff")


def ensure_open_gallery_admin(db: Session, tenant_id: str, current_user: User) -> None:
    """广场/平台级资源管理守卫:需要全局数字员工管理权限。"""
    ensure_permission(db, tenant_id, current_user, PERM_AGENTS_GLOBAL)


def ensure_agent_scope_manager(
    db: Session,
    tenant_id: str,
    agent_id: str | None,
    current_user: User,
) -> AgentProfile | None:
    ensure_current_user_tenant(tenant_id, current_user)
    if not agent_id:
        return None
    row = db.get(AgentProfile, agent_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    if user_has_permission(db, current_user, PERM_AGENTS_GLOBAL):
        return row
    if row.is_overall:
        raise HTTPException(status_code=403, detail="Only administrator can manage overall agent")
    if agent_owned_by_user(row, current_user):
        return row
    raise HTTPException(status_code=403, detail="Only the creator or administrator can manage this staff")


def agent_owned_by_user(row: AgentProfile, user: User) -> bool:
    metadata = row.metadata_json or {}
    return metadata.get("owner_user_id") == user.id
