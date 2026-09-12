# Solana token diligence

SYNTHETIC — PARTIAL

## Target

```json
{
  "family": "solana",
  "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
  "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
}
```

## Assessment

```json
{
  "change_evidence": "Resolve the listed coverage gaps.",
  "question": "Broad token diligence",
  "strongest_contrary_evidence": "Not yet investigated.",
  "unresolved_questions": [
    "All broad dimensions require review."
  ],
  "verdict": "Insufficient evidence; initialized packet is not completed diligence."
}
```

## Dimensions

```json
[
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "token_controls",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "canonical_lp_principal_custody",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "side_pool_removal_risk",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "sellability_exit_depth",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "current_concentration",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "historical_launch_integrity",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "admin_treasury_reward_custody",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "reward_accounting_liveness",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "utility_redemption_rights",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "external_dependencies",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  },
  {
    "basis": "Not yet investigated.",
    "confidence": "low",
    "coverage": "unknown",
    "dimension": "development_disclosure",
    "evidence_ids": [],
    "likelihood": "unknown",
    "severity": "unknown",
    "status": "unknown",
    "time_basis": "unresolved"
  }
]
```

## Findings

```json
[]
```

## Evidence and limitations

```json
{
  "collection_sha256": null,
  "engine_version": "1.0.0",
  "evidence": [
    {
      "artifact": "genesis.json",
      "id": "genesis",
      "kind": "rpc",
      "sha256": "5f300968a7f43da73fb4ce0cf4dcab44ff6f3c2bff34173455b122f222929963",
      "source": "offline synthetic fixture",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "finalized slot 100; synthetic"
    },
    {
      "artifact": "mint.json",
      "id": "mint",
      "kind": "rpc",
      "sha256": "6f36e44a5e7a115b34366afcd80add58b1ba857208f53a007c5369529d0f9b16",
      "source": "offline synthetic fixture",
      "state": {
        "block_evidence_id": "block",
        "block_recheck_evidence_id": "block_recheck",
        "commitment": "finalized",
        "slot": 100
      },
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "finalized slot 100; synthetic"
    },
    {
      "artifact": "block.json",
      "id": "block",
      "kind": "rpc",
      "sha256": "1a484bfd90a694b0c7da8605f14f2abb6edf43e8dd488bf96cf8bc897bd8fba6",
      "source": "offline synthetic fixture",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "finalized slot 100; synthetic"
    },
    {
      "artifact": "block_recheck.json",
      "id": "block_recheck",
      "kind": "rpc",
      "sha256": "c543800d7a951d3dcf74756d541bed8c852f90f69a5d75383ee033f16570a51d",
      "source": "offline synthetic fixture",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "finalized slot 100; synthetic"
    }
  ],
  "identity_evidence": [
    "genesis",
    "mint"
  ],
  "limitations": [
    "Initial packet only; all broad dimensions need research and reconciliation."
  ],
  "safety": {
    "no_broadcast": true,
    "no_real_keys": true,
    "no_real_signing": true
  },
  "schema_version": 1,
  "synthetic": true,
  "target": {
    "family": "solana",
    "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
    "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
  }
}
```
