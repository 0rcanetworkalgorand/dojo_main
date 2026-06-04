# Implementation Plan: Semifinal Hardening

## Overview

This plan hardens the 0rca Swarm Dojo project for the Algorand hackathon semifinal. Tasks produce verifiable evidence — a green frontend build, passing contract tests (example-based and property-based), consistent App IDs, a value proposition artifact, and DoraHacks discoverability. No deployed contract logic is modified.

Tasks are ordered by judging impact: frontend build green first, then economic tests, property tests, stretch tests, App ID verification, value prop artifact, and DoraHacks re-tag last.

## Tasks

- [x] 1. Fix frontend build to achieve green `npm run build`
  - [x] 1.1 Diagnose and fix TypeScript compilation errors in `dojo-frontend/`
    - Run `npm run build` in `dojo-frontend/` and capture all TypeScript errors
    - Fix wallet signer type errors (algosdk signer references need explicit annotations or casts)
    - Fix `sha256` and `from` type/import errors
    - Ensure `socket.io-client` types resolve (v4+ bundles its own types — remove any stale `@types/socket.io-client` if present)
    - Repeat the fix-and-rebuild cycle until exit code 0 with zero TS errors
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 1.2 Record build evidence
    - Create `dojo-frontend/BUILD_EVIDENCE.md` documenting: exact build command (`npm run build`), working directory (`dojo-frontend/`), exit code (0), Node.js version, npm version
    - _Requirements: 1.4_

- [x] 2. Implement EscrowVault economic example tests
  - [x] 2.1 Create `dojo-contracts/tests/test_escrow_economic.py` with example-based economic split tests
    - Follow existing test patterns in `test_escrow_vault.py` (fixtures: `context`, `deployed`, `accounts`, helper `_lock_bounty`)
    - Implement `test_release_fee_and_sensei_amounts`: lock bounty of 1_000_033 (not divisible by 50), submit, release — assert treasury gets `(1_000_033 * 200) // 10000 = 20_000` and sensei gets `980_033`
    - Implement `test_release_conservation_of_funds`: assert `fee + sensei_payment == bounty` for a concrete amount
    - Implement `test_slash_returns_full_bounty`: assert client gets 100% bounty, no fee, no payment to treasury or sensei
    - _Requirements: 2.1, 2.2, 2.5_

  - [x] 2.2 Add negative-path guard tests to `dojo-contracts/tests/test_escrow_economic.py`
    - Implement `test_release_requires_submitted_status_locked`: release on LOCKED (status=0) fails with AssertionError
    - Implement `test_release_requires_submitted_status_completed`: release on COMPLETED (status=2) fails
    - Implement `test_release_requires_submitted_status_slashed`: release on SLASHED (status=3) fails
    - Implement `test_release_requires_nonzero_kite_hash`: release with 32 zero-byte kite_hash fails
    - Implement `test_slash_fails_on_completed`: slash on status=2 fails
    - Implement `test_slash_fails_on_slashed`: slash on status=3 fails
    - Implement `test_release_unauthorized`: random account cannot call release_payment
    - Implement `test_slash_unauthorized`: random account cannot call slash_bounty
    - After each failed call, verify task status byte is unchanged and no inner payments issued
    - _Requirements: 2.3, 2.4, 2.6, 2.7_

  - [x] 2.3 Verify all economic tests pass with `pytest dojo-contracts/tests/test_escrow_economic.py -v`
    - Run tests and confirm zero-exit-code, all pass
    - _Requirements: 2.8_

- [x] 3. Checkpoint — Economic example tests green
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement EscrowVault property-based tests with Hypothesis
  - [x] 4.1 Create `dojo-contracts/tests/test_escrow_properties.py` with property tests for fee formula and conservation
    - Use `hypothesis` library with `@given(bounty=st.integers(min_value=1, max_value=2**64 - 1))`
    - Use `@settings(max_examples=200)` on each property test
    - Add `@example` decorators for boundary values: 1, 49, 50, 51, 2**64 - 1
    - Implement property test for **Property 1 (Fee formula correctness)**: assert `fee == (bounty * 200) // 10000` and `sensei_payment == bounty - fee`
    - Implement property test for **Property 2 (Conservation of funds on release)**: assert `fee + sensei_payment == bounty`
    - Tag each test: `# Feature: semifinal-hardening, Property N: <text>`
    - _Requirements: 3.1, 3.2, 3.5_

  - [x]* 4.2 Write property test for release guard — no payout without valid preconditions
    - **Property 3: Release guard — no payout without valid preconditions**
    - Generate task states where status != SUBMITTED or kite_hash is zero
    - Assert assertion error raised, no inner payments issued, status unchanged
    - **Validates: Requirements 2.3, 2.4, 3.4**

  - [x]* 4.3 Write property test for slash returns full bounty
    - **Property 4: Slash returns full bounty**
    - Generate bounty amounts in [1, 2^64 - 1], set up task as LOCKED or SUBMITTED, slash
    - Assert client refund == full bounty amount
    - **Validates: Requirements 2.5, 3.3**

  - [x]* 4.4 Write property test for slash guard — no refund on settled tasks
    - **Property 5: Slash guard — no refund on already-settled tasks**
    - Generate tasks with status COMPLETED or SLASHED, attempt slash
    - Assert assertion error raised, no inner payment, status unchanged
    - **Validates: Requirements 2.6**

  - [x]* 4.5 Write property test for authorization guard
    - **Property 6: Authorization guard**
    - Generate random accounts that are neither client nor admin, attempt release and slash
    - Assert authorization assertion error, no inner payment, status unchanged
    - **Validates: Requirements 2.7**

  - [x] 4.6 Verify all property tests pass with `pytest dojo-contracts/tests/test_escrow_properties.py -v`
    - Run tests and confirm zero-exit-code, all pass with ≥200 examples per property
    - _Requirements: 3.5_

