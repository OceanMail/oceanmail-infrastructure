#!/usr/bin/env python3
"""Portable public-source verification utility.

Given explicit repository refs (``owner/repo@ref``), verifies — using only
unauthenticated public GitHub API access, no credentials, no administrative
writes — that:

  * the ref resolves to a real commit (and matches an expected SHA, if one
    was supplied on the command line as ``owner/repo@expected_sha``);
  * that commit's author/committer email matches this project's allowed
    identity pattern (GitHub-provided ``@users.noreply.github.com``
    addresses), rather than something that looks like a personal address
    this organization's publication effort is trying to scrub;
  * a GitHub-recognized license file is present;
  * ``.github/workflows/*.yml`` files do not use patterns this project
    treats as public-CI-unsafe: a ``self-hosted`` runner label or the
    ``pull_request_target`` trigger.

Every check reports exactly one of three states: ``verified``, ``failed``,
or ``not_inspected``. ``not_inspected`` (a network error, a rate limit, an
unexpected response shape) is never silently treated as passing and is
never folded into ``verified`` — an inconclusive check must read as
inconclusive, not clean.

This is a small reliability checker, not a deployment system and not a
complete YAML security parser: the workflow check is plain substring/regex
matching against the raw file text, not a YAML-aware analysis, and it can
be fooled by anything that would fool a text search (a matching string
inside a comment or a string literal, for instance). It reports what the
literal text contains, nothing more.

No credential of any kind is used, read, or logged — every request is
unauthenticated and only ever reads. Refuses outright, before making any
network request, to target a repository whose name matches this
organization's historical/frozen/archive naming convention
(``*-archive``, ``*-prototype``, ``*-sanitizing``, ``bempic*``) — this
utility must never be pointed at private archives, and treats a name that
merely looks like one as reason enough to refuse rather than to press on
and see what happens.

Platform note (recorded here because it was discovered running this tool,
not assumed): in an ordinary environment — a contributor's own machine, an
unrestricted CI runner — unauthenticated ``api.github.com`` calls reach any
public repository, subject only to GitHub's own published unauthenticated
rate limit. Run from inside a Claude Code Remote session, however,
``api.github.com`` is additionally intercepted by that session's own agent
proxy and scoped to whatever repositories the session has been granted
access to (its "Repository Scope"); a repository outside that scope
returns HTTP 403 from the proxy itself, with a body naming the proxy, not
from GitHub. This tool cannot distinguish that case from a real GitHub-side
403 and correctly reports it as ``not_inspected`` either way — which is
the right behavior (an inconclusive check must never read as passing) even
though the underlying cause differs. This is a property of that sandbox,
not of this tool or of GitHub's public API; outside such a session this
utility needs no repository allowlisting at all.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

API_ROOT = "https://api.github.com"
USER_AGENT = "oceanmail-infrastructure-verify-public-source/1"

# Matches this organization's own historical/frozen naming convention
# (REPOSITORIES.md: "Frozen/historical repositories"). Refused outright
# rather than merely discouraged — see the module docstring.
_FORBIDDEN_NAME_PATTERN = re.compile(
    r"(-archive|-prototype|-sanitizing)$|^bempic", re.IGNORECASE
)

# GitHub issues these addresses itself for commits made through its web UI
# or API with a verified account; they cannot be typed in by hand the way
# a personal address can, which is why they're the allowed pattern here
# rather than any particular literal address.
_ALLOWED_COMMIT_EMAIL = re.compile(r"^[^@]+@users\.noreply\.github\.com$", re.IGNORECASE)

_SELF_HOSTED_PATTERN = re.compile(r"runs-on\s*:\s*(\[[^\]]*self-hosted|self-hosted)", re.IGNORECASE)
_PULL_REQUEST_TARGET_PATTERN = re.compile(r"pull_request_target\s*:", re.IGNORECASE)


class NotInspected(Exception):
    """Raised internally when a check cannot be completed; never a failure verdict."""


@dataclass
class CheckResult:
    name: str
    state: str  # "verified" | "failed" | "not_inspected"
    detail: str

    def __post_init__(self) -> None:
        if self.state not in ("verified", "failed", "not_inspected"):
            raise ValueError(f"invalid CheckResult state: {self.state!r}")


@dataclass
class RepoReport:
    repo_ref: str
    checks: list[CheckResult] = field(default_factory=list)

    def overall(self) -> str:
        states = {c.state for c in self.checks}
        if "failed" in states:
            return "failed"
        if "not_inspected" in states:
            return "not_inspected"
        return "verified"


def refuse_if_forbidden_name(owner: str, repo: str) -> None:
    if _FORBIDDEN_NAME_PATTERN.search(repo):
        raise ValueError(
            f"refusing to target {owner}/{repo}: name matches this organization's "
            "historical/archive/frozen naming convention; this utility never scans those"
        )


def _api_get(path: str) -> dict | list:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 (public API only)
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise
        raise NotInspected(f"GET {path} -> HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise NotInspected(f"GET {path} -> {exc}") from exc


def check_commit_identity(owner: str, repo: str, ref: str, expected_sha: Optional[str]) -> list[CheckResult]:
    try:
        commit = _api_get(f"/repos/{owner}/{repo}/commits/{ref}")
    except urllib.error.HTTPError:
        return [CheckResult("commit_resolves", "failed", f"{ref} does not resolve to a commit")]
    except NotInspected as exc:
        return [CheckResult("commit_resolves", "not_inspected", str(exc))]

    assert isinstance(commit, dict)
    sha = commit.get("sha", "")
    results = [CheckResult("commit_resolves", "verified", f"{ref} resolves to {sha}")]

    if expected_sha is not None:
        if sha == expected_sha:
            results.append(CheckResult("commit_matches_expected", "verified", sha))
        else:
            results.append(
                CheckResult(
                    "commit_matches_expected", "failed", f"expected {expected_sha}, resolved to {sha}"
                )
            )

    results.append(check_commit_identity_policy(commit))
    return results


def check_commit_identity_policy(commit: dict) -> CheckResult:
    """Fixture-friendly: takes an already-fetched commit object, not a repo/ref."""
    commit_info = commit.get("commit", {})
    emails = [
        commit_info.get("author", {}).get("email"),
        commit_info.get("committer", {}).get("email"),
    ]
    emails = [email for email in emails if email]
    if not emails:
        return CheckResult("commit_identity_policy", "not_inspected", "no author/committer email in response")
    bad = [email for email in emails if not _ALLOWED_COMMIT_EMAIL.match(email)]
    if bad:
        return CheckResult(
            "commit_identity_policy",
            "failed",
            "author/committer email does not match the allowed noreply pattern: " + ", ".join(bad),
        )
    return CheckResult("commit_identity_policy", "verified", "author/committer emails match allowed pattern")


def check_license(owner: str, repo: str) -> CheckResult:
    try:
        license_info = _api_get(f"/repos/{owner}/{repo}/license")
    except urllib.error.HTTPError:
        return CheckResult("license_present", "failed", "no GitHub-recognized license file found")
    except NotInspected as exc:
        return CheckResult("license_present", "not_inspected", str(exc))
    assert isinstance(license_info, dict)
    spdx = (license_info.get("license") or {}).get("spdx_id", "unknown")
    return CheckResult("license_present", "verified", f"license file present, detected SPDX id: {spdx}")


def evaluate_workflow_text(filename: str, text: str) -> CheckResult:
    """Fixture-friendly: pure text-pattern check, no network. Not a YAML parser
    — see the module docstring for exactly what that means and doesn't mean."""
    findings = []
    if _SELF_HOSTED_PATTERN.search(text):
        findings.append("self-hosted runner label")
    if _PULL_REQUEST_TARGET_PATTERN.search(text):
        findings.append("pull_request_target trigger")
    if findings:
        return CheckResult(
            f"workflow:{filename}", "failed", "prohibited pattern(s) found: " + ", ".join(findings)
        )
    return CheckResult(f"workflow:{filename}", "verified", "no prohibited pattern found (text match only)")


