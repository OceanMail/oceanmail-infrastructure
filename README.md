# OceanMail Infrastructure

Deployment, CI/CD, gateway-hosting, and operations documentation for OceanMail 0.2. This fresh source repository contains generic deployment policy; private operational inventory remains outside it.

## Authority and scope

Organization-level OceanMail definition, architecture, cross-repository decisions, terminology, repository inventory, and current project state are authoritative in [`OceanMail/oceanmail-project`](https://github.com/OceanMail/oceanmail-project).

This repository owns deployment manifests, secret-free configuration templates, release acceptance, backup/restore, monitoring, gateway/VPS operations, DNS/TLS/network infrastructure, public SMTP/MX deployment, and cross-service deployment contracts.

It does **not** own Desktop code, Station/HERMES integration code, hosted Server application logic, or organization-wide product semantics.

Start with root [`AGENTS.md`](AGENTS.md), [`docs/README.md`](docs/README.md), central [`workstreams/infrastructure.md`](https://github.com/OceanMail/oceanmail-project/blob/main/workstreams/infrastructure.md), and project ADR-006.

## 0.2 topology direction

Native OMail and public Internet-mail bridging are separate paths:

```text
Native OMail path (no central service required)

Boat/Station A
      |
HERMES/Mercury or another accepted Station transport
      |
relay/store-carry-forward Stations as available
      |
Boat/Station B


Public Internet-mail boundary path

OceanMail Station / authorized Gateway
      |
authenticated OceanMail service boundary
      |
OceanMail hosted service
      |
centralized OceanMail public SMTP/MX boundary
      |
conventional Internet mail/services
```

OceanMail-operated Server/infrastructure is the sole public Internet SMTP/MX boundary. Internet-connected Stations/gateways do not become independent public MTAs or deliver directly to arbitrary Internet SMTP systems. Native OMail remains decentralized and may continue without central Server/Internet availability.

Infrastructure must treat HERMES/Mercury components as upstream dependencies where practical and must not silently vendor or fork them.

The architectural mail boundary is settled. Exact production provider/hosting choice, host count/geography, IP allocation and reverse DNS, reputation monitoring, failover/HA, and scale-out design remain explicit deployment decisions; do not infer them from historical prototypes or create premature production-scale clustering.

Infrastructure must not distribute public-SMTP relay credentials or public-MTA responsibilities to gateway Stations as a deployment shortcut. A central outage may delay Internet-boundary traffic, but the deployment must not make native OMail dependent on central availability.

## Implementation baseline

Deployment, backup and security controls require review against the current 0.2 topology and reproducible validation.

## Immediate milestone

Provide the infrastructure needed for reproducible private 0.2 end-to-end service proofs, including the authenticated Station/Server gateway path and centralized Internet-mail boundary, then grow topology only as measured requirements justify it.

Never commit live credentials, private keys, customer data, or production secrets.

## Public source status

This is an experimental bootstrap, not a production-ready implementation. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md). The approved source/documentation licenses are installed. See [LICENSING.md](LICENSING.md) and [PUBLICATION.md](PUBLICATION.md). No additional inbound agreement is adopted. The public main branch is protected and hosted checks validate proposed changes; external-fork acceptance remains unverified.

## Licenses

OceanMail-owned code and validation tooling: [AGPL-3.0-only](LICENSE). Documentation: [CC-BY-SA-4.0](LICENSE-DOCS). See [scope](LICENSING.md) and the [fresh-history boundary](PUBLICATION.md).
