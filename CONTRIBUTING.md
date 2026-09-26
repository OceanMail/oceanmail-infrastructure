# Contributing

Licenses are installed; see [LICENSING.md](LICENSING.md). No DCO or additional
inbound agreement is adopted. Follow the
[organization contribution policy](https://github.com/OceanMail/oceanmail-project/blob/main/CONTRIBUTING.md)
and this repository's AGENTS.md. Fork and submit PRs against main;
external contributors normally have no upstream write access. Maintainers merge.

This bootstrap repository currently contains documentation and validation tooling,
not a production service. Run `python3 scripts/check-docs.py` from a Git checkout
for JSON syntax and inline local Markdown file targets. No application build is
available yet. Do not include credentials, private mail or operational data.