- [x] 5. Checkpoint — Property tests green
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement stretch tests (PayoutSplitter + Agent lanes)
  - [x]* 6.1 Create `dojo-contracts/tests/test_payout_splitter_properties.py` with property tests
    - **Property 7: PayoutSplitter conservation of funds**
    - Generate 1–16 recipients with percentages summing to exactly 10000 bps
    - Assert sum of all recipient payments equals original payment amount
    - **Property 8: PayoutSplitter rejects invalid percentage sums**
    - Generate percentage sets NOT summing to 10000, assert assertion error
    - Use `@settings(max_examples=200)` and `@example` for boundary cases
    - **Validates: Requirements 4.1, 4.2**

  - [x]* 6.2 Create `dojo-agents/tests/test_lane_validation.py` with agent lane validation tests
    - **Property 9: Agent lane payload validation**
    - Test each lane's `validate_task_payload` method
    - Research lane: valid if payload contains `query` or `description`
    - Code lane: valid if payload contains `description` or `query`
    - Data lane: valid if payload contains `data` or `operation`
    - Outreach lane: valid if payload contains `recipient` or `goal`
    - Test positive cases (valid payloads pass) and negative cases (missing required fields fail)
    - **Validates: Requirements 4.3, 4.4**

  - [x]* 6.3 Verify stretch tests pass with `pytest`
    - Run `pytest dojo-contracts/tests/test_payout_splitter_properties.py -v`
    - Run `pytest dojo-agents/tests/test_lane_validation.py -v`
    - Confirm zero exit code and all cases passing
    - **Validates: Requirements 4.5**

- [x] 7. Verify App ID consistency across all documentation
  - [x] 7.1 Grep repository for App ID references and verify consistency
    - Search all `.md`, `.env`, `.env.example`, and config files for each of the four App IDs: DojoRegistry 758815322, EscrowVault 761941677, CommitmentLock 761941684, PayoutSplitter 758815334
    - For each match, verify surrounding context maps the ID to the correct contract name
    - Correct any mismatched or orphan IDs in place
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 7.2 Create `evidence/APP_ID_VERIFICATION.md` recording verification results
    - List all files checked
    - Record per-file outcome: consistent, or mismatched-then-corrected
    - Include the authoritative App ID set for reference
    - _Requirements: 5.5_

- [x] 8. Create Value Proposition artifact
  - [x] 8.1 Create `VALUE_PROPOSITION.md` at repository root
    - State 98% developer take and 2% protocol fee, contrasted with ~20% centralized freelance fees and ≥30% other platform cuts
    - State 3.3s Algorand settlement finality vs 1+ day (multi-day) centralized payouts
    - Include blockchain rationale covering all four elements: trustless collateral-backed escrow, ungameable on-chain reputation, atomic payment+app-call transaction groups, instant settlement
    - Derive unit economics from `GTM_PLAN.md`: 2% fee, 10% slash, average 5 ALGO bounty → 0.1 ALGO protocol revenue per task
    - Cross-reference all figures against `GTM_PLAN.md` to ensure exact match
    - Make the document human-readable Markdown (no build required)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 9. Document DoraHacks re-tag as a human action
  - [x] 9.1 Create `evidence/DORAHACKS_TAGS.md` with instructions and evidence template
    - Document the manual steps: navigate to DoraHacks submission, add "Algorand" tag while retaining "AI / Robotics" tag, verify both visible on public page
    - Include a template for recording: final tag set, public submission URL, verification timestamp
    - Include fallback note: if "Algorand" tag cannot be added (platform limitation), record the failure reason
    - Mark clearly that this is a MANUAL step to be performed by the maintainer
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 10. Final checkpoint — All tests green, artifacts committed
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–9)
- Unit/example tests validate specific scenarios and edge cases
- Task 9 (DoraHacks re-tag) is a manual human action — the sub-agent creates the evidence template only
- The design specifies Python (`pytest`, `hypothesis`, `algopy_testing`) for all contract and agent tests
- The frontend is TypeScript/Next.js — fixes are applied directly to `.ts`/`.tsx` files in `dojo-frontend/src/`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["2.2", "7.1", "8.1"] },
    { "id": 3, "tasks": ["2.3", "7.2", "9.1"] },
    { "id": 4, "tasks": ["4.1"] },
    { "id": 5, "tasks": ["4.2", "4.3", "4.4", "4.5"] },
    { "id": 6, "tasks": ["4.6", "6.1", "6.2"] },
    { "id": 7, "tasks": ["6.3"] }
  ]
}
```
