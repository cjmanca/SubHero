# Public API, MCP tool surface, authentication and ACLs

**Owner:** integration boundary · **Related:** [workflows](workflows-and-queue.md), [review UI](web-ui-and-review.md), [models](models-and-resources.md).

## Interfaces

- Web UI, documented HTTP API and MCP server must operate through a common application/job service and authorization model. API/MCP actions may submit jobs, inspect statuses/results, fetch reports/correction proposals, and perform **permitted** review/approval/application/admin operations.
- **Separate API keys for raw HTTP and MCP**; keys are revocable and have configurable per-key ACLs. Permit distinct roles/scopes for read/query, enqueue audit, enqueue metadata, enqueue enhancement, view audio/transcript, review proposals, approve, modify/commit media, manage models/glossaries, trigger Plex, manage users/keys, administer settings.
- Server should record actor identity, client type, requested media root, resulting job ID, review decisions, file mutations and external/cloud model disclosures.
- Explicit allowlisted library roots and per-path authorization; never permit arbitrary filesystem modification or unchecked output destinations simply because an MCP agent supplies a path.
- Use secure transport for exposed services; secrets must not be returned in job logs/reports, world-readable configs or model prompts. Optional web UI auth with appropriate local deployment defaults.

## Proposed conceptual actions (not fixed names/routes)

| Group | Capabilities |
| --- | --- |
| Media | list/probe tracks, locate associated sidecars, read scores, request targeted rescans |
| Jobs | submit operations, poll/list/priority, cancel, retry, stage progress, inspect errors |
| Corrections | see old/new/evidence, approve/reject/group/select-all, commit/revert and explain actions |
| Glossary | query candidate terms, confirm/edit scope, request affected-file proposals |
| Configuration | read allowed capabilities/policies, manage model bindings and thresholds when authorized |
| Integrations | invoke Plex re-analysis or supported webhook after successful commit |

API/MCP must support pagination, filtering, stable identifiers, explicit idempotency for submission and approval, safe error codes, and versioning so external automation does not depend on UI shape.

## Special safety cases

- Never let an agent approve edits merely by calling a read-only queue method; approval and source modification are separately permissioned.
- Cloud providers require explicit allow policy for sending speech/text/video off-host; distinguish LAN remote endpoints from third-party remote services and record disclosure in job evidence.
- No silent escalation of permission from audit to publication or from a general scan to direct original-subtitle modification.
