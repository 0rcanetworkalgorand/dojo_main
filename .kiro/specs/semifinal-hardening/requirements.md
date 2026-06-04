# Requirements Document

## Introduction

This feature hardens the 0rca Swarm Dojo project ahead of the Algorand hackathon semifinal. It bundles four concrete gaps identified in a competitive review against the weighted judging criteria (Business 40%, Technical 30%, Scalability & Execution 30%). The goal is to close the distance between a finalist-grade idea and shipped, verifiable evidence that judges can inspect: a green reproducible frontend build, automated tests proving the contracts honor their stated economic guarantees, consistent and discoverable Algorand metadata across documentation and the public submission, and judge-facing materials that quantify the value proposition.

The work spans four scoped areas:

1. **Frontend Build Health** — Re-establish a verified, reproducible green frontend build.
2. **Test Suite** — Add automated evidence that the smart contracts conform to their economic guarantees, with stretch coverage for payout splitting and the Python agent lanes.
3. **Algorand Discoverability & Consistency** — Verify all docs and environment-variable examples reference consistent deployed App IDs, and re-tag the public DoraHacks submission to surface Algorand.
4. **Value Proposition Quantification** — Produce a presentable judge-facing artifact quantifying cost, settlement speed, and the rationale for using a blockchain.

This is a hardening and evidence-gathering effort. It does not change the deployed contract logic, the economic parameters, or the runtime behavior of the platform.

## Glossary

- **Dojo_Frontend**: The Next.js 14 web application located in `dojo-frontend/`, built with `next build`.
- **Frontend_Build_Process**: The TypeScript compilation and Next.js production build invoked via `npm run build` in `dojo-frontend/`.
- **EscrowVault**: The PuyaPy smart contract (`dojo-contracts/projects/smart_contracts/escrow_vault/contract.py`, App ID 761941677) that holds a per-task ALGO bounty and settles it.
- **PayoutSplitter**: The PuyaPy smart contract (`dojo-contracts/projects/smart_contracts/payout_splitter/contract.py`, App ID 758815334) that distributes ALGO across multiple recipients.
- **release_payment**: The EscrowVault method that, on a SUBMITTED task with a valid provenance hash, pays a 2% protocol fee to the treasury and 98% to the sensei.
- **slash_bounty**: The EscrowVault method that refunds 100% of the bounty to the client when a task fails.
- **Sensei**: The developer who deployed the agent and receives 98% of a successful bounty.
- **Client**: The user who funds a task bounty and receives a 100% refund on slash.
- **Treasury**: The platform wallet that receives the 2% protocol fee.
- **kite_hash**: The Kite AI provenance hash stored on the task box; a non-zero value is required before payment can release.
- **Task_Status**: The EscrowVault task lifecycle state stored at box byte offset 104 — 0 = LOCKED, 1 = SUBMITTED, 2 = COMPLETED, 3 = SLASHED.
- **Contract_Test_Suite**: The pytest-based tests under `dojo-contracts/tests/` that run against the `algopy_testing` harness.
- **Agent_Lane**: One of the four Python agent execution lanes (Research, Code, Data, Outreach) in `dojo-agents/lanes/`.
- **App_ID**: The Algorand application identifier for a deployed contract.
- **Deployed_App_IDs**: The reconciled, authoritative App ID set — DojoRegistry 758815322, EscrowVault 761941677, CommitmentLock 761941684, PayoutSplitter 758815334.
- **Project_Documentation**: The Markdown documentation and environment-variable example files in the repository (including `README.md`, `dojo-contracts/DEPLOYMENT_INFO.md`, and `.env.example` files).
- **DoraHacks_Submission**: The public hackathon submission entry for the project on the DoraHacks platform.
- **Value_Prop_Artifact**: The judge-facing deliverable that quantifies the project's value proposition (cost, settlement speed, and blockchain rationale).
- **Maintainer**: The person performing the hardening tasks and the external actions that cannot be automated (such as re-tagging the DoraHacks submission).

## Requirements

### Requirement 1: Frontend Build Health

**User Story:** As a maintainer preparing for the semifinal, I want a verified green frontend build, so that judges and reviewers can reproduce a clean compile and trust the shipped UI.

#### Acceptance Criteria

1. WHEN the Frontend_Build_Process is run via `npm run build` in `dojo-frontend/`, THE Dojo_Frontend SHALL complete the build with a zero exit code, no TypeScript compilation errors emitted to stdout or stderr, and a generated production build output.
2. IF the Frontend_Build_Process reports a TypeScript compilation error, THEN THE Maintainer SHALL correct the reported error and re-run the Frontend_Build_Process, repeating the correct-and-re-run cycle until the build completes with a zero exit code and zero TypeScript compilation errors.
3. THE Dojo_Frontend SHALL declare `socket.io-client` as a resolvable production dependency such that every Socket.IO client type reference resolves and compiles with zero missing-type errors.
4. WHEN the Frontend_Build_Process completes with a zero exit code and no TypeScript compilation errors, THE Maintainer SHALL record, as committed evidence in the repository, the exact build command, the `dojo-frontend/` working directory, the resulting zero exit code, and the Node.js and npm versions used to produce the build.
5. WHERE wallet signer, `sha256`, or `from` type errors previously occurred, THE Dojo_Frontend SHALL compile the affected modules with zero TypeScript type errors for those references.

