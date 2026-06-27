from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Workspace, WorkspaceMember, WorkspaceMemberRole, WorkspacePlan
from app.schemas import (
    WorkspaceCreate,
    WorkspaceInvitationOut,
    WorkspaceInviteCreate,
    WorkspaceMemberOut,
    WorkspaceOut,
    WorkspacePlanOut,
    WorkspaceSwitch,
    WorkspaceUpdate,
)
from app.workspace import (
    create_workspace,
    ensure_user_workspace,
    get_membership,
    invite_by_email,
    normalize_email,
)

from fastapi import APIRouter

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _plan_out(plan: WorkspacePlan | None) -> WorkspacePlanOut | None:
    return WorkspacePlanOut.model_validate(plan) if plan else None


def _workspace_out(db: Session, ws: Workspace) -> WorkspaceOut:
    member_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
    from app.models import SocialAccount

    account_count = db.query(SocialAccount).filter(SocialAccount.workspace_id == ws.id).count()
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        owner_user_id=ws.owner_user_id,
        plan=_plan_out(ws.plan),
        member_count=member_count,
        account_count=account_count,
        created_at=ws.created_at,
    )


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WorkspaceOut]:
    ensure_user_workspace(db, current_user)
    db.commit()
    ids = [
        m.workspace_id
        for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
    ]
    rows = db.query(Workspace).options(joinedload(Workspace.plan)).filter(Workspace.id.in_(ids)).order_by(Workspace.id).all()
    return [_workspace_out(db, ws) for ws in rows]


@router.get("/current", response_model=WorkspaceOut)
def get_current_workspace(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkspaceOut:
    ws = ensure_user_workspace(db, current_user)
    db.commit()
    ws = db.query(Workspace).options(joinedload(Workspace.plan)).filter(Workspace.id == ws.id).one()
    return _workspace_out(db, ws)


@router.post("", response_model=WorkspaceOut)
def create_new_workspace(
    payload: WorkspaceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkspaceOut:
    ws = create_workspace(db, owner=current_user, name=payload.name.strip())
    db.commit()
    db.refresh(ws)
    return _workspace_out(db, ws)


@router.post("/switch", response_model=WorkspaceOut)
def switch_workspace(
    payload: WorkspaceSwitch,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkspaceOut:
    if get_membership(db, current_user.id, payload.workspace_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    current_user.active_workspace_id = payload.workspace_id
    db.commit()
    ws = db.get(Workspace, payload.workspace_id)
    assert ws is not None
    return _workspace_out(db, ws)


@router.put("/current", response_model=WorkspaceOut)
def update_current_workspace(
    payload: WorkspaceUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkspaceOut:
    ws = ensure_user_workspace(db, current_user)
    membership = get_membership(db, current_user.id, ws.id)
    if membership is None or membership.role != WorkspaceMemberRole.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner only")
    ws.name = payload.name.strip()
    db.commit()
    db.refresh(ws)
    return _workspace_out(db, ws)


@router.get("/current/members", response_model=list[WorkspaceMemberOut])
def list_members(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WorkspaceMemberOut]:
    ws = ensure_user_workspace(db, current_user)
    rows = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(WorkspaceMember.workspace_id == ws.id)
        .order_by(WorkspaceMember.joined_at)
        .all()
    )
    return [
        WorkspaceMemberOut(
            user_id=u.id,
            email=u.email or u.username,
            display_name=u.display_name or "",
            role=m.role,
            joined_at=m.joined_at,
        )
        for m, u in rows
    ]


@router.get("/current/invitations", response_model=list[WorkspaceInvitationOut])
def list_invitations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WorkspaceInvitationOut]:
    from app.models import InvitationStatus, WorkspaceInvitation

    ws = ensure_user_workspace(db, current_user)
    membership = get_membership(db, current_user.id, ws.id)
    if membership is None or membership.role != WorkspaceMemberRole.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner only")
    rows = (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.workspace_id == ws.id,
            WorkspaceInvitation.status == InvitationStatus.pending,
        )
        .order_by(WorkspaceInvitation.created_at.desc())
        .all()
    )
    return [WorkspaceInvitationOut.model_validate(r) for r in rows]


@router.post("/current/invitations", response_model=WorkspaceInvitationOut)
def invite_member(
    payload: WorkspaceInviteCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkspaceInvitationOut:
    ws = ensure_user_workspace(db, current_user)
    membership = get_membership(db, current_user.id, ws.id)
    if membership is None or membership.role != WorkspaceMemberRole.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner only")

    if ws.plan and db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count() >= ws.plan.max_members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Member limit reached for current plan")

    try:
        inv = invite_by_email(db, workspace=ws, inviter=current_user, email=payload.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    db.commit()
    db.refresh(inv)
    return WorkspaceInvitationOut.model_validate(inv)
