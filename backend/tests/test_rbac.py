"""RBAC 回归测试:内置/自定义角色、权限点解析与角色管理 API 守卫。"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.roles import (
    RoleCreateRequest,
    RoleUpdateRequest,
    create_role,
    delete_role,
    list_role_users,
    list_roles,
    permission_catalog,
    update_role,
)
from app.db.models import Role, Tenant, User
from app.security.permissions import PERM_ACCOUNTS, PERM_OVERSIGHT
from app.security.rbac import (
    ADMIN_ROLE_ID,
    ALL_PERMISSION_KEYS,
    MEMBER_ROLE_ID,
    catalog_as_list,
    ensure_builtin_roles,
    user_has_permission,
    validate_permission_keys,
)


def test_builtin_roles_are_idempotent_and_admin_resolves_full_catalog() -> None:
    with _test_session() as db:
        db.add(Tenant(id="tenant_demo", name="Demo"))
        ensure_builtin_roles(db, "tenant_demo", commit=True)
        ensure_builtin_roles(db, "tenant_demo", commit=True)  # 幂等

        rows = db.exec(select(Role).where(Role.tenant_id == "tenant_demo")).all()
        assert {row.id for row in rows} == {ADMIN_ROLE_ID, MEMBER_ROLE_ID}
        assert all(row.is_builtin for row in rows)

        admin_user = User(
            id="user_admin", tenant_id="tenant_demo", username="admin",
            role=ADMIN_ROLE_ID, password_hash="x",
        )
        member_user = User(
            id="user_member", tenant_id="tenant_demo", username="member",
            role=MEMBER_ROLE_ID, password_hash="x",
        )
        db.add(admin_user)
        db.add(member_user)
        db.commit()

        # admin 恒真,member 默认无任何权限
        for permission in ALL_PERMISSION_KEYS:
            assert user_has_permission(db, admin_user, permission) is True
            assert user_has_permission(db, member_user, permission) is False


def test_custom_role_grants_configured_permissions_to_member() -> None:
    with _test_session() as db:
        admin, member = _seed_admin_and_member(db)

        created = create_role(
            RoleCreateRequest(
                tenant_id="tenant_demo",
                display_name="审计员",
                description="只看会话与反馈",
                permissions=[PERM_OVERSIGHT],
            ),
            current_user=admin,
            db=db,
        )
        assert created["permissions"] == [PERM_OVERSIGHT]
        assert created["is_builtin"] is False

        member.role = created["id"]
        db.add(member)
        db.commit()

        assert user_has_permission(db, member, PERM_OVERSIGHT) is True
        assert user_has_permission(db, member, PERM_ACCOUNTS) is False

        # 权限配置变更实时生效(每请求读库,无缓存)
        update_role(
            created["id"],
            RoleUpdateRequest(tenant_id="tenant_demo", permissions=[PERM_ACCOUNTS]),
            current_user=admin,
            db=db,
        )
        assert user_has_permission(db, member, PERM_OVERSIGHT) is False
        assert user_has_permission(db, member, PERM_ACCOUNTS) is True


def test_role_management_requires_roles_manage_permission() -> None:
    with _test_session() as db:
        admin, member = _seed_admin_and_member(db)

        with pytest.raises(HTTPException) as catalog_error:
            permission_catalog(tenant_id="tenant_demo", current_user=member, db=db)
        assert catalog_error.value.status_code == 403
        with pytest.raises(HTTPException) as create_error:
            create_role(
                RoleCreateRequest(tenant_id="tenant_demo", display_name="越权角色"),
                current_user=member,
                db=db,
            )
        assert create_error.value.status_code == 403

        catalog = permission_catalog(tenant_id="tenant_demo", current_user=admin, db=db)
        assert catalog["permissions"] == catalog_as_list()

        # 持有 accounts.manage 的角色可读角色列表(账号页分配角色需要)
        accounts_role = Role(
            tenant_id="tenant_demo",
            display_name="账号管理员",
            permissions_json=[PERM_ACCOUNTS],
        )
        db.add(accounts_role)
        db.commit()
        member.role = accounts_role.id
        db.add(member)
        db.commit()
        rows = list_roles(tenant_id="tenant_demo", current_user=member, db=db)
        assert {row["id"] for row in rows} >= {ADMIN_ROLE_ID, MEMBER_ROLE_ID}


def test_admin_role_immutable_and_builtin_roles_undeletable() -> None:
    with _test_session() as db:
        admin, _member = _seed_admin_and_member(db)

        with pytest.raises(HTTPException) as update_error:
            update_role(
                ADMIN_ROLE_ID,
                RoleUpdateRequest(tenant_id="tenant_demo", permissions=[]),
                current_user=admin,
                db=db,
            )
        assert update_error.value.status_code == 403

        for builtin_id in (ADMIN_ROLE_ID, MEMBER_ROLE_ID):
            with pytest.raises(HTTPException) as delete_error:
                delete_role(builtin_id, tenant_id="tenant_demo", current_user=admin, db=db)
            assert delete_error.value.status_code == 403


def test_role_lifecycle_guards_duplicate_name_and_assigned_users() -> None:
    with _test_session() as db:
        admin, member = _seed_admin_and_member(db)

        created = create_role(
            RoleCreateRequest(
                tenant_id="tenant_demo", display_name="值班", permissions=[PERM_OVERSIGHT]
            ),
            current_user=admin,
            db=db,
        )
        with pytest.raises(HTTPException) as duplicate_error:
            create_role(
                RoleCreateRequest(tenant_id="tenant_demo", display_name="值班"),
                current_user=admin,
                db=db,
            )
        assert duplicate_error.value.status_code == 409

        member.role = created["id"]
        db.add(member)
        db.commit()
        with pytest.raises(HTTPException) as assigned_error:
            delete_role(created["id"], tenant_id="tenant_demo", current_user=admin, db=db)
        assert assigned_error.value.status_code == 409

        member.role = MEMBER_ROLE_ID
        db.add(member)
        db.commit()
        assert delete_role(created["id"], tenant_id="tenant_demo", current_user=admin, db=db) == {
            "ok": True
        }
        assert db.get(Role, created["id"]) is None


def test_role_members_list_is_scoped_to_role() -> None:
    with _test_session() as db:
        admin, member = _seed_admin_and_member(db)
        created = create_role(
            RoleCreateRequest(
                tenant_id="tenant_demo", display_name="审计员", permissions=[PERM_OVERSIGHT]
            ),
            current_user=admin,
            db=db,
        )
        member.role = created["id"]
        db.add(member)
        db.commit()

        rows = list_role_users(
            created["id"], tenant_id="tenant_demo", current_user=admin, db=db
        )
        assert [row["username"] for row in rows] == ["member"]
        assert [row["username"] for row in list_role_users(
            MEMBER_ROLE_ID, tenant_id="tenant_demo", current_user=admin, db=db
        )] == []


def test_validate_permission_keys_dedupes_and_rejects_unknown() -> None:
    assert validate_permission_keys([PERM_OVERSIGHT, PERM_OVERSIGHT]) == [PERM_OVERSIGHT]
    with pytest.raises(ValueError):
        validate_permission_keys(["not.a.permission"])

    with _test_session() as db:
        admin, _member = _seed_admin_and_member(db)
        with pytest.raises(HTTPException) as create_error:
            create_role(
                RoleCreateRequest(
                    tenant_id="tenant_demo", display_name="非法权限", permissions=["bogus.key"]
                ),
                current_user=admin,
                db=db,
            )
        assert create_error.value.status_code == 400


def _seed_admin_and_member(db: Session) -> tuple[User, User]:
    db.add(Tenant(id="tenant_demo", name="Demo"))
    ensure_builtin_roles(db, "tenant_demo")
    admin = User(
        id="user_admin", tenant_id="tenant_demo", username="admin",
        role=ADMIN_ROLE_ID, password_hash="x",
    )
    member = User(
        id="user_member", tenant_id="tenant_demo", username="member",
        role=MEMBER_ROLE_ID, password_hash="x",
    )
    db.add(admin)
    db.add(member)
    db.commit()
    return admin, member


def _test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)