### Requirement 2: Smart Contract Economic Test Coverage

**User Story:** As a maintainer, I want automated tests proving the EscrowVault honors its economic split and guard conditions, so that judges have evidence the software conforms to its stated economic guarantees.

#### Acceptance Criteria

1. WHEN release_payment settles a task that is in SUBMITTED status with a non-zero kite_hash, THE Contract_Test_Suite SHALL assert that the Treasury receives exactly the floored 2% fee (`(bounty * 200) // 10000`) and the Sensei receives exactly the remaining amount (`bounty - fee`), and SHALL include at least one bounty amount that is not evenly divisible by 50 microAlgos so that fee floor-truncation is exercised.
2. WHEN release_payment settles a task, THE Contract_Test_Suite SHALL assert that the sum of the Treasury fee and the Sensei payment equals the original bounty amount.
3. IF release_payment is called on a task whose Task_Status is not SUBMITTED (that is, LOCKED, COMPLETED, or SLASHED), THEN THE Contract_Test_Suite SHALL assert that the call fails with an assertion error, that no inner payment is issued to the Treasury or the Sensei, and that the Task_Status is left unchanged.
4. IF release_payment is called on a task whose kite_hash is the zero value, THEN THE Contract_Test_Suite SHALL assert that the call fails with an assertion error, that no inner payment is issued to the Treasury or the Sensei, and that the Task_Status is left unchanged.
5. WHEN slash_bounty settles a failed task, THE Contract_Test_Suite SHALL assert that the Client receives exactly 100% of the bounty amount, that no fee is deducted, and that no inner payment is issued to the Treasury or the Sensei.
6. IF slash_bounty is called on a task whose Task_Status is greater than 1 (already COMPLETED or SLASHED), THEN THE Contract_Test_Suite SHALL assert that the call fails with an assertion error, that no inner payment is issued to the Client, and that the Task_Status is left unchanged.
7. WHEN release_payment or slash_bounty is invoked by an account that is neither the Client nor the admin, THE Contract_Test_Suite SHALL assert that the call fails with an authorization assertion error, that no inner payment is issued, and that the Task_Status is left unchanged.
8. WHEN the Contract_Test_Suite is executed via `pytest` in `dojo-contracts/`, THE Contract_Test_Suite SHALL run to completion with a zero exit code and with the tests covering acceptance criteria 1 through 7 all passing, where assertion errors raised inside the contract during negative-path tests are the expected, asserted outcome of those tests.

### Requirement 3: Economic Invariant Property Tests

**User Story:** As a maintainer, I want property-based tests over a range of bounty amounts, so that the EscrowVault economic invariants hold across many inputs rather than a few hand-picked examples.

#### Acceptance Criteria

1. FOR ALL bounty amounts within the supported microAlgo range (1 to 18,446,744,073,709,551,615, the unsigned 64-bit maximum), WHEN release_payment settles a SUBMITTED task with a valid kite_hash, THE Contract_Test_Suite SHALL assert that `fee + sensei_payment == bounty` (conservation of funds).
2. FOR ALL bounty amounts within the supported microAlgo range, WHEN release_payment settles a task, THE Contract_Test_Suite SHALL assert that `fee == (bounty * 200) // 10000` using integer floor division and `sensei_payment == bounty - fee`.
3. FOR ALL bounty amounts within the supported microAlgo range, WHEN slash_bounty settles a task whose Task_Status is LOCKED or SUBMITTED (status <= 1), THE Contract_Test_Suite SHALL assert that the Client refund equals the full bounty amount (`refund == bounty`).
4. FOR ALL task states where the kite_hash is zero or the Task_Status is not SUBMITTED, WHEN release_payment is invoked, THE Contract_Test_Suite SHALL assert the observable no-payout outcome: an assertion error is raised, no inner payment is issued to the Treasury or the Sensei, and the Task_Status is left unchanged (no payout without valid provenance).
5. THE Contract_Test_Suite SHALL sample at least 100 generated bounty values per property and SHALL additionally include the boundary values 1, 49, 50, 51, and the unsigned 64-bit maximum, so that the floored-fee-zero region (fee is 0 below a bounty of 50 microAlgos and first becomes non-zero at 50) and the maximum are exercised.

### Requirement 4: Stretch Test Coverage

**User Story:** As a maintainer, I want additional tests for the PayoutSplitter and the Python agent lanes, so that more of the system's behavior is backed by automated evidence.

#### Acceptance Criteria

