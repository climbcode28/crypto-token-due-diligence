# Reviewed operational memories

Procedural guidance only. Current user instructions, trusted provider policy and fresh
exact-target evidence remain authoritative. Never store token facts, credentials,
private endpoints or paid-use authorization. Research reads relevant active entries
through `operations.py read` and records candidates under its fresh run directory;
it does not edit this file. See [the lifecycle](references/improvement-loop.md).

The five initial audit lessons are retired because maintained helpers/references now
implement them. There are currently no active entries. The original review draft and
maintenance review are identified by the digests below; retired entries are not loaded
as research guidance. Future entries require demonstrated recovery, review provenance,
exact applicability, an expiry and bounded text.

```json
{
  "schema_version": 1,
  "entries": [
    {
      "id": "OPS-001",
      "status": "retired",
      "component": "source_lookup",
      "operation": "contract_lookup",
      "versions": [
        "v3.0.0"
      ],
      "action": "Use the maintained selective source lookup adapter",
      "limitations": "Source records still require fresh runtime correspondence",
      "verification": [
        "source_lookup.py and test_research_helpers.py",
        "Implemented in maintained helpers or references; retired after review"
      ],
      "reviewed_on": "2026-09-08",
      "expires_on": "2026-12-08",
      "superseded_by": null,
      "review_provenance": {
        "review_sha256": "23b4c4abb19843e6a87dfed3e56a87ea92da27cd141836f431476800be53dba1",
        "observation_sha256": "d7e3fbc40b36b2374aaf0350a398cb6d07d7f4f5427e8d5019f73160f2c7133e",
        "observation_id": "OPS-001"
      }
    },
    {
      "id": "OPS-002",
      "status": "retired",
      "component": "decoder",
      "operation": "clone",
      "versions": [
        "v3.0.0"
      ],
      "action": "Use the exact standard clone extractor",
      "limitations": "Variant runtimes remain unresolved; inspect instance state separately",
      "verification": [
        "evm_decode.py and test_research_helpers.py",
        "Implemented in maintained helpers or references; retired after review"
      ],
      "reviewed_on": "2026-09-08",
      "expires_on": "2026-12-08",
      "superseded_by": null,
      "review_provenance": {
        "review_sha256": "23b4c4abb19843e6a87dfed3e56a87ea92da27cd141836f431476800be53dba1",
        "observation_sha256": "d7e3fbc40b36b2374aaf0350a398cb6d07d7f4f5427e8d5019f73160f2c7133e",
        "observation_id": "OPS-002"
      }
    },
    {
      "id": "OPS-003",
      "status": "retired",
      "component": "assembly",
      "operation": "import",
      "versions": [
        "v3.0.0"
      ],
      "action": "Import helpers without regenerating artifacts",
      "limitations": "Preserve captured plans and raw artifacts; use new outputs",
      "verification": [
        "bundle_assemble.py and test_research_helpers.py",
        "Implemented in maintained helpers or references; retired after review"
      ],
      "reviewed_on": "2026-09-08",
      "expires_on": "2026-12-08",
      "superseded_by": null,
      "review_provenance": {
        "review_sha256": "23b4c4abb19843e6a87dfed3e56a87ea92da27cd141836f431476800be53dba1",
        "observation_sha256": "d7e3fbc40b36b2374aaf0350a398cb6d07d7f4f5427e8d5019f73160f2c7133e",
        "observation_id": "OPS-003"
      }
    },
    {
      "id": "OPS-004",
      "status": "retired",
      "component": "validator",
      "operation": "finding_support",
      "versions": [
        "v3.0.0"
      ],
      "action": "Use explicit finding subjects and registered dependency inputs",
      "limitations": "Mechanical checks cannot establish the truth of arbitrary prose",
      "verification": [
        "report_profile.py and test_strict_profile.py",
        "Implemented in maintained helpers or references; retired after review"
      ],
      "reviewed_on": "2026-09-08",
      "expires_on": "2026-12-08",
      "superseded_by": null,
      "review_provenance": {
        "review_sha256": "23b4c4abb19843e6a87dfed3e56a87ea92da27cd141836f431476800be53dba1",
        "observation_sha256": "d7e3fbc40b36b2374aaf0350a398cb6d07d7f4f5427e8d5019f73160f2c7133e",
        "observation_id": "OPS-004"
      }
    },
    {
      "id": "OPS-005",
      "status": "retired",
      "component": "browser",
      "operation": "capture",
      "versions": [
        "v3.0.0"
      ],
      "action": "Record operation and access mode separately and preserve honest capture provenance",
      "limitations": "A blocked export or API does not establish global source absence",
      "verification": [
        "source-routing-and-execution.md and test_operations.py",
        "Implemented in maintained helpers or references; retired after review"
      ],
      "reviewed_on": "2026-09-08",
      "expires_on": "2026-12-08",
      "superseded_by": null,
      "review_provenance": {
        "review_sha256": "23b4c4abb19843e6a87dfed3e56a87ea92da27cd141836f431476800be53dba1",
        "observation_sha256": "d7e3fbc40b36b2374aaf0350a398cb6d07d7f4f5427e8d5019f73160f2c7133e",
        "observation_id": "OPS-005"
      }
    }
  ]
}
```
