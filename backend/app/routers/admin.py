from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    AccountStatus,
    SocialAccount,
    User,
    Workspace,
    WorkspaceMember,
    WorkspacePlan,
)
from app.schemas import (
    AdminOverview,
    AdminWorkspaceDetail,
    SocialAccountOut,
    WorkspaceInvitationOut,
    WorkspaceMemberOut,
    WorkspaceOut,
    WorkspacePlanCreate,
    WorkspacePlanOut,
    WorkspacePlanUpdate,
)
from app.workspace import ensure_user_workspace

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user


def _workspace_summary(db: Session, ws: Workspace) -> WorkspaceOut:
    member_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
    account_count = db.query(SocialAccount).filter(SocialAccount.workspace_id == ws.id).count()
    plan_out = WorkspacePlanOut.model_validate(ws.plan) if ws.plan else None
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        owner_user_id=ws.owner_user_id,
        plan=plan_out,
        member_count=member_count,
        account_count=account_count,
        created_at=ws.created_at,
    )


@router.get("/overview", response_model=AdminOverview)
def admin_overview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> AdminOverview:
    return AdminOverview(
        total_users=db.query(User).count(),
        total_workspaces=db.query(Workspace).count(),
        total_social_accounts=db.query(SocialAccount).count(),
        accounts_available=db.query(SocialAccount).filter(SocialAccount.status == AccountStatus.available).count(),
        accounts_assigned=db.query(SocialAccount).filter(SocialAccount.workspace_id.isnot(None)).count(),
        total_plans=db.query(WorkspacePlan).count(),
    )


@router.get("/workspaces", response_model=list[WorkspaceOut])
def admin_list_workspaces(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> list[WorkspaceOut]:
    rows = db.query(Workspace).options(joinedload(Workspace.plan)).order_by(Workspace.id.desc()).all()
    return [_workspace_summary(db, ws) for ws in rows]


@router.get("/workspaces/{workspace_id}", response_model=AdminWorkspaceDetail)
def admin_workspace_detail(
    workspace_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> AdminWorkspaceDetail:
    from app.models import InvitationStatus, WorkspaceInvitation

    ws = db.query(Workspace).options(joinedload(Workspace.plan)).filter(Workspace.id == workspace_id).first()
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    members = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(WorkspaceMember.workspace_id == ws.id)
        .all()
    )
    invites = (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.workspace_id == ws.id,
            WorkspaceInvitation.status == InvitationStatus.pending,
        )
        .all()
    )
    accounts = (
        db.query(SocialAccount).filter(SocialAccount.workspace_id == ws.id).order_by(SocialAccount.id).all()
    )
    summary = _workspace_summary(db, ws)
    return AdminWorkspaceDetail(
        **summary.model_dump(),
        members=[
            WorkspaceMemberOut(
                user_id=u.id,
                email=u.email or u.username,
                display_name=u.display_name or "",
                role=m.role,
                joined_at=m.joined_at,
            )
            for m, u in members
        ],
        pending_invites=[WorkspaceInvitationOut.model_validate(i) for i in invites],
        accounts=[SocialAccountOut.model_validate(a) for a in accounts],
    )


@router.get("/accounts", response_model=list[SocialAccountOut])
def admin_list_accounts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
    skip: int = 0,
    limit: int = 100,
) -> list[SocialAccountOut]:
    rows = db.query(SocialAccount).order_by(SocialAccount.id.desc()).offset(skip).limit(min(limit, 200)).all()
    return [SocialAccountOut.model_validate(r) for r in rows]


@router.get("/plans", response_model=list[WorkspacePlanOut])
def admin_list_plans(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> list[WorkspacePlanOut]:
    rows = db.query(WorkspacePlan).order_by(WorkspacePlan.price_monthly).all()
    return [WorkspacePlanOut.model_validate(r) for r in rows]


@router.post("/plans", response_model=WorkspacePlanOut)
def admin_create_plan(
    payload: WorkspacePlanCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> WorkspacePlanOut:
    if db.query(WorkspacePlan).filter(WorkspacePlan.code == payload.code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan code exists")
    plan = WorkspacePlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return WorkspacePlanOut.model_validate(plan)


@router.put("/plans/{plan_id}", response_model=WorkspacePlanOut)
def admin_update_plan(
    plan_id: int,
    payload: WorkspacePlanUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> WorkspacePlanOut:
    plan = db.get(WorkspacePlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return WorkspacePlanOut.model_validate(plan)


@router.put("/workspaces/{workspace_id}/plan/{plan_id}", response_model=WorkspaceOut)
def admin_assign_plan(
    workspace_id: int,
    plan_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> WorkspaceOut:
    ws = db.get(Workspace, workspace_id)
    plan = db.get(WorkspacePlan, plan_id)
    if ws is None or plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    ws.plan_id = plan.id
    db.commit()
    db.refresh(ws)
    return _workspace_summary(db, ws)
