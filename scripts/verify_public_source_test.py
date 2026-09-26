#!/usr/bin/env python3
"""Fixture-based tests for verify-public-source.py.

No network access: every test below feeds already-constructed fixture data
(commit objects, workflow file text) straight to the pure check functions,
or exercises the pre-network input validation. Nothing here proves the
live GitHub API integration works — only that these functions classify
each fixture correctly. Run with: python3 -m unittest scripts.verify_public_source_test
"""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_MODULE_PATH = Path(__file__).resolve().parent / "verify-public-source.py"
_SPEC = importlib.util.spec_from_file_location("verify_public_source", _MODULE_PATH)
verify_public_source = importlib.util.module_from_spec(_SPEC)
sys.modules["verify_public_source"] = verify_public_source
_SPEC.loader.exec_module(verify_public_source)


def commit_fixture(author_email: str, committer_email: str | None = None) -> dict:
    return {
        "sha": "a" * 40,
        "commit": {
            "author": {"email": author_email},
            "committer": {"email": committer_email or author_email},
        },
    }


class CommitIdentityPolicyTests(unittest.TestCase):
    def test_permitted_noreply_identity_is_verified(self):
        result = verify_public_source.check_commit_identity_policy(
            commit_fixture("286094352+Gordonfive@users.noreply.github.com")
        )
        self.assertEqual(result.state, "verified")

    def test_case_insensitive_noreply_domain_is_verified(self):
        result = verify_public_source.check_commit_identity_policy(
            commit_fixture("someone@USERS.NOREPLY.GITHUB.COM")
        )
        self.assertEqual(result.state, "verified")

    def test_prohibited_personal_looking_address_fails(self):
        result = verify_public_source.check_commit_identity_policy(
            commit_fixture("jane.doe@example.com")
        )
        self.assertEqual(result.state, "failed")
        self.assertIn("jane.doe@example.com", result.detail)

    def test_mismatched_author_and_committer_both_reported_when_either_fails(self):
        result = verify_public_source.check_commit_identity_policy(
            commit_fixture("ok@users.noreply.github.com", "leaked@example.com")
        )
        self.assertEqual(result.state, "failed")
        self.assertIn("leaked@example.com", result.detail)
        self.assertNotIn("ok@users.noreply.github.com", result.detail)

    def test_missing_email_fields_are_not_inspected_not_verified(self):
        result = verify_public_source.check_commit_identity_policy(
            {"sha": "a" * 40, "commit": {"author": {}, "committer": {}}}
        )
        self.assertEqual(result.state, "not_inspected")

    def test_lookalike_noreply_suffix_is_not_fooled(self):
        # "@users.noreply.github.com.evil.example" must not match the
        # anchored allowed pattern merely because it contains the substring.
        result = verify_public_source.check_commit_identity_policy(
            commit_fixture("attacker@users.noreply.github.com.evil.example")
        )
        self.assertEqual(result.state, "failed")

    def test_embedded_newline_in_local_part_is_not_matched(self):
        # [^@]+ alone would let a crafted local part smuggle a second,
        # unrelated-looking address past the anchored pattern.
        result = verify_public_source.check_commit_identity_policy(
            commit_fixture("junk\nreal@users.noreply.github.com")
        )
        self.assertEqual(result.state, "failed")


