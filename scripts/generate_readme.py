#!/usr/bin/env python3
"""Generate the configured public-project cards in the profile README."""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
import yaml

GRAPHQL_URL = "https://api.github.com/graphql"
START_MARKER = "<!-- PROJECTS:START -->"
END_MARKER = "<!-- PROJECTS:END -->"
GRAPHQL_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    description
    url
    homepageUrl
    visibility
    openGraphImageUrl
    usesCustomOpenGraphImage
    primaryLanguage {
      name
      color
    }
    repositoryTopics(first: 10) {
      nodes {
        topic {
          name
        }
      }
    }
    stargazers {
      totalCount
    }
    forks {
      totalCount
    }
  }
}
"""
DEFAULT_SETTINGS = {
    "columns": 2,
    "show_language": True,
    "show_topics": True,
    "show_stars": True,
    "show_forks": True,
}
LANGUAGE_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}\Z")


def load_config(path: Path) -> tuple[str, list[str], dict[str, Any]]:
    with path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError(f"{path}: expected a YAML mapping")

    owner = config.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError(f"{path}: 'owner' must be a non-empty string")

    entries = config.get("projects")
    if not isinstance(entries, list):
        raise ValueError(f"{path}: 'projects' must be a list")

    repositories: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: projects[{index}] must be a mapping")
        name = entry.get("repo")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{path}: projects[{index}].repo must be a non-empty string")
        if name in repositories:
            raise ValueError(f"{path}: duplicate repository {name!r}")
        repositories.append(name)

    settings = dict(DEFAULT_SETTINGS)
    configured_settings = config.get("settings", {})
    if not isinstance(configured_settings, dict):
        raise ValueError(f"{path}: 'settings' must be a mapping")
    settings.update(configured_settings)

    columns = settings["columns"]
    if isinstance(columns, bool) or not isinstance(columns, int) or columns < 1:
        raise ValueError(f"{path}: settings.columns must be a positive integer")
    for key in ("show_language", "show_topics", "show_stars", "show_forks"):
        if not isinstance(settings[key], bool):
            raise ValueError(f"{path}: settings.{key} must be true or false")

    return owner.strip(), repositories, settings


def require_public_repository(repository: Any, owner: str, name: str) -> dict[str, Any]:
    if not isinstance(repository, dict):
        raise ValueError(f"Repository {owner}/{name} was not found or is inaccessible")
    visibility = repository.get("visibility")
    if visibility != "PUBLIC":
        raise ValueError(
            f"Repository {owner}/{name} has visibility {visibility!r}; "
            "only PUBLIC repositories may be published"
        )
    return repository


def fetch_repository(owner: str, name: str, token: str) -> dict[str, Any]:
    response = requests.post(
        GRAPHQL_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"query": GRAPHQL_QUERY, "variables": {"owner": owner, "name": name}},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError(f"GitHub GraphQL returned an invalid response for {owner}/{name}")
    errors = payload.get("errors")
    if errors:
        messages = "; ".join(
            str(error.get("message", "Unknown GraphQL error"))
            for error in errors
            if isinstance(error, dict)
        )
        raise ValueError(f"GitHub GraphQL error for {owner}/{name}: {messages}")

    data = payload.get("data")
    repository = data.get("repository") if isinstance(data, dict) else None
    return require_public_repository(repository, owner, name)


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def safe_http_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
    except ValueError:
        return None
    return value


def render_projects(repositories: list[dict[str, Any]], settings: dict[str, Any]) -> str:
    if not repositories:
        return "<p>No projects configured.</p>"

    lines = [
        "",
        "| Project | Description | Language |",
        "|---------|-------------|----------|",
    ]
    
    for repo in repositories:
        name = escape(repo.get("name", "—"))
        url = repo.get("url", "#")
        desc = escape(repo.get("description", "—"))
        
        language_badge = "—"
        if settings["show_language"]:
            language = repo.get("primaryLanguage", {})
            if language and isinstance(language, dict):
                lang_name = language.get("name")
                if lang_name:
                    lang_name_escaped = lang_name.replace(" ", "%20")
                    language_badge = f'![{lang_name}](https://img.shields.io/badge/-{lang_name_escaped}-333?style=flat)'
        
        lines.append(f"| [{name}]({url}) | {desc} | {language_badge} |")
    
    lines.append("")
    return "\n".join(lines)


def update_readme(path: Path, generated_content: str) -> bool:
    with path.open(encoding="utf-8", newline="") as readme_file:
        original = readme_file.read()

    if original.count(START_MARKER) != 1 or original.count(END_MARKER) != 1:
        raise ValueError(
            f"{path}: expected exactly one {START_MARKER} and one {END_MARKER}"
        )
    start = original.index(START_MARKER) + len(START_MARKER)
    end = original.index(END_MARKER)
    if end < start:
        raise ValueError(f"{path}: {END_MARKER} must follow {START_MARKER}")

    newline = "\r\n" if "\r\n" in original else "\n"
    generated_content = generated_content.replace("\r\n", "\n").replace("\n", newline)
    updated = original[:start] + newline + generated_content + newline + original[end:]
    if updated == original:
        return False

    with path.open("w", encoding="utf-8", newline="") as readme_file:
        readme_file.write(updated)
    return True


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / ".github" / "projects.yml")
    parser.add_argument("--readme", type=Path, default=root / "README.md")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_GRAPHQL_TOKEN")
    if not token:
        parser.error("GITHUB_GRAPHQL_TOKEN is required")

    owner, names, settings = load_config(args.config)
    repositories = [fetch_repository(owner, name, token) for name in names]
    changed = update_readme(args.readme, render_projects(repositories, settings))
    print("README updated." if changed else "README is already up to date.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, requests.RequestException, ValueError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

