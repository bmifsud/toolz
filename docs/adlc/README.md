# Toolz Agentic Development Lifecycle (ADLC)

A lightweight repository template adapted from the supplied AI Software Development Life Cycle
and granular execution checklist. This is workflow scaffolding, not certification or evidence
that toolz is release-ready. The source documents are reference material, not legal authority.

## Start a change

Copy [intent](templates/intent.md) and [evidence](templates/evidence.md) into
`docs/adlc/changes/<change-id>/`. Fill them before implementation and link them in the PR.
Use [status](status.md) as a small release ledger; keep detailed tasks in GitHub issues.
Do not copy secrets, private prompts, tokens or raw device output into any record.

## Five phases

| Phase | Required output | Exit condition |
| --- | --- | --- |
| 1. Intent | Problem, scope, owner, acceptance criteria, risks | Expected behavior and exclusions are explicit |
| 2. Plan | Affected paths, dependencies, permissions, validation and rollback | Source inspected; material assumptions resolved |
| 3. Implement | Small branch diff; updated docs and component inventory when applicable | Scoped implementation and focused checks completed |
| 4. Verify | Revision-bound commands, results, artifacts, independent review | Required checks passed; failures and unavailable checks remain visible |
| 5. Release and learn | Approved revision, deployment/rollback evidence, follow-up | Merge/release gates passed; merged revision verified before closure |

Apply AI-product evaluations only to delivered AI behavior. Version prompts, model/provider
references, tool permissions and evaluation cases when those change; record unknown versions
as unknown. Use [component inventory](templates/ai-components.md) for those changes.
This inventory is not a standards-compliant generated SBOM/AIBOM.

## Verification and release gates

Use [existing verification guidance](../verification.md) and
[Tier-1 acceptance](../../backup/TIER1_DEPLOYMENT_ACCEPTANCE.md).
Check commands and paths against the actual revision first.
Unit tests, mocked uploads and green CI do not prove device or restoration behavior.

The standing release hold remains until all evidence below is verified:

- Bridge: authenticated connect, reconnect, cancel, restart and denied/security paths,
  first on an emulator and then on the tablet.
- Tier-1: scheduled execution, encrypted upload with readback/integrity, and missed-run catch-up.
- Tier-2: safe OmniRoute shutdown/WAL handling, encrypted snapshot/upload, isolated restore and integrity.
- Required CI and human approvals apply to the final reviewed revision; blocking findings resolved.

This template does not change schedules, branch protection, runtime permissions or deployments.
GitHub checkboxes and agent instructions are records, not enforced security controls.
Enforcement gaps stay blocked until a separately reviewed implementation provides them.

## Current baseline

Inspected main on 2026-11-02: backup scripts/tests and documentation exist;
no AGENTS.md, GitHub templates/workflows or Android project were returned by the inspected tree.
Older documentation references absent workflows and Android paths. Reconcile those references
before using them as executable instructions. No live backup/device gate was executed for setup.

## Sources

Adapted from the user's supplied “AI Software Development Life Cycle.pdf” and
“A full granular and itemized list of all the steps.pdf.pdf”, read on 2026-11-02.
Use their lifecycle/checklist concepts proportionately; no legal or standards claims are adopted.
