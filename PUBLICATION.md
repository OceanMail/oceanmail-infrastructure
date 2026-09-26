# Fresh source publication

Owner direction, 2026-09-26: Server and Infrastructure join Project, Station and Desktop as public source repositories. This supersedes the earlier three-repository publication scope.

This repository starts from a sanitized current tree with new Git history. The original repository remains private with an `-archive` suffix. Historical branches, identities, PRs, Actions artifacts and logs are not imported. Only generic architecture and operational security policy belong in this source repository; private deployment inventory remains outside it.

LICENSE and LICENSE-DOCS contain the approved AGPL-3.0-only and CC-BY-SA-4.0 texts. LICENSING.md defines scope and preserves third-party terms. Additional inbound contribution terms remain unadopted.

This is a documentation/bootstrap source release, not a running production service. Required hosted CI check: `docs`. Use pull requests, zero required approving reviews, required checks, and protected main. Configure private vulnerability reporting and exclude public repositories from trusted runners.
