# Ownership and concurrency policy

## Single owner

Every mutable file/resource has one current owner: person, role, run ID, and task ID. Read-only review does not transfer ownership. A handoff transfers it explicitly with a current diff/state record.

## Scope packet

Before mutation, the owner records exact paths/resources, authority, acceptance, non-goals, expected callers, and verification. A role MUST NOT opportunistically repair a sibling's file; create a new slice or coordinate a boundary instead.

## Parallel work

Parallel work is allowed only when:

- slices have disjoint mutable paths;
- shared interfaces are written down;
- dependencies and integration owner are explicit;
- each agent receives a bounded context/capability packet;
- shared checks run after the edit wave settles.

If paths overlap, serialize or renegotiate ownership. Do not rely on file locks or chat timing as a correctness mechanism.

## Unexpected changes

Treat user or sibling changes as intentional. Stop, re-read, and coordinate. Never reset, checkout, stash, or revert unrelated work without explicit authorization.

## Integration

The integration owner re-reads shared files, reconciles interfaces, preserves all accepted changes, and runs the shared verification once. A subagent's “done” message is not integration evidence.
