# App ID Consistency Verification

## Authoritative App ID Set

| Contract | App ID |
|----------|--------|
| DojoRegistry | 758815322 |
| EscrowVault | 761941677 |
| CommitmentLock | 761941684 |
| PayoutSplitter | 758815334 |

## Verification Results

### Files Checked — Consistent (No Changes Needed)

| File | App IDs Found | Status |
|------|--------------|--------|
| `README.md` | DojoRegistry 758815322, EscrowVault 761941677, CommitmentLock 761941684, PayoutSplitter 758815334 | ✅ Consistent |
| `dojo-contracts/DEPLOYMENT_INFO.md` | All four App IDs in table + explorer URLs | ✅ Consistent |
| `dojo-frontend/README.md` | All four App IDs in table | ✅ Consistent |
| `dojo-contracts/README.md` | All four App IDs in table | ✅ Consistent |
| `dojo-contracts/deployment_testnet.json` | All four App IDs | ✅ Consistent |
| `dojo-frontend/.env.local` | All four App IDs | ✅ Consistent |
| `dojo-backend/.env` | All four App IDs | ✅ Consistent |
| `dojo-agents/main.py` | DojoRegistry 758815322 (fallback), EscrowVault 761941677 (fallback) | ✅ Consistent |
| `dojo-agents/scripts/admin_register_agent.py` | DojoRegistry 758815322 (hardcoded) | ✅ Consistent |
| `IMPLEMENTATION_ROADMAP.md` | DojoRegistry 758815322, EscrowVault 761941677 | ✅ Consistent |
| `dojo-frontend/src/app/tasks/post/page.tsx` | EscrowVault 761941677 (fallback) | ✅ Consistent |
| `dojo-frontend/src/app/hire/page.tsx` | EscrowVault 761941677 (fallback, two occurrences) | ✅ Consistent |
| `dojo-frontend/src/app/build/page.tsx` | CommitmentLock 761941684 (fallback) | ✅ Consistent |
| `swarm-frontend/src/app/tasks/post/page.tsx` | EscrowVault 761941677 (fallback) | ✅ Consistent |
| `swarm-frontend/src/app/build/page.tsx` | CommitmentLock 761941684 (fallback) | ✅ Consistent |
| `dojo-contracts/fund_contracts.js` | EscrowVault 761941677, CommitmentLock 761941684 | ✅ Consistent |
| `dojo-backend/test_lock_bounty.ts` | EscrowVault 761941677 (fallback) | ✅ Consistent |
| `dojo-backend/test_stake.ts` | CommitmentLock 761941684 (fallback) | ✅ Consistent |

### Files Corrected — Mismatched or Incomplete (Fixed)

| File | Issue | Correction |
|------|-------|-----------|
| `dojo-frontend/.env.example` | Missing `NEXT_PUBLIC_ESCROW_VAULT_APP_ID` and `NEXT_PUBLIC_PAYOUT_SPLITTER_APP_ID`; existing entries had empty values | Added all four App IDs with correct values |
| `swarm-frontend/.env.example` | Missing `NEXT_PUBLIC_ESCROW_VAULT_APP_ID` and `NEXT_PUBLIC_PAYOUT_SPLITTER_APP_ID`; existing entries had empty values | Added all four App IDs with correct values |
| `INTEGRATION_GUIDE.md` (backend section) | Missing `COMMITMENT_LOCK_APP_ID` and `PAYOUT_SPLITTER_APP_ID` | Added both entries with correct values |
| `INTEGRATION_GUIDE.md` (frontend section) | Missing `NEXT_PUBLIC_COMMITMENT_LOCK_APP_ID` and `NEXT_PUBLIC_PAYOUT_SPLITTER_APP_ID` | Added both entries with correct values |
| `dojo-contracts/deployment_updated.json` | Missing `DojoRegistry` and `PayoutSplitter` entries | Added both with correct App IDs |

### Stale/Orphan IDs

No stale or orphan App IDs found. All numeric IDs in the repository match one of the four authoritative values and are mapped to the correct contract name in their surrounding context.

## Verification Method

- Used `grep` to search for each of the four authoritative App IDs across all `.md`, `.env`, `.env.example`, `.env.local`, `.json`, `.js`, `.ts`, `.tsx`, and `.py` files.
- Excluded `node_modules/`, `.git/`, `.next/`, `dist/`, `.venv/`, `__pycache__/`, and `.ruff_cache/` directories.
- For each match, verified that the surrounding context (variable name, table column, or JSON key) maps the ID to the correct contract name.
- Searched for any 9-digit numbers starting with 7 to identify potential stale App IDs not in the authoritative set — none found.
- Verified `.env.example` files provide all four App IDs for developer reference.

## Date

Verified: 2025-01-20
