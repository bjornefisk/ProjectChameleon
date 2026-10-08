# Parallel dispatch checklist

- [ ] Parent run/task ID and integration owner exist.
- [ ] Each slice has disjoint mutable paths/resources.
- [ ] Shared interfaces and dependency edges are explicit.
- [ ] Each child receives authority, acceptance, non-goals, risk, capabilities, stop conditions, and handoff schema.
- [ ] No child receives secrets or unnecessary context.
- [ ] Only unblocked work was dispatched.
- [ ] Shared build/test/format checks are not contaminated by concurrent edits.
- [ ] Child reports are checked against actual files/diffs/evidence.
- [ ] Conflicts are resolved by authority/ownership, not last writer.
- [ ] One integration wave ran after edits settled.
- [ ] Abandoned/failed/unrun slices and next owner are recorded.
