# Evidence record guide

Use a durable evidence record when a research result affects multiple tasks, a dependency, a release, an ADR, or a known external blocker.

## Record fields

```text
record_id:
question/decision:
owner and review date:
authority consulted:
claim:
classification: OBSERVED | INFERRED | UNVERIFIED_EXTERNAL_FACT
source URL/path:
publisher/project:
revision/version/commit:
published/updated date:
retrieved/inspected date:
inspected section/symbol/API field:
local reproduction and environment:
result/artifact/hash:
scope and limitations:
contradictions:
decision impact:
expiry/recheck condition:
next owner:
```

## Quality rules

- One material claim per record when claims have different sources or freshness.
- Quote only the minimum source text needed; link rather than copying long external content.
- Separate a source's guarantee from behavior observed in one environment.
- Keep failed searches and unavailable tools as limitations, not negative product claims.
- Update or supersede stale records instead of editing history into a false present.
- Do not store secrets, private URLs, cookies, or personal data.

## Review gate

The decision owner checks authority, source revision, freshness, reproduction, contradictory evidence, license/dependency impact, and whether the result is strong enough for the intended action. If not, keep the decision blocked or mark the external fact unverified.
