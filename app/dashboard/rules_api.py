"""Rule set viewing and saving endpoints for the in-dashboard rule editor."""

import asyncio
from collections.abc import Mapping
from pathlib import Path

from fastapi import APIRouter, Cookie, HTTPException, Request, status

from app.dashboard.admin import ADMIN_COOKIE_NAME, AdminSessions, run_pipeline_step
from app.dashboard.schemas import (
    ClassificationCategoryModel,
    ClassificationValueModel,
    ContextRuleModel,
    ContextsModel,
    RuleCreateRequest,
    RuleDeleteResponse,
    RulePreviewRequest,
    RulePreviewResponse,
    RuleProblemModel,
    RuleSaveRequest,
    RuleSaveResponse,
    RuleSetBody,
    RuleSetItem,
    RuleSetsResponse,
    RuleVersionModel,
    RuleVersionResponse,
    RuleVersionsResponse,
    ValidationModel,
    WorkflowModel,
    WorkflowStageModel,
)
from app.dashboard.service import DashboardService
from app.processor.preview import summarize_impact
from app.processor.rule_loader import (
    ClassificationMatch,
    ConfigurationConflictError,
    ContextConfig,
    ContextRule,
    DomainRule,
    StageConfig,
    ValidationConfig,
    WorkflowConfig,
)
from app.processor.rule_store import (
    InvalidRuleSetNameError,
    RevisionConflictError,
    RuleProblem,
    RuleSetExistsError,
    RuleSetNotFoundError,
    RuleStore,
    RuleVersionNotFoundError,
    StoredRuleSet,
    effective_default_name,
    unique_name,
    validate_rule_set,
)

_preview_lock = asyncio.Lock()


def rule_to_body(rule: DomainRule) -> RuleSetBody:
    """Convert a DomainRule to the API model, keeping classification order."""
    return RuleSetBody(
        project_ids=list(rule.project_ids),
        team=rule.team,
        classification=[
            ClassificationCategoryModel(
                name=category,
                values=[
                    ClassificationValueModel(
                        name=value_name,
                        labels=list(match.labels),
                        title=list(match.title),
                    )
                    for value_name, match in values.items()
                ],
            )
            for category, values in rule.classification.items()
        ],
        contexts=ContextsModel(
            rules=[
                ContextRuleModel(
                    name=context.name,
                    labels=list(context.labels),
                    title=list(context.title),
                )
                for context in rule.contexts.rules
            ],
            require_assignment=rule.contexts.require_assignment,
        ),
        workflow=WorkflowModel(
            stages=[
                WorkflowStageModel(
                    name=stage.name,
                    labels=list(stage.labels),
                    type=stage.type,
                    description=stage.description,
                )
                for stage in rule.workflow.stages
            ]
        ),
        validation=ValidationModel(
            required_labels={k: list(v) for k, v in rule.validation.required_labels.items()},
            required_fields={k: list(v) for k, v in rule.validation.required_fields.items()},
            stale_threshold_days=rule.validation.stale_threshold_days,
            max_cycle_time_days=rule.validation.max_cycle_time_days,
        ),
        colors=dict(rule.colors),
    )


def body_to_rule(body: RuleSetBody) -> DomainRule:
    """Convert the API model to a DomainRule, keeping classification order."""
    return DomainRule(
        project_ids=list(body.project_ids),
        team=body.team,
        classification={
            category.name: {
                value.name: ClassificationMatch(
                    labels=list(value.labels), title=list(value.title)
                )
                for value in category.values
            }
            for category in body.classification
        },
        contexts=ContextConfig(
            rules=[
                ContextRule(
                    name=context.name,
                    labels=list(context.labels),
                    title=list(context.title),
                )
                for context in body.contexts.rules
            ],
            require_assignment=body.contexts.require_assignment,
        ),
        workflow=WorkflowConfig(
            stages=[
                StageConfig(
                    name=stage.name,
                    labels=list(stage.labels),
                    type=stage.type,
                    description=stage.description,
                )
                for stage in body.workflow.stages
            ]
        ),
        validation=ValidationConfig(
            required_labels={k: list(v) for k, v in body.validation.required_labels.items()},
            required_fields={k: list(v) for k, v in body.validation.required_fields.items()},
            stale_threshold_days=body.validation.stale_threshold_days,
            max_cycle_time_days=body.validation.max_cycle_time_days,
        ),
        colors=dict(body.colors),
    )


