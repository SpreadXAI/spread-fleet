from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    AccountPrompt,
    AccountStatus,
    BatchTask,
    BatchTaskMember,
    ExecutionLog,
    ScheduledTask,
    SocialAccount,
    TaskStatus,
    User,
    Workspace,
    WorkspaceMember,
)
from app.schemas import (
    BatchTaskCreate,
    BatchTaskOut,
    DashboardStats,
    ExecutionLogOut,
    PromptOut,
    PromptUpdate,
    ScheduleCreate,
    ScheduleOut,
    SocialAccountOut,
)
from app.workspace import ensure_user_workspace, get_membership

router = APIRouter(tags=["app"])

MAX_SCHEDULES_PER_ACCOUNT = 3


def _active_workspace(db: Session, user: User) -> Workspace:
    ws = ensure_user_workspace(db, user)
    return ws


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DashboardStats:
    ws = _active_workspace(db, current_user)
    owned = db.query(SocialAccount).filter(SocialAccount.workspace_id == ws.id).count()
    market = db.query(SocialAccount).filter(SocialAccount.status == AccountStatus.available).count()
    member_ids = [
        m.user_id for m in db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).all()
    ]
    schedules = (
        db.query(ScheduledTask)
        .join(SocialAccount)
        .filter(SocialAccount.workspace_id == ws.id, ScheduledTask.enabled.is_(True))
        .count()
    )
    batches = db.query(BatchTask).filter(BatchTask.workspace_id == ws.id).count()
    logs = (
        db.query(ExecutionLog)
        .join(SocialAccount)
        .filter(SocialAccount.workspace_id == ws.id)
        .count()
    )
    members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
    return DashboardStats(
        total_accounts_owned=owned,
        available_market=market,
        active_schedules=schedules,
        batch_tasks=batches,
        recent_logs=logs,
        workspace_name=ws.name,
        workspace_members=members,
    )


@router.get("/market/accounts", response_model=list[SocialAccountOut])
def list_market_accounts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 50,
) -> list[SocialAccountOut]:
    del current_user
    rows = (
        db.query(SocialAccount)
        .filter(SocialAccount.status == AccountStatus.available, SocialAccount.workspace_id.is_(None))
        .order_by(SocialAccount.id)
        .offset(skip)
        .limit(min(limit, 100))
        .all()
    )
    return [SocialAccountOut.model_validate(r) for r in rows]


@router.get("/my/accounts", response_model=list[SocialAccountOut])
def list_my_accounts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SocialAccountOut]:
    ws = _active_workspace(db, current_user)
    rows = (
        db.query(SocialAccount)
        .filter(SocialAccount.workspace_id == ws.id)
        .order_by(SocialAccount.id)
        .all()
    )
    return [SocialAccountOut.model_validate(r) for r in rows]


