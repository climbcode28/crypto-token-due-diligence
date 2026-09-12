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
  "collection_sha256": "35d65625ba4ecb6f71699f8bea0798fed0347414d1fecef719d9ea701126d280",
  "engine_version": "1.0.0",
  "evidence": [
    {
      "artifact": "evidence/block.json",
      "id": "block",
      "kind": "collector",
      "sha256": "3852583e3ddf82dc1639f9d273e5ea777440eea9c8d795ca4a9b2611c87a9af5",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/block_recheck.json",
      "id": "block_recheck",
      "kind": "collector",
      "sha256": "266580c52ee459b10d0ac28d435ea48b097e73dd4bb90512401fec8ab0cb5cab",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/end_block.json",
      "id": "end_block",
      "kind": "collector",
      "sha256": "351fa6eb9e63c9d0aaacf3e04d263fc9b7d25438cfa780b4b0ab80392acfc91b",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/end_block_recheck.json",
      "id": "end_block_recheck",
      "kind": "collector",
      "sha256": "3c35c1f0c767a2c1eef08959761b4ac8aeef957ea991cf2af7017ca02c23b82b",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/genesis.json",
      "id": "genesis",
      "kind": "collector",
      "sha256": "b69a719ea023bcbbf177c8815d05295e2f308b3af3be7f8f5749278ef8fabeea",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/genesis_recheck.json",
      "id": "genesis_recheck",
      "kind": "collector",
      "sha256": "16d4e8178cb0d35e3333f2065a1515552595d2cee3c13dac1e8568d7a027004b",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/largest.json",
      "id": "largest",
      "kind": "collector",
      "sha256": "15cca497d2ca1760bc19358881eda67fcfd414b0a3a826fdc9b9809d9f6e9153",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/mint.json",
      "id": "mint",
      "kind": "collector",
      "sha256": "8120e760076fdfb1a1a4645e0544d536ba1b5a63371b654c6b84ad24ffedbceb",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    },
    {
      "artifact": "evidence/mint_recheck.json",
      "id": "mint_recheck",
      "kind": "collector",
      "sha256": "ab3e2adbf62b348d19fad6bae8ee9759af93be312899c89a5ad747be342ef6cc",
      "source": "request and response in artifact",
      "subject": {
        "family": "solana",
        "genesis_hash": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
        "mint": "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi"
      },
      "time_basis": "See response context slot and collection samples; no exact-state pin."
    }
  ],
  "identity_evidence": [],
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
