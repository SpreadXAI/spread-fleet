"""Spider Radar skill catalog — wraps Tactile Skill Plaza with platform layering."""

from __future__ import annotations

from app.config import Settings
from app.models import SkillLayer
from app.schemas import SkillCatalogOut, SkillCatalogSkill
from app.tactile.client import TactileClient

PLATFORM_AUTHORING_SLUGS = frozenset({"skill-creator", "spider-radar-ops", "tactile-ops"})
PLATFORM_RUNTIME_SLUGS = frozenset({"tactile-ops", "spider-radar-ops", "zero-twitter-ops"})


def _to_skill(item: dict, *, layer: SkillLayer, readonly: bool = False) -> SkillCatalogSkill:
    return SkillCatalogSkill(
        id=int(item["id"]),
        slug=item.get("slug", ""),
        name=item.get("name", ""),
        description=item.get("description", ""),
        layer=layer,
        current_version_id=item.get("current_version_id"),
        current_version=item.get("current_version"),
        workspace_id=item.get("workspace_id"),
        readonly=readonly,
    )


def _dedupe_skills(items: list[SkillCatalogSkill]) -> list[SkillCatalogSkill]:
    seen: set[int] = set()
    out: list[SkillCatalogSkill] = []
    for skill in items:
        if skill.id in seen:
            continue
        seen.add(skill.id)
        out.append(skill)
    return out


def _layer_for_slug(slug: str) -> SkillLayer:
    if slug in PLATFORM_AUTHORING_SLUGS or slug in PLATFORM_RUNTIME_SLUGS:
        return SkillLayer.platform
    return SkillLayer.workspace


def platform_authoring_bindings(settings: Settings, client: TactileClient) -> list[dict[str, int]]:
    catalog = build_skill_catalog(settings, client)
    bindings: list[dict[str, int]] = []
    for skill in catalog.platform:
        if skill.slug in PLATFORM_AUTHORING_SLUGS and skill.current_version_id:
            bindings.append({"skill_id": skill.id, "version_id": skill.current_version_id})
    if bindings:
        return bindings
    fallback: list[dict[str, int]] = []
    if settings.tactile_skill_creator_skill_id and settings.tactile_skill_creator_skill_version_id:
        fallback.append(
            {
                "skill_id": settings.tactile_skill_creator_skill_id,
                "version_id": settings.tactile_skill_creator_skill_version_id,
            }
        )
    if settings.tactile_skill_ops_skill_id and settings.tactile_skill_ops_skill_version_id:
        fallback.append(
            {
                "skill_id": settings.tactile_skill_ops_skill_id,
                "version_id": settings.tactile_skill_ops_skill_version_id,
            }
        )
    return fallback


def build_skill_catalog(settings: Settings, client: TactileClient) -> SkillCatalogOut:
    ws_id = settings.tactile_workspace_id
    manage = client.list_workspace_skills(ws_id) if ws_id else {"workspace": [], "mine": []}
    market = client.list_skill_market(ws_id) if ws_id else {"items": []}

    platform: list[SkillCatalogSkill] = []
    workspace: list[SkillCatalogSkill] = []
    mine: list[SkillCatalogSkill] = []

    for item in manage.get("workspace") or []:
        slug = str(item.get("slug", ""))
        layer = _layer_for_slug(slug)
        skill = _to_skill(item, layer=layer, readonly=slug in PLATFORM_AUTHORING_SLUGS)
        (platform if layer == SkillLayer.platform else workspace).append(skill)

    for item in manage.get("mine") or []:
        slug = str(item.get("slug", ""))
        layer = _layer_for_slug(slug)
        skill = _to_skill(item, layer=layer, readonly=slug in PLATFORM_AUTHORING_SLUGS)
        (platform if layer == SkillLayer.platform else mine).append(skill)

    for item in market.get("items") or []:
        slug = str(item.get("slug", ""))
        if slug in PLATFORM_AUTHORING_SLUGS or slug in PLATFORM_RUNTIME_SLUGS:
            platform.append(
                _to_skill(item, layer=SkillLayer.platform, readonly=slug in PLATFORM_AUTHORING_SLUGS)
            )

    if settings.tactile_template_skill_id and settings.tactile_template_skill_version_id:
        if not any(s.id == settings.tactile_template_skill_id for s in platform):
            platform.append(
                SkillCatalogSkill(
                    id=settings.tactile_template_skill_id,
                    slug="twitter-ops-template",
                    name="Platform Twitter Ops",
                    description="Default platform twitter operations skill.",
                    layer=SkillLayer.platform,
                    current_version_id=settings.tactile_template_skill_version_id,
                    current_version=None,
                    workspace_id=ws_id,
                    readonly=True,
                )
            )

    platform = _dedupe_skills(platform)
    workspace = _dedupe_skills(workspace)
    mine = _dedupe_skills(mine)
    all_skills = _dedupe_skills(platform + workspace + mine)

    return SkillCatalogOut(platform=platform, workspace=workspace, mine=mine, all=all_skills)