@router.post("/my/accounts/{account_id}/purchase", response_model=SocialAccountOut)
def purchase_account(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SocialAccountOut:
    ws = _active_workspace(db, current_user)
    if ws.plan:
        current_count = db.query(SocialAccount).filter(SocialAccount.workspace_id == ws.id).count()
        if current_count >= ws.plan.max_accounts:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account limit reached for plan")

    account = db.get(SocialAccount, account_id)
    if account is None or account.status != AccountStatus.available or account.workspace_id is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not available")
    account.owner_user_id = current_user.id
    account.workspace_id = ws.id
    account.status = AccountStatus.sold
    db.commit()
    db.refresh(account)
    return SocialAccountOut.model_validate(account)


@router.get("/my/accounts/{account_id}", response_model=SocialAccountOut)
def get_my_account(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SocialAccountOut:
    account = _workspace_account(db, current_user, account_id)
    return SocialAccountOut.model_validate(account)


@router.get("/my/accounts/{account_id}/prompt", response_model=PromptOut | None)
def get_prompt(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PromptOut | None:
    _workspace_account(db, current_user, account_id)
    prompt = db.query(AccountPrompt).filter(AccountPrompt.account_id == account_id).first()
    return PromptOut.model_validate(prompt) if prompt else None


@router.put("/my/accounts/{account_id}/prompt", response_model=PromptOut)
def upsert_prompt(
    account_id: int,
    payload: PromptUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PromptOut:
    _workspace_account(db, current_user, account_id)
    prompt = db.query(AccountPrompt).filter(AccountPrompt.account_id == account_id).first()
    if prompt is None:
        prompt = AccountPrompt(account_id=account_id, user_id=current_user.id)
        db.add(prompt)
    prompt.persona = payload.persona
    prompt.prompt_text = payload.prompt_text
    prompt.user_id = current_user.id
    db.commit()
    db.refresh(prompt)
    return PromptOut.model_validate(prompt)


@router.get("/my/accounts/{account_id}/schedules", response_model=list[ScheduleOut])
def list_schedules(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ScheduleOut]:
    _workspace_account(db, current_user, account_id)
    rows = (
        db.query(ScheduledTask)
        .filter(ScheduledTask.account_id == account_id)
        .order_by(ScheduledTask.start_time)
        .all()
    )
    return [ScheduleOut.model_validate(r) for r in rows]


@router.post("/my/accounts/{account_id}/schedules", response_model=ScheduleOut)
def create_schedule(
    account_id: int,
    payload: ScheduleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScheduleOut:
    ws = _active_workspace(db, current_user)
    _workspace_account(db, current_user, account_id)
    max_sched = ws.plan.max_schedules_per_account if ws.plan else MAX_SCHEDULES_PER_ACCOUNT
    count = db.query(ScheduledTask).filter(ScheduledTask.account_id == account_id).count()
    if count >= max_sched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {max_sched} schedules per account",
        )
    task = ScheduledTask(
        account_id=account_id,
        user_id=current_user.id,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        enabled=payload.enabled,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return ScheduleOut.model_validate(task)


@router.delete("/my/accounts/{account_id}/schedules/{schedule_id}")
def delete_schedule(
    account_id: int,
    schedule_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    _workspace_account(db, current_user, account_id)
    task = (
        db.query(ScheduledTask)
        .filter(ScheduledTask.id == schedule_id, ScheduledTask.account_id == account_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    db.delete(task)
    db.commit()
    return {"status": "deleted"}


@router.get("/batch-tasks", response_model=list[BatchTaskOut])
def list_batch_tasks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[BatchTaskOut]:
    ws = _active_workspace(db, current_user)
    rows = (
        db.query(BatchTask)
        .options(joinedload(BatchTask.members))
        .filter(BatchTask.workspace_id == ws.id)
        .order_by(BatchTask.id.desc())
        .all()
    )
    return [_batch_out(r) for r in rows]


@router.post("/batch-tasks", response_model=BatchTaskOut)
def create_batch_task(
    payload: BatchTaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BatchTaskOut:
    ws = _active_workspace(db, current_user)
    for aid in payload.account_ids:
        _workspace_account(db, current_user, aid)

    batch = BatchTask(
        user_id=current_user.id,
        workspace_id=ws.id,
        name=payload.name,
        prompt_text=payload.prompt_text,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        enabled=payload.enabled,
    )
    db.add(batch)
    db.flush()
    for aid in payload.account_ids:
        db.add(BatchTaskMember(batch_task_id=batch.id, account_id=aid))
    db.commit()
    db.refresh(batch)
    batch = (
        db.query(BatchTask)
        .options(joinedload(BatchTask.members))
        .filter(BatchTask.id == batch.id)
        .one()
    )
    return _batch_out(batch)


@router.get("/execution-logs", response_model=list[ExecutionLogOut])
def list_execution_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
) -> list[ExecutionLogOut]:
    ws = _active_workspace(db, current_user)
    rows = (
        db.query(ExecutionLog, SocialAccount.handle)
        .join(SocialAccount, ExecutionLog.account_id == SocialAccount.id)
        .filter(SocialAccount.workspace_id == ws.id)
        .order_by(ExecutionLog.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    result = []
    for log, handle in rows:
        item = ExecutionLogOut.model_validate(log)
        item.account_handle = handle
        result.append(item)
    return result


def _workspace_account(db: Session, user: User, account_id: int) -> SocialAccount:
    ws = _active_workspace(db, user)
    if get_membership(db, user.id, ws.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in workspace")
    account = db.get(SocialAccount, account_id)
    if account is None or account.workspace_id != ws.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _batch_out(batch: BatchTask) -> BatchTaskOut:
    return BatchTaskOut(
        id=batch.id,
        name=batch.name,
        prompt_text=batch.prompt_text,
        start_time=batch.start_time,
        duration_minutes=batch.duration_minutes,
        enabled=batch.enabled,
        created_at=batch.created_at,
        account_ids=[m.account_id for m in batch.members],
    )
