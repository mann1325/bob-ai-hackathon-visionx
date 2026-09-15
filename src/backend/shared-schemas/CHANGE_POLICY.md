# SHARED SCHEMA CHANGE POLICY

## LOCK RULE

No member may independently:
- rename a field
- delete a field
- change a type
- change required/optional status
- change semantic meaning
- change API response shape

## Change Process

```text
Need identified
→ Discuss with all affected members
→ Agree on change
→ Version the contract
→ Update implementations
→ Integration test
→ Merge
```

## Compatibility Rule

Prefer adding optional fields instead of breaking existing fields.

These files are the team's single source of truth:
- `data-schema.json`
- `signal-schema.json`
- `document-analysis-schema.json`
- `api-contract.yaml`
