from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.auth import (
    LoginRequest,
    UserCreateRequest,
    UserUpdateRequest,
    create_user,
    login,
    update_user,
)
from app.db.models import Role, Tenant, User
from app.security.auth import hash_password
from app.security.permissions import PERM_ACCOUNTS
from app.security.rbac import ADMIN_ROLE_ID, MEMBER_ROLE_ID, ensure_builtin_roles


def test_unknown_login_does_not_create_account() -> None:
    with _test_session() as db:
        db.add(Tenant(id="tenant_demo", name="Demo"))
        db.commit()

        try:
            login(LoginRequest(tenant_id="tenant_demo", username="missing", password="secret"), db)
        except HTTPException as error:
            assert error.status_code == 401
            assert error.detail == "Invalid username or password"
        else:
            raise AssertionError("unknown account must not be created during login")

        assert db.exec(select(User)).all() == []


def test_database_role_controls_account_management() -> None:
    with _test_session() as db:
        db.add(Tenant(id="tenant_demo", name="Demo"))
        ensure_builtin_roles(db, "tenant_demo")
        member_named_admin = User(
            id="user_named_admin",
            tenant_id="tenant_demo",
            username="admin",
            role="member",
            password_hash=hash_password("secret"),
        )
        role_admin = User(
            id="user_role_admin",
            tenant_id="tenant_demo",
            username="ops",
            role="admin",
            password_hash=hash_password("secret"),
        )
        db.add(member_named_admin)
        db.add(role_admin)
        db.commit()

        try:
            create_user(
                UserCreateRequest(tenant_id="tenant_demo", username="blocked", password="secret"),
                member_named_admin,
                db,
            )
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("an admin-looking username must not grant administrator access")

        created = create_user(
            UserCreateRequest(
                tenant_id="tenant_demo",
                username="created_admin",
                password="secret",
                role="admin",
            ),
            role_admin,
            db,
        )
        assert created.role == "admin"

        updated = update_user(
            created.id,
            UserUpdateRequest(tenant_id="tenant_demo", role="member"),
            role_admin,
            db,
        )
        assert updated.role == "member"


def test_accounts_manager_cannot_create_or_promote_administrator() -> None:
    with _test_session() as db:
        db.add(Tenant(id="tenant_demo", name="Demo"))
        ensure_builtin_roles(db, "tenant_demo")
        accounts_role = Role(
            tenant_id="tenant_demo",
            display_name="账号管理员",
            permissions_json=[PERM_ACCOUNTS],
        )
        db.add(accounts_role)
        db.commit()

        accounts_manager = User(
            id="user_accounts_manager",
            tenant_id="tenant_demo",
            username="accounts_manager",
            role=accounts_role.id,
            password_hash=hash_password("secret"),
        )
        member = User(
            id="user_member",
            tenant_id="tenant_demo",
            username="member",
            role=MEMBER_ROLE_ID,
            password_hash=hash_password("secret"),
        )
        admin = User(
            id="user_admin",
            tenant_id="tenant_demo",
            username="admin",
            role=ADMIN_ROLE_ID,
            password_hash=hash_password("secret"),
        )
        db.add(accounts_manager)
        db.add(member)
        db.add(admin)
        db.commit()

        try:
            create_user(
                UserCreateRequest(
                    tenant_id="tenant_demo",
                    username="forbidden_admin",
                    password="secret",
                    role=ADMIN_ROLE_ID,
                ),
                accounts_manager,
                db,
            )
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("accounts manager must not create administrator accounts")

        try:
            update_user(
                member.id,
                UserUpdateRequest(tenant_id="tenant_demo", role=ADMIN_ROLE_ID),
                accounts_manager,
                db,
            )
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("accounts manager must not promote accounts to administrator")

        try:
            update_user(
                admin.id,
                UserUpdateRequest(tenant_id="tenant_demo", role=MEMBER_ROLE_ID),
                accounts_manager,
                db,
            )
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("accounts manager must not demote administrator accounts")


def _test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)
