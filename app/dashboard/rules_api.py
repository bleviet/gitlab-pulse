"""Rule set viewing and saving endpoints for the in-dashboard rule editor."""

from fastapi import APIRouter, Cookie, HTTPException, status

from app.dashboard.admin import ADMIN_COOKIE_NAME, AdminSessions, run_pipeline_step
from app.dashboard.schemas import (
    ClassificationCategoryModel,
    ClassificationValueModel,
    ContextRuleModel,
    ContextsModel,
    RuleProblemModel,
    RuleSaveRequest,
    RuleSaveResponse,
    RuleSetBody,
    RuleSetItem,
    RuleSetsResponse,
    ValidationModel,
    WorkflowModel,
    WorkflowStageModel,
)
from app.dashboard.service import DashboardService
from app.processor.rule_loader import (
    ClassificationMatch,
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
    RuleSetNotFoundError,
    RuleStore,
    StoredRuleSet,
    validate_rule_set,
)


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
        )

    @router.put("/api/admin/rules/{name}", response_model=RuleSaveResponse)
    async def save_rule(
        name: str,
        payload: RuleSaveRequest,
        pulse_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    ) -> RuleSaveResponse:
        sessions.require(pulse_admin_session)
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

        problems = _duplicate_classification_problems(payload.rule)
        rule = body_to_rule(payload.rule)
        if not problems:
            stored_sets = store.list_rule_sets()[0]
            others = {s.name: s.rule for s in stored_sets if s.name != name}
            problems = validate_rule_set(rule, others)
            current = next((s for s in stored_sets if s.name == name), None)
            if current is not None and set(rule.project_ids) == set(
                current.rule.project_ids
            ):
                problems = [p for p in problems if p.path != "project_ids"]
        if problems:
            summary = (
                "1 problem needs"
                if len(problems) == 1
                else f"{len(problems)} problems need"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": (
                        f"{summary} fixing before these rules can be saved."
                    ),
                    "problems": [
                        RuleProblemModel(
                            path=problem.path, message=problem.message
                        ).model_dump()
                        for problem in problems
                    ],
                },
            )

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

    return router