def _to_item(stored: StoredRuleSet) -> RuleSetItem:
    return RuleSetItem(
        name=stored.name, revision=stored.revision, rule=rule_to_body(stored.rule)
    )


def _duplicate_classification_problems(body: RuleSetBody) -> list[RuleProblem]:
    problems: list[RuleProblem] = []
    seen_categories: set[str] = set()
    for category in body.classification:
        if category.name in seen_categories:
            problems.append(
                RuleProblem(
                    path=f"classification.{category.name}.name",
                    message=f"There is more than one category named '{category.name}'.",
                )
            )
        seen_categories.add(category.name)
        seen_values: set[str] = set()
        for index, value in enumerate(category.values):
            if value.name in seen_values:
                problems.append(
                    RuleProblem(
                        path=f"classification.{category.name}.{index}.name",
                        message=(
                            f"There is more than one value named '{value.name}' "
                            f"in '{category.name}'."
                        ),
                    )
                )
            seen_values.add(value.name)
    return problems


def _check_name(store: RuleStore, name: str) -> None:
    """Raise HTTP 422 for an invalid name and 404 for an unknown rule set."""
    try:
        store.check_exists(name)
    except InvalidRuleSetNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except RuleSetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


def _validate_body(
    body: RuleSetBody, others: Mapping[str, DomainRule]
) -> tuple[DomainRule | None, list[RuleProblem]]:
    """Convert and validate a draft; the rule is None after duplicate names."""
    duplicates = _duplicate_classification_problems(body)
    if duplicates:
        return None, duplicates
    rule = body_to_rule(body)
    return rule, validate_rule_set(rule, others)


def _problems_error(problems: list[RuleProblem]) -> HTTPException:
    summary = (
        "1 problem needs" if len(problems) == 1 else f"{len(problems)} problems need"
    )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": f"{summary} fixing before these rules can be saved.",
            "problems": [
                RuleProblemModel(path=problem.path, message=problem.message).model_dump()
                for problem in problems
            ],
        },
    )


def _check_draft(
    store: RuleStore, name: str, body: RuleSetBody
) -> tuple[
    DomainRule | None, DomainRule | None, dict[str, DomainRule], list[RuleProblem]
]:
    """Validate a draft of an existing rule set for saving or previewing.

    Returns:
        The converted rule (None when duplicate classification names make the
        conversion unreliable), the stored version of this rule set, the other
        stored rule sets by name, and the problems found.

    Raises:
        HTTPException: 422 for an invalid name, 404 for an unknown rule set.
    """
    _check_name(store, name)
    stored_sets = store.list_rule_sets()[0]
    others = {s.name: s.rule for s in stored_sets if s.name != name}
    rule, problems = _validate_body(body, others)
    if rule is None:
        return None, None, {}, problems
    current = next((s for s in stored_sets if s.name == name), None)
    saved = current.rule if current is not None else None
    if saved is not None and set(rule.project_ids) == set(saved.project_ids):
        problems = [p for p in problems if p.path != "project_ids"]
    return rule, saved, others, problems


