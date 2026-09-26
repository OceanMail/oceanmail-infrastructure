# OceanMail Infrastructure Documentation

This repository owns **deployment and operations documentation** for OceanMail 0.2 infrastructure.

Organization-level product semantics, cross-repository architecture, terminology, decisions, and current project state are authoritative in [`OceanMail/oceanmail-project`](https://github.com/OceanMail/oceanmail-project).

## Current operations documents

- [`CI-RUNNERS.md`](CI-RUNNERS.md) — generic public CI execution policy and private-runner exclusion requirements; no private host inventory is published.

## This repository may define

- environments/topology used to deploy OceanMail services;
- CI/CD and release acceptance;
- infrastructure security controls;
- secret-management boundaries and secret-free templates;
- backup/restore/disaster-recovery procedures;
- monitoring/alerting;
- VPS/gateway/service deployment runbooks;
- DNS/TLS/network infrastructure;
- infrastructure supply-chain controls;
- operational evidence/work reports; and
- cross-service deployment contracts that do not redefine application semantics.

## This repository must not independently redefine

- OMail/OChat product behavior;
- Client/Station/Server responsibilities;
- Station/user role semantics;
- mailbox/account product semantics;
- gateway/relay willingness policy;
- constrained-link accounting/product rules; or
- organization-wide roadmap/architecture decisions.

Those belong in `OceanMail/oceanmail-project` and should be referenced here.

## Documentation precedence

For Infrastructure work:

1. accepted project decisions/architecture/interfaces in `OceanMail/oceanmail-project`;
2. current infrastructure architecture/security/operations documentation here;
3. deployment plans;
4. research/work reports/history.

Infrastructure may impose operational constraints, but conflicts with project architecture must be surfaced/reconciled rather than silently changing product behavior.

## Expected future structure

Add files only when real deployment work requires them, for example:

```text
docs/
    README.md
    ARCHITECTURE.md
    ENVIRONMENTS.md
    SECURITY.md
    BACKUP-RESTORE.md
    OPERATIONS.md
    decisions/
    work-reports/
```

Avoid production-scale topology documentation before measured requirements justify the topology itself.

## Legacy material

`OceanMail/oceanmail-infrastructure-0.1-prototype` remains historical evidence. Reintroduce proven runbooks/security controls selectively after review rather than inheriting 0.1 deployment assumptions wholesale.
