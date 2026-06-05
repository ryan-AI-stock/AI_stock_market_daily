"""Google Drive publish option resolution helpers."""

from __future__ import annotations

from typing import Mapping


def resolve_daily_report_folder_id(drive_cfg: dict, env: Mapping[str, str | None]) -> str | None:
    return env.get("DAILY_REPORT_DRIVE_FOLDER_ID") or drive_cfg.get("folder_id")


def resolve_public_report_folder_id(public_cfg: dict, env: Mapping[str, str | None]) -> str | None:
    return (
        env.get("PUBLIC_REPORT_DRIVE_FOLDER_ID")
        or env.get("FREE_REPORT_DRIVE_FOLDER_ID")
        or public_cfg.get("folder_id")
    )


def resolve_public_report_file_id(public_cfg: dict, env: Mapping[str, str | None]) -> str | None:
    return env.get("PUBLIC_REPORT_DRIVE_FILE_ID") or public_cfg.get("fixed_file_id")
