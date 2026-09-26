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


class ForbiddenNameTests(unittest.TestCase):
    def test_archive_suffix_is_refused(self):
        with self.assertRaises(ValueError):
            verify_public_source.refuse_if_forbidden_name("OceanMail", "oceanmail-station-archive")

    def test_prototype_suffix_is_refused(self):
        with self.assertRaises(ValueError):
            verify_public_source.refuse_if_forbidden_name("OceanMail", "oceanmail-0.1-prototype")

    def test_bempic_prefix_is_refused(self):
        with self.assertRaises(ValueError):
            verify_public_source.refuse_if_forbidden_name("OceanMail", "bempic-reference")

    def test_active_repository_is_permitted(self):
        verify_public_source.refuse_if_forbidden_name("OceanMail", "oceanmail-station")

    def test_this_check_runs_before_any_network_access(self):
        # verify_repo_ref must reject a forbidden name without ever reaching
        # a network call — this is what lets this test run with no network
        # access at all and still exercise the real entry point.
        with self.assertRaises(ValueError):
            verify_public_source.verify_repo_ref("OceanMail/oceanmail-desktop-archive@main")


class CheckResultTests(unittest.TestCase):
    def test_invalid_state_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            verify_public_source.CheckResult("x", "passing", "not a real state")


if __name__ == "__main__":
    unittest.main()
