"""Skill catalog, account bindings, batch install, and skill authoring."""

from __future__ import annotations

import json

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import AccountSkillBinding, SkillLayer, User
from app.routers.app import _active_workspace, _workspace_account
from app.schemas import (
    AccountSkillBindingOut,
    BatchSkillInstallRequest,
    BatchSkillInstallResult,
    SkillCatalogOut,
    SkillCreateSessionOut,
    SkillCreateSessionRequest,
)
from app.tactile.client import TactileClient, TactileError
from app.tactile.dispatcher import build_dispatch_env
from app.tactile.skill_catalog import PLATFORM_AUTHORING_SLUGS, build_skill_catalog, platform_authoring_bindings
from app.tactile.skill_sync import install_skill_on_accounts, sync_account_skills_to_agent

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/catalog", response_model=SkillCatalogOut)
def list_skill_catalog(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SkillCatalogOut:
    del db, current_user
    settings = get_settings()
    if not settings.tactile_workspace_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tactile not configured")
    client = TactileClient(settings)
    try:
        return build_skill_catalog(settings, client)
    except TactileError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.detail) from exc


@router.get("/platform", response_model=SkillCatalogOut)
def list_platform_skills(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SkillCatalogOut:
    """Platform-built skills only (skill-creator, skill-ops) — read-only in Spider Radar."""
    catalog = list_skill_catalog(db, current_user)
    authoring = [s for s in catalog.platform if s.slug in PLATFORM_AUTHORING_SLUGS]
    return SkillCatalogOut(platform=authoring, workspace=[], mine=[], all=authoring)


@router.get("/my/accounts/{account_id}/bindings", response_model=list[AccountSkillBindingOut])
def list_account_skills(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AccountSkillBindingOut]:
    _workspace_account(db, current_user, account_id)
    rows = (
        db.query(AccountSkillBinding)
        .filter(AccountSkillBinding.account_id == account_id)
        .order_by(AccountSkillBinding.sort_order, AccountSkillBinding.id)
        .all()
    )
    return [AccountSkillBindingOut.model_validate(r) for r in rows]


@router.post("/batch-install", response_model=BatchSkillInstallResult)
def batch_install_skill(
    payload: BatchSkillInstallRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BatchSkillInstallResult:
    settings = get_settings()
    ws = _active_workspace(db, current_user)
    client = TactileClient(settings)
    try:
        catalog = build_skill_catalog(settings, client)
    except TactileError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.detail) from exc

    installable = {s.id: s for s in catalog.workspace + catalog.mine if not s.readonly}
    if payload.skill_id not in installable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform authoring skills cannot be batch-installed; pick a workspace skill",
        )

    account_ids: list[int] = []
    for aid in payload.account_ids:
        account = _workspace_account(db, current_user, aid)
        if account.workspace_id != ws.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not in workspace")
        account_ids.append(aid)

    skill_meta = installable[payload.skill_id]
    slug = payload.slug or skill_meta.slug
    name = payload.name or skill_meta.name

    try:
        affected = install_skill_on_accounts(
            db,
            settings,
            account_ids=account_ids,
            skill_id=payload.skill_id,
            version_id=payload.version_id,
            slug=slug,
            name=name,
            layer=payload.layer,
            inputs_json=payload.inputs_json,
            outputs_json=payload.outputs_json,
        )
    except TactileError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.detail) from exc

    return BatchSkillInstallResult(
        skill_id=payload.skill_id,
        version_id=payload.version_id,
        account_ids=affected,
        installed_count=len(affected),
    )


@router.post("/create-session", response_model=SkillCreateSessionOut)
def start_skill_create_session(
    payload: SkillCreateSessionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SkillCreateSessionOut:
    settings = get_settings()
    account = _workspace_account(db, current_user, payload.account_id)

    if not account.session_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected account must have a session cookie before skill authoring",
        )

    agent_id = settings.tactile_skill_creator_agent_id
    if not agent_id or not settings.tactile_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Skill creator agent not configured (TACTILE_SKILL_CREATOR_AGENT_ID)",
        )

    client = TactileClient(settings)
    try:
        authoring_bindings = platform_authoring_bindings(settings, client)
        if not authoring_bindings:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Platform skill-creator / skill-ops not found in Tactile catalog",
            )
        client.update_agent_bindings(agent_id, {"skills": authoring_bindings})

        dispatch_env_json = json.dumps(build_dispatch_env(account), ensure_ascii=False)
        content = (
            f"Author a new Spider Radar nurturing skill for Twitter account @{account.handle}.\n\n"
            f"Account display name: {account.display_name}\n"
            f"Account bio: {account.bio or '(none)'}\n\n"
            f"Skill goal:\n{payload.prompt.strip()}\n\n"
            f"Use skill-creator to draft SKILL.md (define inputs/outputs clearly), "
            f"then use spider-radar-ops / tactile-ops to upload to Skill Plaza "
            f"workspace {settings.tactile_workspace_id}.\n"
            f"Test against the injected TWITTER_COOKIE for this account when validating behavior."
        )
        work = client.create_work(
            workspace_id=settings.tactile_workspace_id,
            agent_id=agent_id,
            name=payload.title or f"Skill for @{account.handle}",
            content=content,
            dispatch_env_json=dispatch_env_json,
        )
    except TactileError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.detail) from exc

    return SkillCreateSessionOut(
        tactile_work_id=work.get("id"),
        tactile_session_id=work.get("session_id"),
        tactile_agent_id=agent_id,
        account_id=account.id,
        account_handle=account.handle,
        message=f"Skill authoring started for @{account.handle} with platform skill-creator + skill-ops",
    )


@router.post("/my/accounts/{account_id}/sync-skills")
def sync_account_skills(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    account = _workspace_account(db, current_user, account_id)
    settings = get_settings()
    try:
        sync_account_skills_to_agent(db, settings, account)
    except TactileError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.detail) from exc
    return {"status": "synced"}
