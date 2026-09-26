# OceanMail CI execution policy

Status: active public CI policy. Runner-group isolation requires administrative
verification; source-level workflow checks do not prove that setting.

Public and fork pull-request validation uses GitHub-hosted runners with read-only
tokens and no repository secrets. Public repositories must have no access to
trusted self-hosted runners, including repository-scoped registrations and all
organization runner groups. Workflow conditions alone are not that boundary.

Hardware or private integration testing requires a deliberate maintainer operation
against reviewed exact commits. It is not dispatched by untrusted public PR code.
Privileged container access and a VM snapshot are not isolation from hostile jobs.

Private host identities, accounts, paths, sizing, software inventories, service
configuration, network topology and recovery procedures are intentionally excluded
from public source. Keep those records in access-controlled operations storage.

Administrators must maintain and verify runner exclusion, default token
permissions, outside-contributor workflow approvals and secret boundaries. Record
sanitized evidence in the public project record. Review published logs, artifacts
and Git metadata separately from the current tree; a documentation check is not
a full-history privacy audit.