class WorkflowTextTests(unittest.TestCase):
    def test_clean_workflow_is_verified(self):
        text = """
        name: CI
        on: [push, pull_request]
        permissions:
          contents: read
        jobs:
          test:
            runs-on: ubuntu-24.04
            steps:
              - run: echo ok
        """
        result = verify_public_source.evaluate_workflow_text("ci.yml", text)
        self.assertEqual(result.state, "verified")

    def test_self_hosted_runner_fails(self):
        text = "jobs:\n  build:\n    runs-on: self-hosted\n"
        result = verify_public_source.evaluate_workflow_text("build.yml", text)
        self.assertEqual(result.state, "failed")
        self.assertIn("self-hosted", result.detail)

    def test_self_hosted_in_label_list_fails(self):
        text = "jobs:\n  build:\n    runs-on: [self-hosted, linux, x64]\n"
        result = verify_public_source.evaluate_workflow_text("build.yml", text)
        self.assertEqual(result.state, "failed")

    def test_pull_request_target_trigger_fails(self):
        text = "on:\n  pull_request_target:\n    types: [opened]\n"
        result = verify_public_source.evaluate_workflow_text("pr.yml", text)
        self.assertEqual(result.state, "failed")
        self.assertIn("pull_request_target", result.detail)

    def test_both_prohibited_patterns_are_both_reported(self):
        text = "on:\n  pull_request_target:\njobs:\n  build:\n    runs-on: self-hosted\n"
        result = verify_public_source.evaluate_workflow_text("both.yml", text)
        self.assertEqual(result.state, "failed")
        self.assertIn("self-hosted", result.detail)
        self.assertIn("pull_request_target", result.detail)

    def test_unrelated_mention_of_self_hosted_in_a_comment_is_a_known_text_match_limitation(self):
        # Documents, rather than hides, the text-matching tool's known
        # false-positive shape — see the module docstring's explicit
        # "not a complete YAML security parser" disclaimer.
        text = "# we used to run this on self-hosted, not anymore\nruns-on: ubuntu-24.04\n"
        result = verify_public_source.evaluate_workflow_text("commented.yml", text)
        self.assertEqual(result.state, "verified", "the pattern only matches an actual runs-on: value")


class WorkflowTextBypassTests(unittest.TestCase):
    """Realistic GitHub Actions spellings a prior version of the checker missed."""

    def test_double_quoted_self_hosted_is_detected(self):
        text = 'jobs:\n  build:\n    runs-on: "self-hosted"\n'
        result = verify_public_source.evaluate_workflow_text("q.yml", text)
        self.assertEqual(result.state, "failed")

    def test_single_quoted_self_hosted_is_detected(self):
        text = "jobs:\n  build:\n    runs-on: 'self-hosted'\n"
        result = verify_public_source.evaluate_workflow_text("q.yml", text)
        self.assertEqual(result.state, "failed")

    def test_block_style_self_hosted_first_item_is_detected(self):
        text = "jobs:\n  build:\n    runs-on:\n      - self-hosted\n"
        result = verify_public_source.evaluate_workflow_text("b.yml", text)
        self.assertEqual(result.state, "failed")

    def test_block_style_self_hosted_as_later_item_is_detected(self):
        text = "jobs:\n  build:\n    runs-on:\n      - linux\n      - self-hosted\n"
        result = verify_public_source.evaluate_workflow_text("b2.yml", text)
        self.assertEqual(result.state, "failed")

    def test_bare_pull_request_target_trigger_is_detected(self):
        text = "on: pull_request_target\njobs:\n  build:\n    runs-on: ubuntu-24.04\n"
        result = verify_public_source.evaluate_workflow_text("bare.yml", text)
        self.assertEqual(result.state, "failed")
        self.assertIn("pull_request_target", result.detail)

    def test_pull_request_target_in_flow_sequence_is_detected(self):
        text = "on: [push, pull_request_target]\njobs:\n  build:\n    runs-on: ubuntu-24.04\n"
        result = verify_public_source.evaluate_workflow_text("flow.yml", text)
        self.assertEqual(result.state, "failed")

    def test_similarly_named_label_is_not_a_false_positive(self):
        # "self-hosted-build-2" is a different token; the checker must not
        # match on a mere substring.
        text = "jobs:\n  build:\n    runs-on: self-hosted-build-2\n"
        result = verify_public_source.evaluate_workflow_text("similar.yml", text)
        self.assertEqual(result.state, "verified")

    def test_unrelated_key_starting_with_on_is_not_matched(self):
        text = "jobs:\n  build:\n    online-check: true\n    runs-on: ubuntu-24.04\n"
        result = verify_public_source.evaluate_workflow_text("notatrigger.yml", text)
        self.assertEqual(result.state, "verified")

    def test_quoted_runs_on_key_is_detected(self):
        text = 'jobs:\n  build:\n    "runs-on": self-hosted\n'
        result = verify_public_source.evaluate_workflow_text("qkey.yml", text)
        self.assertEqual(result.state, "failed")

    def test_single_quoted_on_key_is_detected(self):
        text = "'on':\n  pull_request_target:\njobs:\n  build:\n    runs-on: ubuntu-24.04\n"
        result = verify_public_source.evaluate_workflow_text("qkey2.yml", text)
        self.assertEqual(result.state, "failed")

    def test_quoted_pull_request_target_key_is_detected(self):
        text = 'on:\n  "pull_request_target":\njobs:\n  build:\n    runs-on: ubuntu-24.04\n'
        result = verify_public_source.evaluate_workflow_text("qkey3.yml", text)
        self.assertEqual(result.state, "failed")
        self.assertIn("pull_request_target", result.detail)

    def test_self_hosted_inside_a_conditional_expression_is_detected(self):
        text = (
            "jobs:\n  build:\n    runs-on: "
            "${{ github.repository == 'x' && 'self-hosted' || 'ubuntu-latest' }}\n"
        )
        result = verify_public_source.evaluate_workflow_text("expr.yml", text)
        self.assertEqual(result.state, "failed")

    def test_block_list_scan_stops_at_a_dedented_sibling_key(self):
        text = (
            "jobs:\n"
            "  build:\n"
            "    runs-on:\n"
            "      - ubuntu-24.04\n"
            "    needs:\n"
            "      - self-hosted-build\n"
        )
        result = verify_public_source.evaluate_workflow_text("sibling.yml", text)
        self.assertEqual(result.state, "verified")