def check_workflows(owner: str, repo: str) -> list[CheckResult]:
    try:
        listing = _api_get(f"/repos/{owner}/{repo}/contents/.github/workflows")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return [CheckResult("workflows", "verified", "no .github/workflows directory")]
        return [CheckResult("workflows", "not_inspected", f"HTTP {exc.code}")]
    except NotInspected as exc:
        return [CheckResult("workflows", "not_inspected", str(exc))]

    assert isinstance(listing, list)
    results = []
    for entry in listing:
        name = entry.get("name", "")
        if not (name.endswith(".yml") or name.endswith(".yaml")):
            continue
        try:
            file_info = _api_get(f"/repos/{owner}/{repo}/contents/.github/workflows/{name}")
            assert isinstance(file_info, dict)
            if file_info.get("encoding") != "base64":
                results.append(CheckResult(f"workflow:{name}", "not_inspected", "unexpected content encoding"))
                continue
            text = base64.b64decode(file_info["content"]).decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, NotInspected) as exc:
            results.append(CheckResult(f"workflow:{name}", "not_inspected", str(exc)))
            continue
        results.append(evaluate_workflow_text(name, text))
    if not results:
        results.append(CheckResult("workflows", "verified", "workflows directory present but no .yml/.yaml files"))
    return results


def verify_repo_ref(repo_ref: str) -> RepoReport:
    if "@" in repo_ref:
        owner_repo, ref = repo_ref.split("@", 1)
    else:
        owner_repo, ref = repo_ref, "HEAD"
    if "/" not in owner_repo:
        raise ValueError(f"expected owner/repo[@ref], got {repo_ref!r}")
    owner, repo = owner_repo.split("/", 1)
    refuse_if_forbidden_name(owner, repo)

    # A ref that is itself a 40-char hex string is treated as the expected
    # commit identity to match, as well as the ref to resolve.
    expected_sha = ref if re.fullmatch(r"[0-9a-fA-F]{40}", ref) else None

    report = RepoReport(repo_ref=f"{owner}/{repo}@{ref}")
    report.checks.extend(check_commit_identity(owner, repo, ref, expected_sha))
    report.checks.append(check_license(owner, repo))
    report.checks.extend(check_workflows(owner, repo))
    return report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "repo_refs",
        nargs="+",
        metavar="owner/repo[@ref]",
        help="Explicit repository ref(s) to verify, e.g. OceanMail/oceanmail-station@main "
        "or OceanMail/oceanmail-station@<40-char sha>",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    reports = []
    had_error = False
    for repo_ref in args.repo_refs:
        try:
            reports.append(verify_repo_ref(repo_ref))
        except ValueError as exc:
            had_error = True
            print(f"ERROR: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(
            [{"repo_ref": r.repo_ref, "overall": r.overall(),
              "checks": [{"name": c.name, "state": c.state, "detail": c.detail} for c in r.checks]}
             for r in reports],
            indent=2,
        ))
    else:
        for r in reports:
            print(f"\n{r.repo_ref} — overall: {r.overall()}")
            for c in r.checks:
                print(f"  [{c.state:13}] {c.name}: {c.detail}")

    any_failed = any(r.overall() == "failed" for r in reports)
    any_not_inspected = any(r.overall() == "not_inspected" for r in reports)
    if had_error or any_failed:
        return 1
    if any_not_inspected:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
