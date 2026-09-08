"""Generate a GitHub profile card from public repository data."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


API_VERSION = "2022-11-28"
PAGE_SIZE = 100


def fetchPublicRepositories(username: str, token: str | None) -> list[dict[str, Any]]:
    """Fetch every public repository owned by a GitHub user.

    Args:
        username (str): GitHub account name to query.
        token (str | None): Optional token used to increase the API rate limit.

    Returns:
        list[dict[str, Any]]: Public repositories returned by GitHub.

    Raises:
        RuntimeError: If GitHub returns an invalid response or request error.
    """
    repositories: list[dict[str, Any]] = []
    pageNumber = 1

    while True:
        apiUrl = (
            f"https://api.github.com/users/{username}/repos"
            f"?type=owner&sort=full_name&per_page={PAGE_SIZE}&page={pageNumber}"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SilenceEagle-profile-stats",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        print(f"Fetching public repositories page {pageNumber}...", flush=True)
        request = urllib.request.Request(apiUrl, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                pageRepositories = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            raise RuntimeError(f"GitHub API request failed: {error}") from error

        if not isinstance(pageRepositories, list):
            raise RuntimeError("GitHub API returned an unexpected response")

        repositories.extend(pageRepositories)
        print(f"Fetched {len(repositories)} repositories so far.", flush=True)
        if len(pageRepositories) < PAGE_SIZE:
            return repositories
        pageNumber += 1


def renderStatsCard(username: str, repositoryCount: int, starCount: int) -> str:
    """Render public repository statistics as an SVG card.

    Args:
        username (str): GitHub account name displayed in the title.
        repositoryCount (int): Number of owned public repositories.
        starCount (int): Total stars across the public repositories.

    Returns:
        str: Complete SVG document.
    """
    safeUsername = escape(username)
    updatedAt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="170" viewBox="0 0 495 170">
    <style>
        .card {{ fill: #0a0f0b; stroke: #2f8f46; stroke-width: 1; }}
        .title {{ fill: #abd200; font: 600 18px 'Segoe UI', Ubuntu, sans-serif; }}
        .label {{ fill: #68b587; font: 600 14px 'Segoe UI', Ubuntu, sans-serif; }}
        .value {{ fill: #ffffff; font: 700 24px 'Segoe UI', Ubuntu, sans-serif; }}
        .meta {{ fill: #68b587; font: 12px 'Segoe UI', Ubuntu, sans-serif; }}
    </style>
    <rect class="card" x="0.5" y="0.5" width="494" height="169" rx="4.5"/>
    <text class="title" x="25" y="35">{safeUsername}'s GitHub Stats</text>
    <text class="label" x="25" y="75">Public repositories</text>
    <text class="value" x="25" y="108">{repositoryCount:,}</text>
    <text class="label" x="270" y="75">Total stars</text>
    <text class="value" x="270" y="108">&#9733; {starCount:,}</text>
    <text class="meta" x="25" y="145">Updated {updatedAt}</text>
</svg>
"""


def writeStatsCard(outputPath: Path, svgContent: str) -> None:
    """Write an SVG card to disk.

    Args:
        outputPath (Path): Destination path for the SVG card.
        svgContent (str): SVG document to write.
    """
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    outputPath.write_text(svgContent, encoding="utf-8")
    print(f"Wrote statistics card to {outputPath}.", flush=True)


def parseArguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed username and output arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True, help="GitHub username to summarize")
    parser.add_argument("--output", type=Path, required=True, help="SVG output path")
    return parser.parse_args()


def main() -> int:
    """Generate the public GitHub statistics card.

    Returns:
        int: Zero on success and one on failure.
    """
    arguments = parseArguments()
    try:
        repositories = fetchPublicRepositories(arguments.username, os.environ.get("GITHUB_TOKEN"))
        totalStars = sum(int(repository.get("stargazers_count", 0)) for repository in repositories)
        writeStatsCard(arguments.output, renderStatsCard(arguments.username, len(repositories), totalStars))
    except (RuntimeError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr, flush=True)
        return 1

    print(f"Completed: {len(repositories)} public repositories, {totalStars} total stars.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
