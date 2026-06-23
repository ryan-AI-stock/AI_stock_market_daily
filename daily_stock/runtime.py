"""Runtime option parsing for scheduled and validation report runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping

from daily_stock.report_contracts import get_report_date


FORCE_RUN_TRUE_VALUES = {"1", "true", "yes", "y"}


@dataclass(frozen=True)
class RuntimeOptions:
    validation_folder_id: str = ""
    force_run_report: bool = False
    github_actions: bool = False
    github_event_name: str = ""
    report_date_override: str = ""

    @property
    def validation_mode(self) -> bool:
        return bool(self.validation_folder_id)

    @property
    def should_force_run(self) -> bool:
        return self.force_run_report or self.validation_mode

    @property
    def is_workflow_dispatch(self) -> bool:
        return self.github_event_name == "workflow_dispatch"


@dataclass(frozen=True)
class ReportRunContext:
    now_tw: datetime
    report_date: str
    runtime_options: RuntimeOptions

    @property
    def date_key(self) -> str:
        return self.report_date.replace("-", "")

    def with_report_date(self, report_date: str) -> "ReportRunContext":
        return ReportRunContext(
            now_tw=self.now_tw,
            report_date=report_date,
            runtime_options=self.runtime_options,
        )


def parse_runtime_options(env: Mapping[str, str | None]) -> RuntimeOptions:
    return RuntimeOptions(
        validation_folder_id=str(env.get("REPORT_VALIDATION_DRIVE_FOLDER_ID") or "").strip(),
        force_run_report=_is_force_run_enabled(env.get("FORCE_RUN_REPORT")),
        github_actions=_is_github_actions(env.get("GITHUB_ACTIONS")),
        github_event_name=str(env.get("GITHUB_EVENT_NAME") or "").strip(),
        report_date_override=_report_date_override(env.get("REPORT_DATE")),
    )


def build_report_run_context(now_tw: datetime, env: Mapping[str, str | None]) -> ReportRunContext:
    runtime_options = parse_runtime_options(env)
    return ReportRunContext(
        now_tw=now_tw,
        report_date=runtime_options.report_date_override or get_report_date(now_tw),
        runtime_options=runtime_options,
    )


def _is_force_run_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in FORCE_RUN_TRUE_VALUES


def _is_github_actions(value: str | None) -> bool:
    return str(value or "").strip().lower() == "true"


def _report_date_override(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
        raise ValueError("REPORT_DATE must use YYYY-MM-DD format")
    return date.fromisoformat(raw).isoformat()
