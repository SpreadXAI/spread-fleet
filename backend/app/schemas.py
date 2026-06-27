from datetime import datetime, time

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.models import AccountStatus, AccountTier, InvitationStatus, SkillLayer, TaskStatus, WorkspaceMemberRole

if TYPE_CHECKING:
    from app.models import SocialAccount


class UserRegister(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class UserProfileUpdate(BaseModel):
    display_name: str = Field(max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    is_admin: bool = False
    active_workspace_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class WorkspacePlanOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    max_accounts: int
    max_members: int
    max_schedules_per_account: int
    price_monthly: float
    enabled: bool

    model_config = {"from_attributes": True}


class WorkspacePlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    max_accounts: int | None = Field(default=None, ge=1)
    max_members: int | None = Field(default=None, ge=1)
    max_schedules_per_account: int | None = Field(default=None, ge=1)
    price_monthly: float | None = Field(default=None, ge=0)
    enabled: bool | None = None


class WorkspacePlanCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    max_accounts: int = Field(default=10, ge=1)
    max_members: int = Field(default=5, ge=1)
    max_schedules_per_account: int = Field(default=3, ge=1)
    price_monthly: float = Field(default=0, ge=0)
    enabled: bool = True


class WorkspaceMemberOut(BaseModel):
    user_id: int
    email: str
    display_name: str
    role: WorkspaceMemberRole
    joined_at: datetime


class WorkspaceInvitationOut(BaseModel):
    id: int
    email: str
    status: InvitationStatus
    created_at: datetime


class WorkspaceOut(BaseModel):
    id: int
    name: str
    owner_user_id: int
    plan: WorkspacePlanOut | None = None
    member_count: int = 0
    account_count: int = 0
    created_at: datetime


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WorkspaceInviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class WorkspaceSwitch(BaseModel):
    workspace_id: int


class AdminOverview(BaseModel):
    total_users: int
    total_workspaces: int
    total_social_accounts: int
    accounts_available: int
    accounts_assigned: int
    total_plans: int


class AdminWorkspaceDetail(WorkspaceOut):
    members: list[WorkspaceMemberOut]
    pending_invites: list[WorkspaceInvitationOut]
    accounts: list["SocialAccountOut"]


class SocialAccountOut(BaseModel):
    id: int
    platform: str
    handle: str
    display_name: str
    avatar_url: str
    bio: str
    profile_url: str
    tier: AccountTier
    price: float
    followers: int
    status: AccountStatus
    owner_user_id: int | None
    workspace_id: int | None = None
    has_cookie: bool = False
    tactile_agent_id: int | None = None
    tactile_last_work_id: int | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, account: "SocialAccount") -> "SocialAccountOut":
        data = cls.model_validate(account)
        data.has_cookie = bool(account.session_cookie)
        return data


class CookieUpdate(BaseModel):
    session_cookie: str = Field(min_length=1)


class AccountRunOut(BaseModel):
    log_id: int
    tactile_work_id: int | None
    tactile_session_id: str | None
    status: TaskStatus
    message: str


class TactileCallbackLog(BaseModel):
    account_id: int
    step: str = Field(min_length=1, max_length=64)
    message: str
    screenshot_url: str | None = None
    status: TaskStatus = TaskStatus.completed
    tactile_work_id: int | None = None
    tactile_session_id: str | None = None


class PromptUpdate(BaseModel):
    persona: str = ""
    prompt_text: str = ""


class PromptOut(BaseModel):
    id: int
    account_id: int
    persona: str
    prompt_text: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    start_time: time
    duration_minutes: int = Field(default=30, ge=1, le=60)
    enabled: bool = True


class ScheduleOut(BaseModel):
    id: int
    account_id: int
    start_time: time
    duration_minutes: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchTaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    prompt_text: str = ""
    start_time: time
    duration_minutes: int = Field(default=30, ge=1, le=60)
    account_ids: list[int] = Field(min_length=1)
    enabled: bool = True


class BatchTaskOut(BaseModel):
    id: int
    name: str
    prompt_text: str
    start_time: time
    duration_minutes: int
    enabled: bool
    created_at: datetime
    account_ids: list[int]

    model_config = {"from_attributes": True}


class ExecutionLogOut(BaseModel):
    id: int
    account_id: int
    step: str
    message: str
    screenshot_url: str | None
    status: TaskStatus
    created_at: datetime
    account_handle: str | None = None
    tactile_work_id: int | None = None
    tactile_session_id: str | None = None

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_accounts_owned: int
    available_market: int
    active_schedules: int
    batch_tasks: int
    recent_logs: int
    workspace_name: str | None = None
    workspace_members: int = 0


AdminWorkspaceDetail.model_rebuild()


class SkillCatalogSkill(BaseModel):
    id: int
    slug: str
    name: str
    description: str = ""
    layer: SkillLayer
    current_version_id: int | None = None
    current_version: str | None = None
    workspace_id: int | None = None
    readonly: bool = False


class SkillCatalogOut(BaseModel):
    platform: list[SkillCatalogSkill] = Field(default_factory=list)
    workspace: list[SkillCatalogSkill] = Field(default_factory=list)
    mine: list[SkillCatalogSkill] = Field(default_factory=list)
    all: list[SkillCatalogSkill] = Field(default_factory=list)


class AccountSkillBindingOut(BaseModel):
    id: int
    account_id: int
    skill_id: int
    version_id: int
    slug: str
    name: str
    layer: SkillLayer
    inputs_json: str | None = None
    outputs_json: str | None = None
    sort_order: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchSkillInstallRequest(BaseModel):
    skill_id: int
    version_id: int
    account_ids: list[int] = Field(min_length=1)
    slug: str = ""
    name: str = ""
    layer: SkillLayer = SkillLayer.account
    inputs_json: str | None = None
    outputs_json: str | None = None


class BatchSkillInstallResult(BaseModel):
    skill_id: int
    version_id: int
    account_ids: list[int]
    installed_count: int


class SkillCreateSessionRequest(BaseModel):
    account_id: int = Field(ge=1)
    prompt: str = Field(min_length=10)
    title: str = Field(default="Spider Radar Skill", max_length=200)


class SkillCreateSessionOut(BaseModel):
    tactile_work_id: int | None
    tactile_session_id: str | None
    tactile_agent_id: int | None = None
    account_id: int
    account_handle: str
    message: str
