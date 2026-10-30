# ADR-006: Define the failure protocol and search-status taxonomy

## Status

Accepted — implemented in the bounded runner and staging paths. Native platform, organizer scoring, and release qualification remain separate evidence questions.

## Date

2026-10-06

## Context

The ratified contract and Accepted ADR-003 establish the hard boundary: a Stage 1 result is a design document, a hard-invalid or infeasible task must fail closed, and the runner must not emit a misleading design or PNG. This ADR supplies the internal status vocabulary, the distinction between an exhausted search and a search interrupted by a cutoff, and the transaction boundary for publishing the two task artifacts.

The current public success shape must remain unchanged. In particular, a failure status must not be smuggled into a design document and a second JSON ``unsatisfiable`` response must not be invented before the organizer specifies how failures are scored. JSON Schema defines validation rather than process exit status ([JSON Schema validation](https://json-schema.org/draft/2020-12/json-schema-validation)), while the POSIX utility convention uses zero for success and nonzero for failure ([POSIX utility conventions](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap01.html)). Those sources are general conventions, not organizer-specific scoring rules.

The implementation now stages artifacts before publication, reports typed failures, cleans stale outputs, and preserves the all-or-nothing JSON/PNG boundary. This ADR remains the source for those rules.

### Authority classification

- **Ratified current contract:** `Docs/PROJECT_CONTRACT.md` §§3 and 8, ADR-001, ADR-003, and ADR-004. These remain authoritative. They require a design-only success response, typed fail-closed infeasibility, no Stage 1 artifact for a failed task, and an offline `linux/amd64` runtime.
- **Accepted internal contract decision:** the status names, deterministic cutoff rule, pair-publication protocol, and batch aggregation below are ratified defaults used by the current runner. Current evidence is recorded in the implementation tickets and `Docs/STATUS.md`.
- **Externally unverified organizer fact:** whether hidden tasks are guaranteed feasible and how the scorer treats missing output or a nonzero task failure. No local decision can answer that question.

## Decision

### 1. Use stable internal statuses, not a new success wire format

Use the following internal task statuses and reason-code families:

| Status | Meaning | Required artifact behavior |
| --- | --- | --- |
| `SUCCESS` | A candidate passed all hard checks and both required artifacts were committed. | Publish the design JSON and PNG as one logical pair. |
| `MALFORMED_INPUT` | The task envelope, source document, target canvas, schema, or required semantic input checks are invalid before a candidate can be trusted. | Publish neither artifact for the task; record a stable diagnostic reason. |
| `INFEASIBLE_LAYOUT` | A complete, deterministic candidate search was exhausted and no hard-valid candidate exists. | Raise the typed fail-closed error required by ADR-003; publish neither artifact. |
| `INCOMPLETE_SEARCH` | A deterministic work limit, timeout, or other search cutoff occurred before the search could establish feasibility or infeasibility. | Publish neither artifact; report a typed failure reason, not a claim of proven infeasibility. |
| `RUNTIME_IO_FAILURE` | Renderer, dependency, asset, filesystem, serialization, or other runtime failure prevented a trustworthy result. | Publish neither artifact; record the failure without treating it as a layout result. |

`INFEASIBLE_LAYOUT` and `INCOMPLETE_SEARCH` are accepted reason-coded outcomes of the same typed, fail-closed internal failure surface where necessary; they are not alternate public response documents. The accepted `InfeasibleLayoutError` (or language-equivalent typed error) remains the contract boundary until a future accepted ADR says otherwise.

### 2. Keep the public success and failure boundary boring

- On success, the response remains exactly the design document prescribed by the contract: target canvas plus the source element set in source order. No status, score, candidate list, or diagnostic field is added to the response schema.
- On failure, do not emit an ``unsatisfiable`` JSON envelope or a best-effort design. The runner records a typed internal status and reason and follows the organizer's eventual submission protocol.
- A future organizer-required failure envelope would require an explicit accepted contract/ADR change. This ADR does not create one.

### 3. Do not call an interrupted search proven infeasible

A hard-valid candidate found before an optimization cutoff MUST be returned, subject to deterministic ranking among the candidates actually found. If no candidate has been found before the cutoff, the result is `INCOMPLETE_SEARCH`, not `INFEASIBLE_LAYOUT`. Only an exhausted search space with no hard-valid candidate may claim `INFEASIBLE_LAYOUT`.

This distinction preserves ADR-003's fail-closed rule while avoiding a false proof from a timeout. It also gives the search ADR a stable hand-off for cutoff behavior.

### 3b. Maximize feasibility via contract-permitted geometric levers

Candidate generation SHOULD prevent avoidable failures on extreme canvas ratios by considering all contract-permitted levers before declaring infeasibility:

1. Reduce text font sizes while preserving unchanged copy, fixed typography properties, renderer bounds, and qualitative readability. Try larger positive sizes first, then smaller positive sizes when needed; there is no universal numeric minimum. ADR-011 supersedes this subsection's former numeric floor.
2. Isotropically downscale foreground artwork while preserving exact image ratios.
3. Consider horizontal-ribbon or multi-column topology shifts that spread content along the dominant canvas axis.
4. Compress margins and element spacing where the source relationships and hard constraints allow.

The official score consequence of task failure is not established by this ADR. `INFEASIBLE_LAYOUT` is reserved for an exhausted finite search with no hard-valid candidate; a cutoff without a candidate remains `INCOMPLETE_SEARCH`. Neither status permits publishing a misleading design or PNG.

### 4. Commit the JSON and PNG as one task result

For each task:

1. Create task-private staging paths that cannot be mistaken for final outputs.
2. Serialize the candidate JSON and render the PNG into staging.
3. Validate the serialized JSON and the rendered result, including the checks required by the contract and the renderer conformance decisions.
4. Publish the pair through one task-level commit step only after both artifacts exist and validate.
5. If any step fails, remove or quarantine the task's staged and final paths so a stale result cannot be mistaken for this run's result.

The pair-commit guarantee is logical: consumers must observe either both final artifacts for a successful task or neither. The concrete filesystem primitive is an implementation detail and must not change the public design schema.

### 5. Continue independent tasks and aggregate failure conservatively

Independent tasks MAY continue after one task fails so that one malformed, infeasible, incomplete, or runtime-failed task does not hide diagnostics for the rest of the batch. The batch process exits zero only when every task commits both artifacts. If any task fails or does not commit its pair, the aggregate exit status is nonzero, following the POSIX convention above.

This aggregation is an internal runner policy. The organizer's scoring treatment of a missing task output remains an external blocker.

## Alternatives Considered

### Always emit the best candidate found

Rejected. ADR-003 explicitly requires fail-closed behavior. Returning a candidate that has not passed the hard contract makes an invalid submission indistinguishable from a valid one.

### Add a second JSON response for ``unsatisfiable``

Deferred. ADR-003 records this as an open interface decision, and the supplied scoring interface does not define such an envelope. Adding it now would silently change the ratified wire contract.

### Treat every timeout as proven infeasibility

Rejected. A timeout establishes only that the selected search did not finish. It cannot establish that no hard-valid candidate exists.

### Write JSON and PNG independently as they become available

Rejected. A renderer or I/O failure after JSON publication would leave a partial or stale task result. The pair must be staged and committed together.

### Stop the entire batch at the first failed task

Rejected as the default. Continuing independent tasks produces complete diagnostics and does not alter the fail-closed result for the failed task. A caller may still choose to stop externally, but the runner's default aggregate status remains nonzero if any task fails.

### Return zero when some tasks fail because the process itself ran

Rejected. A successful process is not the same as a successful batch. Zero is reserved for the all-task-committed case.

## Consequences

- The orchestrator has an explicit typed status path and task-level pair publication.
- Search code exposes whether its candidate set was exhausted or cut off; it cannot infer that from the absence of a candidate alone.
- Artifact publication is transactional at the task level and includes stale-output handling.
- Batch logs distinguish malformed input, proven infeasibility, incomplete search, and runtime/I/O failure without changing the design schema.
- The organizer's failure scoring remains unresolved. A local run can be deterministic and fail closed without claiming that the external scorer will accept missing output.
- Implementation changes remain limited to this ADR's accepted behavior and recorded project scope.

## Affected files/schema fields

The affected implementation includes the task runner/orchestrator (`chameleon/engine/main.py`), task output staging/publishing, and typed internal error definitions. No public schema field is added or changed. The existing design response, element identity rules, and ADR-003 failure contract remain the boundary.

The runner, staging paths, typed errors, and task-level publication behavior implement this ADR. The public schema remains unchanged.

## Required validation/evidence

Before implementation can claim conformance, the evidence must include at least:

- malformed envelope, schema-invalid input, and semantically invalid input each produce `MALFORMED_INPUT`, no task artifacts, and a nonzero aggregate result;
- a search that exhausts a finite candidate set with no hard-valid result produces `INFEASIBLE_LAYOUT` and the typed fail-closed error;
- a deterministic cutoff before proof produces `INCOMPLETE_SEARCH`, never `INFEASIBLE_LAYOUT`;
- a valid candidate found before the cutoff is returned only after serialized hard validation;
- injected renderer, asset, serialization, and filesystem failures produce `RUNTIME_IO_FAILURE` and no stale or partial pair;
- interruption or failure between staging and commit leaves no observable one-file result;
- repeated runs produce the same status, reason code, artifact bytes, and aggregate exit status; and
- a mixed batch continues independent tasks, commits only successful pairs, and exits nonzero if any task does not commit both artifacts.

Focused and full test evidence is recorded in Ticket 03 and `Docs/STATUS.md`. This ADR defines the required evidence and does not replace those records.

### Organizer clarification required

- Are hidden tasks guaranteed feasible? How does the scorer handle no-output/nonzero task failure?
