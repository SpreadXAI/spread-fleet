"""Workspace membership and bootstrap helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    InvitationStatus,
    SocialAccount,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceMemberRole,
    WorkspacePlan,
    User,
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def user_workspace_ids(db: Session, user_id: int) -> list[int]:
    rows = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == user_id).all()
    return [r[0] for r in rows]


def get_membership(db: Session, user_id: int, workspace_id: int) -> WorkspaceMember | None:
    return (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user_id, WorkspaceMember.workspace_id == workspace_id)
        .first()
    )


def require_active_workspace(db: Session, user: User) -> Workspace:
    if user.active_workspace_id is None:
        raise ValueError("no active workspace")
    ws = db.get(Workspace, user.active_workspace_id)
    if ws is None or get_membership(db, user.id, ws.id) is None:
        raise ValueError("invalid workspace")
    return ws


def create_workspace(
    db: Session,
    *,
    owner: User,
    name: str,
    plan: WorkspacePlan | None = None,
) -> Workspace:
    if plan is None:
        plan = db.query(WorkspacePlan).filter(WorkspacePlan.code == "starter").first()
    ws = Workspace(
        name=name,
        owner_user_id=owner.id,
        plan_id=plan.id if plan else None,
    )
    db.add(ws)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=owner.id,
            role=WorkspaceMemberRole.owner,
        )
    )
    owner.active_workspace_id = ws.id
    return ws


def accept_pending_invitations(db: Session, user: User) -> list[Workspace]:
    email = normalize_email(user.email or user.username)
    invites = (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.email == email,
            WorkspaceInvitation.status == InvitationStatus.pending,
        )
        .all()
    )
    joined: list[Workspace] = []
    for inv in invites:
        if get_membership(db, user.id, inv.workspace_id):
            inv.status = InvitationStatus.accepted
            continue
        db.add(
            WorkspaceMember(
                workspace_id=inv.workspace_id,
                user_id=user.id,
                role=WorkspaceMemberRole.member,
            )
        )
        inv.status = InvitationStatus.accepted
        ws = db.get(Workspace, inv.workspace_id)
        if ws:
            joined.append(ws)
    if user.active_workspace_id is None:
        first = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
        if first:
            user.active_workspace_id = first.workspace_id
    return joined


def ensure_user_workspace(db: Session, user: User) -> Workspace:
    accept_pending_invitations(db, user)
    if user.active_workspace_id:
        ws = db.get(Workspace, user.active_workspace_id)
        if ws and get_membership(db, user.id, ws.id):
            return ws
    member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
    if member:
        user.active_workspace_id = member.workspace_id
        ws = db.get(Workspace, member.workspace_id)
        if ws:
            return ws
    label = (user.email or user.username or "用户").split("@")[0]
    return create_workspace(db, owner=user, name=f"{label} 的团队")


def invite_by_email(
    db: Session,
    *,
    workspace: Workspace,
    inviter: User,
    email: str,
) -> WorkspaceInvitation:
    email = normalize_email(email)
    if email == normalize_email(inviter.email or inviter.username):
        raise ValueError("cannot invite yourself")

    existing_member = (
        db.query(WorkspaceMember)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            (User.email == email) | (User.username == email),
        )
        .first()
    )
    if existing_member:
        raise ValueError("user already in workspace")

    pending = (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.workspace_id == workspace.id,
            WorkspaceInvitation.email == email,
            WorkspaceInvitation.status == InvitationStatus.pending,
        )
        .first()
    )
    if pending:
        return pending

    target = db.query(User).filter((User.email == email) | (User.username == email)).first()
    inv = WorkspaceInvitation(
        workspace_id=workspace.id,
        email=email,
        invited_by_user_id=inviter.id,
        status=InvitationStatus.pending,
    )
    db.add(inv)
    db.flush()
    if target:
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=target.id,
                role=WorkspaceMemberRole.member,
            )
        )
        inv.status = InvitationStatus.accepted
        if target.active_workspace_id is None:
            target.active_workspace_id = workspace.id
    return inv


def migrate_accounts_to_workspaces(db: Session) -> None:
    """Attach legacy user-owned accounts to the user's active workspace."""
    accounts = db.query(SocialAccount).filter(
        SocialAccount.workspace_id.is_(None),
        SocialAccount.owner_user_id.isnot(None),
    ).all()
    for acc in accounts:
        user = db.get(User, acc.owner_user_id)
        if user is None:
            continue
        ws = ensure_user_workspace(db, user)
        acc.workspace_id = ws.id
    db.commit()
