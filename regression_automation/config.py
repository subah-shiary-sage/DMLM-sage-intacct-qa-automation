"""
config.py — Loads regression_config.yaml, the module registry.

One file maps each ``--module`` name to the checklist sheet(s) it owns, the page
objects that drive it, and (optionally) its own JIRA target. The JIRA bearer
token is never stored here — this file is committed to git, so only the *name*
of the environment variable holding the token is recorded.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import workbook as wbmod

DEFAULT_CONFIG_PATH = Path("regression_config.yaml")


class ConfigError(ValueError):
    """regression_config.yaml is missing, malformed, or names something unknown."""


@dataclass
class JiraTarget:
    issue: str
    comment_id: str
    token_env_var: str = "JIRA_API_TOKEN"
    base_url: str = "https://jira.sage.com"

    def resolve_token(self) -> str:
        token = os.environ.get(self.token_env_var, "").strip()
        if not token:
            raise ConfigError(
                f"No JIRA token found. Set {self.token_env_var} in your .env "
                "(it must not be committed to the repo)."
            )
        return token


@dataclass
class SheetRef:
    sheet_name: str
    row_start: int | None = None
    row_end: int | None = None


@dataclass
class ModuleConfig:
    name: str
    sheets: list[SheetRef]
    page_object: str | None = None
    listing_page_object: str | None = None
    scenarios: str | None = None
    jira: JiraTarget | None = None
    environment: str = ""
    notes: str = ""

    def load_page_object(self) -> Any:
        return _import_dotted(self.page_object) if self.page_object else None

    def load_listing_page_object(self) -> Any:
        return _import_dotted(self.listing_page_object) if self.listing_page_object else None

    def load_scenarios(self) -> Any:
        return importlib.import_module(self.scenarios) if self.scenarios else None


@dataclass
class RegressionConfig:
    modules: dict[str, ModuleConfig]
    default_jira: JiraTarget
    environment: str = ""
    workbook_path: Path = field(default_factory=lambda: wbmod.WORKBOOK_PATH)

    def module(self, name: str) -> ModuleConfig:
        try:
            return self.modules[name]
        except KeyError:
            raise ConfigError(
                f"Unknown module {name!r}. Valid choices: "
                + ", ".join(sorted(self.modules))
            ) from None


def _import_dotted(path: str) -> Any:
    """Resolve 'pkg.mod.ClassName' to the class, with a clear error if it can't."""
    if "." not in path:
        raise ConfigError(f"{path!r} is not a dotted path to a class.")
    module_name, _, attr = path.rpartition(".")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ConfigError(f"Cannot import {module_name!r} (from {path!r}): {exc}") from None
    try:
        return getattr(module, attr)
    except AttributeError:
        raise ConfigError(f"{module_name!r} has no attribute {attr!r} (from {path!r})") from None


def _parse_jira(raw: dict | None, fallback: JiraTarget | None) -> JiraTarget | None:
    if not raw:
        return fallback
    if fallback is None:
        missing = [k for k in ("issue", "comment_id") if k not in raw]
        if missing:
            raise ConfigError(f"jira block is missing required key(s): {', '.join(missing)}")
    return JiraTarget(
        issue=str(raw.get("issue", fallback.issue if fallback else "")),
        comment_id=str(raw.get("comment_id", fallback.comment_id if fallback else "")),
        token_env_var=str(
            raw.get("token_env_var", fallback.token_env_var if fallback else "JIRA_API_TOKEN")
        ),
        base_url=str(
            raw.get("base_url", fallback.base_url if fallback else "https://jira.sage.com")
        ),
    )


def load_config(
    path: Path = DEFAULT_CONFIG_PATH, *, validate_imports: bool = True
) -> RegressionConfig:
    """
    Parse and validate the registry.

    Validation happens here rather than at first use, so a typo in a page-object
    path or sheet name fails immediately instead of halfway through a live run.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    default_jira = _parse_jira(raw.get("jira"), None)
    if default_jira is None:
        raise ConfigError("regression_config.yaml needs a top-level 'jira:' block.")

    environment = str(raw.get("environment", ""))
    wb_path = Path(raw.get("workbook", wbmod.WORKBOOK_PATH))

    raw_modules = raw.get("modules") or {}
    if not raw_modules:
        raise ConfigError("regression_config.yaml defines no modules.")

    modules: dict[str, ModuleConfig] = {}
    for name, spec in raw_modules.items():
        spec = spec or {}
        raw_sheets = spec.get("sheets")
        if not raw_sheets:
            raise ConfigError(f"Module {name!r} lists no sheets.")

        sheets: list[SheetRef] = []
        for entry in raw_sheets:
            if isinstance(entry, str):
                sheets.append(SheetRef(sheet_name=entry))
                continue
            sheet_name = entry.get("name")
            if not sheet_name:
                raise ConfigError(f"Module {name!r} has a sheet entry with no 'name'.")
            sheets.append(
                SheetRef(
                    sheet_name=sheet_name,
                    row_start=entry.get("row_start"),
                    row_end=entry.get("row_end"),
                )
            )

        for ref in sheets:
            if ref.sheet_name not in wbmod.FAMILY_LAYOUT:
                raise ConfigError(
                    f"Module {name!r} references unknown sheet {ref.sheet_name!r}.\n"
                    f"Known sheets: {', '.join(wbmod.FAMILY_LAYOUT)}"
                )

        module = ModuleConfig(
            name=name,
            sheets=sheets,
            page_object=spec.get("page_object"),
            listing_page_object=spec.get("listing_page_object"),
            scenarios=spec.get("scenarios"),
            jira=_parse_jira(spec.get("jira"), default_jira),
            environment=str(spec.get("environment", environment)),
            notes=str(spec.get("notes", "")),
        )

        if validate_imports:
            for dotted in (module.page_object, module.listing_page_object):
                if dotted:
                    _import_dotted(dotted)
            if module.scenarios:
                try:
                    importlib.import_module(module.scenarios)
                except ImportError as exc:
                    raise ConfigError(
                        f"Module {name!r}: cannot import scenarios "
                        f"{module.scenarios!r}: {exc}"
                    ) from None

        modules[name] = module

    return RegressionConfig(
        modules=modules,
        default_jira=default_jira,
        environment=environment,
        workbook_path=wb_path,
    )