class QuotePathTests(unittest.TestCase):
    def test_fragment_character_is_percent_encoded(self):
        self.assertEqual(verify_public_source._quote_path("release#1"), "release%231")

    def test_slash_is_preserved_for_branch_names(self):
        self.assertEqual(
            verify_public_source._quote_path("claude/new-session-e8frjc"),
            "claude/new-session-e8frjc",
        )


class RefPinningTests(unittest.TestCase):
    """verify_repo_ref must check the resolved commit, not silently fall back
    to whatever the default branch currently contains."""

    def test_license_and_workflow_checks_use_the_resolved_sha_not_the_raw_ref(self):
        commit_obj = {
            "sha": "b" * 40,
            "commit": {
                "author": {"email": "ok@users.noreply.github.com"},
                "committer": {"email": "ok@users.noreply.github.com"},
            },
        }
        requested_paths = []

        def fake_api_get(path):
            requested_paths.append(path)
            if "/commits/" in path:
                return commit_obj
            if "/license" in path:
                return {"license": {"spdx_id": "MIT"}}
            if "/contents/.github/workflows" in path:
                return []
            raise AssertionError(f"unexpected path: {path}")

        with patch.object(verify_public_source, "_api_get", side_effect=fake_api_get):
            report = verify_public_source.verify_repo_ref("OceanMail/oceanmail-station@main")

        self.assertEqual(report.overall(), "verified")
        non_commit_paths = [p for p in requested_paths if "/commits/" not in p]
        self.assertTrue(non_commit_paths, "expected license/workflow requests to have been made")
        for path in non_commit_paths:
            self.assertIn(f"ref={'b' * 40}", path, f"expected the resolved SHA in {path!r}, not the raw ref 'main'")

    def test_unresolved_commit_marks_license_and_workflows_not_inspected_without_a_default_branch_check(self):
        requested_paths = []

        def fake_api_get(path):
            requested_paths.append(path)
            raise verify_public_source.NotInspected("simulated network failure")

        with patch.object(verify_public_source, "_api_get", side_effect=fake_api_get):
            report = verify_public_source.verify_repo_ref("OceanMail/oceanmail-station@main")

        self.assertEqual(report.overall(), "not_inspected")
        by_name = {c.name: c for c in report.checks}
        self.assertEqual(by_name["license_present"].state, "not_inspected")
        self.assertEqual(by_name["workflows"].state, "not_inspected")
        self.assertEqual(len(requested_paths), 1, "must not fall back to checking the default branch")

    def test_ref_containing_a_hash_is_percent_encoded_in_the_commit_lookup_path(self):
        requested_paths = []

        def fake_api_get(path):
            requested_paths.append(path)
            raise verify_public_source.NotInspected("stop after first call")

        with patch.object(verify_public_source, "_api_get", side_effect=fake_api_get):
            verify_public_source.check_commit_identity("OceanMail", "oceanmail-station", "release#1", None)

        self.assertEqual(len(requested_paths), 1)
        self.assertIn("release%231", requested_paths[0])
        self.assertNotIn("release#1", requested_paths[0])


