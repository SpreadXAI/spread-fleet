"""Seed mock data, plans, admin account, workspace migration."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func

from app.auth import hash_password
from app.config import get_settings
from app.database import SessionLocal, ensure_schema, engine
from app.models import (
    AccountStatus,
    AccountTier,
    Base,
    ExecutionLog,
    SocialAccount,
    TaskStatus,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceMemberRole,
    WorkspacePlan,
)
from app.workspace import create_workspace, ensure_user_workspace, migrate_accounts_to_workspaces

TIER_PRICES = {
    AccountTier.basic: 9.9,
    AccountTier.standard: 29.9,
    AccountTier.premium: 99.9,
}

PLANS = [
    {
        "code": "starter",
        "name": "入门版",
        "description": "小团队试用，适合 1-3 人协作",
        "max_accounts": 5,
        "max_members": 3,
        "max_schedules_per_account": 2,
        "price_monthly": 0,
    },
    {
        "code": "growth",
        "name": "成长版",
        "description": "中型团队，更多账号与成员席位",
        "max_accounts": 20,
        "max_members": 10,
        "max_schedules_per_account": 3,
        "price_monthly": 299,
    },
    {
        "code": "fleet",
        "name": "舰队版",
        "description": "大规模账号舰队编排",
        "max_accounts": 100,
        "max_members": 30,
        "max_schedules_per_account": 3,
        "price_monthly": 999,
    },
]

BIOS = [
    "Tech enthusiast | AI & automation",
    "Digital marketer | Growth hacker",
    "Crypto curious | Web3 explorer",
    "Content creator | Lifestyle blogger",
    "Startup founder | Product thinker",
    "Fitness coach | Morning runner",
    "Photography lover | Travel addict",
    "Indie hacker | Building in public",
]

FIRST = ["alex", "sam", "jordan", "taylor", "casey", "riley", "morgan", "jamie", "avery", "quinn"]
LAST = ["chen", "wang", "kim", "patel", "garcia", "lee", "brown", "martin", "singh", "nguyen"]


def seed_plans() -> None:
    db = SessionLocal()
    try:
        for p in PLANS:
            if db.query(WorkspacePlan).filter(WorkspacePlan.code == p["code"]).first():
                continue
            db.add(WorkspacePlan(**p))
        db.commit()
        print("Plans seeded")
    finally:
        db.close()


def seed_admin() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        email = settings.admin_email.strip().lower()
        user = db.query(User).filter((User.email == email) | (User.username == email)).first()
        if user is None:
            user = User(
                username=email,
                email=email,
                display_name="管理员",
                password_hash=hash_password(settings.admin_password),
                is_admin=True,
            )
            db.add(user)
            db.flush()
            create_workspace(db, owner=user, name="Spider雷达 管理空间")
            db.commit()
            print(f"Admin created: {email}")
        else:
            user.is_admin = True
            ensure_user_workspace(db, user)
            db.commit()
            print(f"Admin updated: {email}")
    finally:
        db.close()


def seed_accounts(count: int = 200) -> None:
    ensure_schema()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(func.count(SocialAccount.id)).scalar() or 0
        if existing >= count:
            print(f"Skip seed: already have {existing} accounts")
            return

        to_create = count - existing
        tiers = list(AccountTier)
        for i in range(to_create):
            tier = random.choice(tiers)
            first = random.choice(FIRST)
            last = random.choice(LAST)
            num = existing + i + 1
            handle = f"{first}_{last}_{num}"
            display = f"{first.title()} {last.title()}"
            account = SocialAccount(
                platform="twitter",
                handle=handle,
                display_name=display,
                avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={handle}",
                bio=random.choice(BIOS),
                profile_url=f"https://x.com/{handle}",
                tier=tier,
                price=TIER_PRICES[tier],
                followers=random.randint(120, 50000),
                status=AccountStatus.available,
            )
            db.add(account)
        db.commit()
        print(f"Seeded {to_create} accounts (total target {count})")
    finally:
        db.close()


def bootstrap_existing_users() -> None:
    db = SessionLocal()
    try:
        for user in db.query(User).all():
            ensure_user_workspace(db, user)
        migrate_accounts_to_workspaces(db)
        db.commit()
        print("Existing users/workspaces migrated")
    finally:
        db.close()


def seed_demo_logs() -> None:
    db = SessionLocal()
    try:
        owned = db.query(SocialAccount).filter(SocialAccount.workspace_id.isnot(None)).limit(5).all()
        if not owned:
            return
        steps = [
            ("login", "账号登录成功", TaskStatus.completed),
            ("browse", "浏览目标主页", TaskStatus.completed),
            ("action", "执行互动操作", TaskStatus.completed),
            ("report", "生成执行报告", TaskStatus.completed),
        ]
        for account in owned:
            if db.query(ExecutionLog).filter(ExecutionLog.account_id == account.id).count() > 0:
                continue
            for step, msg, st in steps:
                db.add(
                    ExecutionLog(
                        account_id=account.id,
                        user_id=account.owner_user_id,
                        step=step,
                        message=msg,
                        screenshot_url=None,
                        status=st,
                    )
                )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed_plans()
    seed_admin()
    seed_accounts(n)
    bootstrap_existing_users()
    seed_demo_logs()
