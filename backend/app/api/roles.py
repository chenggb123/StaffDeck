"""角色管理 API:内置 admin/member + 自定义角色的增删改查与权限配置。

- 角色列表对 accounts.manage / roles.manage 持有者可见(账号页分配角色需要)。
- 角色的创建/修改/删除与权限配置仅 roles.manage 持有者(默认仅管理员)。
- admin 角色不可修改/删除;内置角色不可删除;名下仍有用户的角色不可删除。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.db.models import Role, User, utc_now
from app.security.auth import ensure_current_user_tenant, get_current_user
from app.security.permissions import PERM_ACCOUNTS, PERM_ROLES, ensure_permission
from app.security.rbac import (
    ADMIN_ROLE_ID,
    BUILTIN_ROLE_IDS,
    catalog_as_list,
    ensure_builtin_roles,
    get_role,
    role_read_dict,
    user_has_permission,
    validate_permission_keys,
)

router = APIRouter(prefix="/api/enterprise/roles", tags=["roles"])

MAX_ROLE_DISPLAY_NAME = 40
MAX_ROLE_DESCRIPTION = 200


class RoleRead(BaseModel):
    id: str
    tenant_id: str
    display_name: str
    description: str | None = None
    is_builtin: bool = False
    permissions: list[str] = []
    user_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class RoleCreateRequest(BaseModel):
    tenant_id: str
    display_name: str
    description: str | None = None
    permissions: list[str] = []


class RoleUpdateRequest(BaseModel):
    tenant_id: str
    display_name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


def _ensure_role_reader(db: Session, tenant_id: str, current_user: User) -> None:
    """角色列表读守卫:账号管理(需分配角色)或角色权限管理任一权限即可。"""
    ensure_current_user_tenant(tenant_id, current_user)
    if not (
        user_has_permission(db, current_user, PERM_ACCOUNTS)
        or user_has_permission(db, current_user, PERM_ROLES)
    ):
        raise HTTPException(status_code=403, detail="Permission required: roles.read")


@router.get("/permissions/catalog")
def permission_catalog(
    tenant_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    """权限点目录(按定义顺序,前端按 group 分组渲染)。"""
    ensure_permission(db, tenant_id, current_user, PERM_ROLES)
    return {"permissions": catalog_as_list()}


@router.get("", response_model=list[RoleRead])
def list_roles(
    tenant_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> list[dict]:
    _ensure_role_reader(db, tenant_id, current_user)
    # 兜底:老库未跑过新 seed 时惰性补建内置角色
    ensure_builtin_roles(db, tenant_id, commit=True)
    rows = db.exec(select(Role).where(Role.tenant_id == tenant_id).order_by(Role.created_at)).all()
    return [role_read_dict(db, row) for row in rows]


@router.post("", response_model=RoleRead, status_code=201)
def create_role(
    request: RoleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    ensure_permission(db, request.tenant_id, current_user, PERM_ROLES)
    display_name = (request.display_name or "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Role display name is required")
    if len(display_name) > MAX_ROLE_DISPLAY_NAME:
        raise HTTPException(status_code=400, detail="Role display name is too long")
    try:
        permissions = validate_permission_keys(request.permissions or [])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    role = Role(
        tenant_id=request.tenant_id,
        display_name=display_name,
        description=(request.description or "").strip()[:MAX_ROLE_DESCRIPTION] or None,
        permissions_json=permissions,
    )
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Role display name already exists") from exc
    db.refresh(role)
    return role_read_dict(db, role)


@router.put("/{role_id}", response_model=RoleRead)
def update_role(
    role_id: str,
    request: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    ensure_permission(db, request.tenant_id, current_user, PERM_ROLES)
    role = get_role(db, request.tenant_id, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.id == ADMIN_ROLE_ID:
        raise HTTPException(status_code=403, detail="The administrator role cannot be modified")
    if request.display_name is not None:
        display_name = request.display_name.strip()
        if not display_name:
            raise HTTPException(status_code=400, detail="Role display name is required")
        if len(display_name) > MAX_ROLE_DISPLAY_NAME:
            raise HTTPException(status_code=400, detail="Role display name is too long")
        role.display_name = display_name
    if request.description is not None:
        role.description = request.description.strip()[:MAX_ROLE_DESCRIPTION] or None
    if request.permissions is not None:
        try:
            role.permissions_json = validate_permission_keys(request.permissions)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    role.updated_at = utc_now()
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Role display name already exists") from exc
    db.refresh(role)
    return role_read_dict(db, role)


@router.delete("/{role_id}")
def delete_role(
    role_id: str,
    tenant_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, bool]:
    ensure_permission(db, tenant_id, current_user, PERM_ROLES)
    role = get_role(db, tenant_id, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.id in BUILTIN_ROLE_IDS:
        raise HTTPException(status_code=403, detail="Built-in roles cannot be deleted")
    assigned = db.exec(
        select(User.id).where(User.tenant_id == tenant_id, User.role == role.id)
    ).first()
    if assigned is not None:
        raise HTTPException(
            status_code=409, detail="Role is still assigned to users; reassign them first"
        )
    db.delete(role)
    db.commit()
    return {"ok": True}