def create_rules_router(
    service: DashboardService, store: RuleStore, sessions: AdminSessions
) -> APIRouter:
    """Build the router exposing rule sets for viewing and saving."""
    router = APIRouter(tags=["rules"])

    @router.get("/api/rules", response_model=RuleSetsResponse)
    def list_rules() -> RuleSetsResponse:
        rule_sets, load_errors = store.list_rule_sets()
        return RuleSetsResponse(
            rule_sets=[_to_item(stored) for stored in rule_sets],
            load_errors=load_errors,
            source=store.source,
            default_name=effective_default_name({s.name: s.rule for s in rule_sets}),
        )

    @router.put("/api/admin/rules/{name}", response_model=RuleSaveResponse)
    async def save_rule(
        name: str,
        payload: RuleSaveRequest,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> RuleSaveResponse:
        sessions.require(pulse_admin_session)
        rule, _saved, _others, problems = _check_draft(store, name, payload.rule)
        if problems or rule is None:
            raise _problems_error(problems)

        try:
            stored = store.write(name, rule, payload.revision)
        except InvalidRuleSetNameError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        except RuleSetNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except RevisionConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "These rules were changed by someone else. "
                    "Reload to see the latest version."
                ),
            ) from exc

        job = await run_pipeline_step("app/processor/main.py", "Processor (L2)", service)
        service.clear_cache()
        return RuleSaveResponse(rule_set=_to_item(stored), job=job)

    @router.post("/api/admin/rules", response_model=RuleSaveResponse)
    async def create_rule(
        payload: RuleCreateRequest,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> RuleSaveResponse:
        sessions.require(pulse_admin_session)
        stored_sets, load_errors = store.list_rule_sets()
        rule, problems = _validate_body(
            payload.rule, {s.name: s.rule for s in stored_sets}
        )
        if problems or rule is None:
            raise _problems_error(problems)
        taken = {s.name for s in stored_sets} | {Path(f).stem for f in load_errors}
        try:
            stored = store.create(unique_name(rule.team, taken), rule)
        except RuleSetExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(exc)
            ) from exc
        job = await run_pipeline_step("app/processor/main.py", "Processor (L2)", service)
        service.clear_cache()
        return RuleSaveResponse(rule_set=_to_item(stored), job=job)

    @router.delete("/api/admin/rules/{name}", response_model=RuleDeleteResponse)
    async def delete_rule(
        name: str,
        revision: str,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> RuleDeleteResponse:
        sessions.require(pulse_admin_session)
        _check_name(store, name)
        stored = {s.name: s.rule for s in store.list_rule_sets()[0]}
        if name == effective_default_name(stored):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The rule set that applies to all other projects cannot be deleted.",
            )
        if len(stored) <= 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The last rule set cannot be deleted.",
            )
        try:
            store.delete(name, revision)
        except RevisionConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "These rules were changed by someone else. "
                    "Reload to see the latest version."
                ),
            ) from exc
        job = await run_pipeline_step("app/processor/main.py", "Processor (L2)", service)
        service.clear_cache()
        return RuleDeleteResponse(job=job)

    @router.get(
        "/api/admin/rules/{name}/versions", response_model=RuleVersionsResponse
    )
    def list_rule_versions(
        name: str,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> RuleVersionsResponse:
        sessions.require(pulse_admin_session)
        _check_name(store, name)
        return RuleVersionsResponse(
            versions=[
                RuleVersionModel(
                    id=version.id,
                    kind=version.kind,
                    saved_at=version.saved_at.isoformat() if version.saved_at else None,
                )
                for version in store.list_versions(name)
            ]
        )

    @router.get(
        "/api/admin/rules/{name}/versions/{version_id}",
        response_model=RuleVersionResponse,
    )
    def get_rule_version(
        name: str,
        version_id: str,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> RuleVersionResponse:
        sessions.require(pulse_admin_session)
        _check_name(store, name)
        try:
            rule = store.read_version(name, version_id)
        except RuleVersionNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This version cannot be read.",
            ) from exc
        return RuleVersionResponse(rule=rule_to_body(rule))

    @router.post("/api/admin/rules/{name}/preview", response_model=RulePreviewResponse)
    async def preview_rule(
        name: str,
        payload: RulePreviewRequest,
        request: Request,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> RulePreviewResponse:
        sessions.require(pulse_admin_session)
        rule, saved, others, problems = _check_draft(store, name, payload.rule)
        if problems or rule is None:
            return RulePreviewResponse(
                problems=[
                    RuleProblemModel(path=problem.path, message=problem.message)
                    for problem in problems
                ]
            )
        async with _preview_lock:
            if await request.is_disconnected():
                return RulePreviewResponse()
            try:
                impact = await asyncio.to_thread(
                    summarize_impact,
                    service.processed_path,
                    store.active_path,
                    name,
                    rule,
                    others,
                    saved,
                )
            except ConfigurationConflictError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Two rule files claim the same project, so the effect cannot "
                        "be calculated. Ask the person who maintains the rule files "
                        "to fix this."
                    ),
                ) from exc
        return RulePreviewResponse(impact=impact)

    return router