class MalformedResponseTests(unittest.TestCase):
    """A successful (2xx) but unexpectedly-shaped response must classify as
    not_inspected, not crash the whole utility with an uncaught AssertionError."""

    def test_non_dict_commit_response_is_not_inspected(self):
        with patch.object(verify_public_source, "_api_get", return_value=["not", "a", "dict"]):
            checks, sha = verify_public_source.check_commit_identity(
                "OceanMail", "oceanmail-station", "main", None
            )
        self.assertIsNone(sha)
        self.assertEqual(checks[0].state, "not_inspected")

    def test_non_dict_license_response_is_not_inspected(self):
        with patch.object(verify_public_source, "_api_get", return_value=["not", "a", "dict"]):
            result = verify_public_source.check_license("OceanMail", "oceanmail-station", "b" * 40)
        self.assertEqual(result.state, "not_inspected")

    def test_non_list_workflow_listing_response_is_not_inspected(self):
        with patch.object(verify_public_source, "_api_get", return_value={"not": "a list"}):
            checks = verify_public_source.check_workflows("OceanMail", "oceanmail-station", "b" * 40)
        self.assertEqual(checks[0].state, "not_inspected")

    def test_non_dict_workflow_file_response_is_not_inspected(self):
        def fake_api_get(path):
            if path.endswith("/workflows?ref=" + "b" * 40):
                return [{"name": "ci.yml"}]
            return ["not", "a", "dict"]

        with patch.object(verify_public_source, "_api_get", side_effect=fake_api_get):
            checks = verify_public_source.check_workflows("OceanMail", "oceanmail-station", "b" * 40)
        self.assertEqual(checks[0].state, "not_inspected")


class ApiGetDecodeTests(unittest.TestCase):
    """_api_get must never let a raw transport-level exception escape as
    anything other than NotInspected — see MalformedResponseTests for the
    response-shape half of the same invariant."""

    def test_non_utf8_response_body_is_not_inspected_not_a_crash(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                return False

            def read(self):
                return b"\xff\xfe not valid utf-8"

        with patch.object(verify_public_source.urllib.request, "urlopen", return_value=FakeResponse()):
            with self.assertRaises(verify_public_source.NotInspected):
                verify_public_source._api_get("/repos/OceanMail/oceanmail-station/commits/main")


class ForbiddenNameTests(unittest.TestCase):
    def test_archive_suffix_is_refused(self):
        with self.assertRaises(ValueError):
            verify_public_source.refuse_if_forbidden_name("example-org", "example-archive")

    def test_prototype_suffix_is_refused(self):
        with self.assertRaises(ValueError):
            verify_public_source.refuse_if_forbidden_name("example-org", "example-prototype")

    def test_bempic_prefix_is_refused(self):
        with self.assertRaises(ValueError):
            verify_public_source.refuse_if_forbidden_name("example-org", "bempic-example")

    def test_active_repository_is_permitted(self):
        verify_public_source.refuse_if_forbidden_name("OceanMail", "oceanmail-station")

    def test_this_check_runs_before_any_network_access(self):
        # verify_repo_ref must reject a forbidden name without ever reaching
        # a network call — this is what lets this test run with no network
        # access at all and still exercise the real entry point.
        with self.assertRaises(ValueError):
            verify_public_source.verify_repo_ref("example-org/example-archive@main")


class CheckResultTests(unittest.TestCase):
    def test_invalid_state_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            verify_public_source.CheckResult("x", "passing", "not a real state")


if __name__ == "__main__":
    unittest.main()
