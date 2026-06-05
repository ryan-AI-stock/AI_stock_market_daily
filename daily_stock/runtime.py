"""Runtime option parsing for scheduled and validation report runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


FORCE_RUN_TRUE_VALUES = {"1", "true", "yes", "y"}


@dataclass(frozen=True)
class RuntimeOptions:
    validation_folder_id: str = ""
    force_run_report: bool = False
    github_actions: bool = False

    @property
    def validation_mode(self) -> bool:
        return bool(self.validation_folder_id)

    @property
    def should_force_run(self) -> bool:
        return self.force_run_report or self.validation_mode


def parse_runtime_options(env: Mapping[str, str | None]) -> RuntimeOptions:
    return RuntimeOptions(
        validation_folder_id=str(env.get("REPORT_VALIDATION_DRIVE_FOLDER_ID") or "").strip(),
        force_run_report=_is_force_run_enabled(env.get("FORCE_RUN_REPORT")),
        github_actions=_is_github_actions(env.get("GITHUB_ACTIONS")),
    )


def _is_force_run_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in FORCE_RUN_TRUE_VALUES


def _is_github_actions(value: str | None) -> bool:
    return str(value or "").strip().lower() == "true"