1. WHERE PayoutSplitter stretch coverage is implemented, WHEN split_percentage distributes a payment across 1 to 16 recipients whose percentages sum to exactly 10000 basis points, THE Contract_Test_Suite SHALL assert that the sum of all recipient payments equals the original payment amount.
2. WHERE PayoutSplitter stretch coverage is implemented, IF split_percentage is called with percentages that do not sum to exactly 10000 basis points, THEN THE Contract_Test_Suite SHALL assert that the call fails with an assertion error and that no recipient payment is dispatched.
3. WHERE Python agent lane stretch coverage is implemented, WHEN an Agent_Lane (Research, Code, Data, or Outreach) validates a payload that contains all of its required fields, THE lane test SHALL assert that validation returns a pass result.
4. WHERE Python agent lane stretch coverage is implemented, IF an Agent_Lane validates a payload that is missing a required field, THEN THE lane test SHALL assert that validation returns a fail result.
5. WHERE stretch tests are implemented, WHEN the stretch tests are executed via `pytest`, THE stretch tests SHALL run to completion with a zero exit code and all included cases passing, where assertion errors raised inside a contract during negative-path tests are the expected, asserted outcome of those tests.

### Requirement 5: Algorand App ID Consistency Verification

**User Story:** As a maintainer, I want all documentation and environment-variable examples to reference the same deployed App IDs, so that reviewers who copy values from any document interact with the correct on-chain contracts.

#### Acceptance Criteria

1. THE Maintainer SHALL verify that every App_ID referenced in Project_Documentation has a numeric value exactly equal to the Deployed_App_IDs value mapped to the same contract name (DojoRegistry 758815322, EscrowVault 761941677, CommitmentLock 761941684, PayoutSplitter 758815334).
2. WHEN an environment-variable example file within Project_Documentation references a contract App_ID, THE referenced App_ID value SHALL exactly equal the corresponding value in the Deployed_App_IDs set.
3. IF a referenced App_ID maps to a known contract name but its value does not equal the Deployed_App_IDs value, THEN THE Maintainer SHALL correct the referenced value to match the Deployed_App_IDs set and re-run the comparison until every App_ID reference is consistent.
4. IF a referenced App_ID value does not exist anywhere in the Deployed_App_IDs set (for example, a stale ID from a prior deployment), THEN THE Maintainer SHALL correct or remove the orphan reference and re-run the comparison until every App_ID reference is consistent.
5. WHEN the consistency verification is complete, THE Maintainer SHALL record, as committed evidence in the repository, the list of files checked and the per-file verification outcome (consistent, or mismatched-then-corrected).

### Requirement 6: DoraHacks Algorand Discoverability

**User Story:** As a maintainer, I want the DoraHacks submission tagged so Algorand is surfaced, so that the project appears in Algorand-track discovery and judges recognize it as an Algorand project.

#### Acceptance Criteria

1. THE Maintainer SHALL update the DoraHacks_Submission tags so that the resulting tag set contains an "Algorand" tag while retaining the existing "AI / Robotics" tag.
2. WHEN the DoraHacks_Submission tag update is saved, THE Maintainer SHALL verify on the publicly visible submission page that both the "Algorand" tag and the "AI / Robotics" tag are displayed.
3. IF the "Algorand" tag cannot be added to the DoraHacks_Submission (for example, the tag is unavailable or a platform tag limit is reached), THEN THE Maintainer SHALL leave the existing "AI / Robotics" tag unchanged and record the failure reason as evidence in the repository.
4. WHEN the DoraHacks_Submission tags are updated, THE Maintainer SHALL record the resulting complete tag set and the public submission URL in a version-controlled file in the repository as evidence.

### Requirement 7: Value Proposition Quantification Artifact

**User Story:** As a maintainer, I want a presentable artifact that quantifies the value proposition, so that judges can quickly grasp the cost, speed, and trust advantages of the platform.

#### Acceptance Criteria

1. THE Value_Prop_Artifact SHALL state, as explicit numeric figures, the 0rca developer take rate of 98% and the protocol fee of 2%, alongside the comparison figures of approximately 20% for a centralized freelance platform fee and 30% or more for other centralized platform cuts, such that all four figures (98%, 2%, ~20%, ≥30%) appear explicitly in the artifact.
2. THE Value_Prop_Artifact SHALL state the Algorand settlement finality of approximately 3.3 seconds and SHALL contrast it against centralized-platform payout timelines of one day or more (multi-day), such that both the 3.3-second figure and the multi-day comparison appear explicitly.
3. THE Value_Prop_Artifact SHALL state a blockchain-rationale answer that explicitly addresses all four of the following elements: trustless collateral-backed escrow, ungameable on-chain reputation, atomic payment-plus-app-call transaction groups, and instant settlement.
4. THE Value_Prop_Artifact SHALL derive its cost and fee figures from the values stated in `GTM_PLAN.md` (2% protocol fee, 10% stake slash on failure, average bounty 5 ALGO), and every monetary and percentage figure it states SHALL match the corresponding value in `GTM_PLAN.md`.
5. THE Value_Prop_Artifact SHALL be committed to the repository as a human-readable document that can be opened and read in a standard text or document viewer without building, compiling, or running the application.
6. IF any cost, fee, or settlement-time figure stated in the Value_Prop_Artifact does not match the corresponding value in `GTM_PLAN.md`, THEN THE Maintainer SHALL correct the figure so that it matches `GTM_PLAN.md`.
