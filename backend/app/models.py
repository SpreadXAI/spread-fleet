import enum
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountTier(str, enum.Enum):
    basic = "basic"
    standard = "standard"
    premium = "premium"


class AccountStatus(str, enum.Enum):
    available = "available"
    sold = "sold"
    running = "running"
    disabled = "disabled"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class WorkspaceMemberRole(str, enum.Enum):
    owner = "owner"
    member = "member"


class InvitationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    active_workspace_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="owner")
    prompts: Mapped[list["AccountPrompt"]] = relationship(back_populates="user")
    schedules: Mapped[list["ScheduledTask"]] = relationship(back_populates="user")
    batch_tasks: Mapped[list["BatchTask"]] = relationship(back_populates="user")
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user")
    owned_workspaces: Mapped[list["Workspace"]] = relationship(back_populates="owner")


class WorkspacePlan(Base):
    __tablename__ = "workspace_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    max_accounts: Mapped[int] = mapped_column(Integer, default=10)
    max_members: Mapped[int] = mapped_column(Integer, default=5)
    max_schedules_per_account: Mapped[int] = mapped_column(Integer, default=3)
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="plan")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("workspace_plans.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="owned_workspaces", foreign_keys=[owner_user_id])
    plan: Mapped[WorkspacePlan | None] = relationship(back_populates="workspaces")
    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    invitations: Mapped[list["WorkspaceInvitation"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    social_accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="workspace")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[WorkspaceMemberRole] = mapped_column(Enum(WorkspaceMemberRole), default=WorkspaceMemberRole.member)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="workspace_memberships")


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[InvitationStatus] = mapped_column(Enum(InvitationStatus), default=InvitationStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="invitations")


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), default="twitter")
    handle: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    avatar_url: Mapped[str] = mapped_column(String(512))
    bio: Mapped[str] = mapped_column(Text, default="")
    profile_url: Mapped[str] = mapped_column(String(512))
    tier: Mapped[AccountTier] = mapped_column(Enum(AccountTier), default=AccountTier.basic)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[AccountStatus] = mapped_column(Enum(AccountStatus), default=AccountStatus.available)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User | None] = relationship(back_populates="accounts")
    workspace: Mapped[Workspace | None] = relationship(back_populates="social_accounts")
    prompt: Mapped["AccountPrompt | None"] = relationship(back_populates="account", uselist=False)
    schedules: Mapped[list["ScheduledTask"]] = relationship(back_populates="account")
    logs: Mapped[list["ExecutionLog"]] = relationship(back_populates="account")


class AccountPrompt(Base):
    __tablename__ = "account_prompts"
    __table_args__ = (UniqueConstraint("account_id", name="uq_prompt_account"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    persona: Mapped[str] = mapped_column(Text, default="")
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    account: Mapped[SocialAccount] = relationship(back_populates="prompt")
    user: Mapped[User] = relationship(back_populates="prompts")


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    start_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped[SocialAccount] = relationship(back_populates="schedules")
    user: Mapped[User] = relationship(back_populates="schedules")


class BatchTask(Base):
    __tablename__ = "batch_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    start_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="batch_tasks")
    members: Mapped[list["BatchTaskMember"]] = relationship(back_populates="batch_task", cascade="all, delete-orphan")


class BatchTaskMember(Base):
    __tablename__ = "batch_task_members"
    __table_args__ = (UniqueConstraint("batch_task_id", "account_id", name="uq_batch_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_task_id: Mapped[int] = mapped_column(ForeignKey("batch_tasks.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id"), index=True)

    batch_task: Mapped[BatchTask] = relationship(back_populates="members")
    account: Mapped[SocialAccount] = relationship()


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    step: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    screenshot_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.completed)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped[SocialAccount] = relationship(back_populates="logs")
