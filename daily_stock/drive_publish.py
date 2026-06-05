"""Google Drive publish option resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


GOOGLE_DRIVE_SCOPES = ("https://www.googleapis.com/auth/drive",)
PDF_MIME_TYPE = "application/pdf"
HTML_MIME_TYPE = "text/html"
PNG_MIME_TYPE = "image/png"
DEFAULT_PUBLIC_REPORT_FILE_NAME = "每日台股報告.pdf"


@dataclass(frozen=True)
class GoogleOAuthConfig:
    refresh_token: str
    client_id: str
    client_secret: str
    scopes: tuple[str, ...] = GOOGLE_DRIVE_SCOPES

    @property
    def is_configured(self) -> bool:
        return bool(self.refresh_token and self.client_id and self.client_secret)


def resolve_google_oauth_config(env: Mapping[str, str | None]) -> GoogleOAuthConfig:
    return GoogleOAuthConfig(
        refresh_token=str(env.get("GOOGLE_OAUTH_REFRESH_TOKEN") or "").strip(),
        client_id=str(env.get("GOOGLE_OAUTH_CLIENT_ID") or "").strip(),
        client_secret=str(env.get("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip(),
    )


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


def resolve_self_report_mime_type(file_path: Path, explicit_mime_type: str | None = None) -> str:
    if explicit_mime_type:
        return explicit_mime_type
    return PDF_MIME_TYPE if file_path.suffix.lower() == ".pdf" else PNG_MIME_TYPE


def resolve_public_report_mime_type(file_path: Path) -> str:
    return PDF_MIME_TYPE if file_path.suffix.lower() == ".pdf" else HTML_MIME_TYPE


def resolve_public_report_fixed_name(public_cfg: dict, fallback_name: str | None = None) -> str:
    return public_cfg.get("fixed_file_name") or fallback_name or DEFAULT_PUBLIC_REPORT_FILE_NAME
