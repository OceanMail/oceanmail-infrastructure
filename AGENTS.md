# OceanMail Infrastructure — Agent Instructions

These repository-local instructions apply to implementation agents working in `OceanMail/oceanmail-infrastructure`.

## Organization authority

Organization-level OceanMail definition, architecture, terminology, repository inventory, cross-repository decisions, current project state, and AI/contributor workflow are authoritative in [`OceanMail/oceanmail-project`](https://github.com/OceanMail/oceanmail-project).

Before substantial Infrastructure work, read there in order:

1. `PROJECT.md`
2. `CURRENT_STATE.md`
3. `DECISIONS.md`
4. `REPOSITORIES.md`
5. `workstreams/infrastructure.md`
6. relevant project ADR/interface documents

Then read this repository's README/docs, current deployment artifacts, open PRs/issues, and validation/tests.

## Infrastructure boundary

This repository owns deployment and operations implementation, including:

- environments/topology;
- CI/CD and release acceptance;
- DNS/TLS/network infrastructure;
- monitoring/alerting;
- backup/restore/disaster recovery;
- secret-management boundaries and secret-free templates;
- gateway/VPS/service deployment runbooks;
- infrastructure supply-chain controls.

It does not own Desktop code, Station/HERMES integration code, hosted Server application logic, or organization-wide product semantics.

Operational constraints must be surfaced and reconciled; do not silently redefine application/product behavior to simplify deployment.

## Historical material

The earlier 0.1 design is historical evidence, not current deployment authority. Reuse proven runbooks/security controls selectively after review against current 0.2 architecture.

## Security and scale discipline

- Never commit live credentials, private keys, passwords, production tokens, customer data, or sensitive production material.
- Keep secret-bearing values outside versioned configuration.
- Preserve recoverability, backup verification, and artifact/version provenance.
- Avoid premature clustering or production-scale topology before measured requirements justify it.
- Keep hosted-service responsibilities separable from RF Station responsibilities.

## Documentation/workflow

Component deployment/operations truth stays here. When infrastructure work changes organization-level topology assumptions, cross-component deployment contracts, security boundaries, or settled architecture, update `OceanMail/oceanmail-project` as well.

Separate validation into STATIC / UNIT, INTEGRATION, and LIVE / PRODUCT/OPERATIONS as appropriate. Follow architecture escalation and merge authority in the central project `AGENTS.md`.
