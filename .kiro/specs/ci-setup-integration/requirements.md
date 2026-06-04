# Requirements Document

## Introduction

This feature bundles three complementary improvements to the 0rca Swarm Dojo project aimed at demonstrating engineering maturity to hackathon judges: a CI pipeline with a visible status badge, a one-command local setup script, and a full-lifecycle integration test that exercises the real Algorand TestNet contracts end-to-end. Together these prove the project is maintained, easy to evaluate, and functionally complete.

## Glossary

- **CI_Pipeline**: A GitHub Actions workflow that automatically builds and tests the project on every push to main and on every pull request.
- **Badge**: A Markdown status image embedded in README.md that reflects the latest CI run result (green for passing, red for failing).
- **Setup_Script**: A PowerShell script (or Makefile) that boots all local services and seeds the database in a single command.
- **Integration_Test**: A pytest-based test script that exercises the full task lifecycle against deployed Algorand TestNet contracts and the running backend.
- **EscrowVault**: The Algorand smart contract (App ID 761941677) that locks client bounties and distributes payments on task completion.
- **Backend**: The Express + Prisma + SQLite API server located in dojo-backend/, running on port 3001.
- **Frontend**: The Next.js 14 application located in dojo-frontend/, running on port 3000.
- **Contract_Tests**: The pytest suite located in dojo-contracts/tests/ that validates smart contract logic.
- **Admin_Mnemonic**: The Algorand account mnemonic used to sign administrative transactions; stored as a GitHub Actions secret for CI and in a local .env file for development.
- **Provenance_Hash**: A 32-byte hash submitted to EscrowVault via submit_task to prove task completion before payment release.
- **Task_Lifecycle**: The complete flow from task creation through escrow lock, task submission with provenance hash, to payment release.

## Requirements

### Requirement 1: CI Workflow File

**User Story:** As a hackathon judge, I want to see an automated CI pipeline, so that I can immediately verify the project builds and tests pass without running anything locally.

#### Acceptance Criteria

1. THE CI_Pipeline SHALL be defined in a GitHub Actions workflow file at `.github/workflows/ci.yml`.
2. WHEN a push to the main branch occurs, THE CI_Pipeline SHALL trigger a build-and-test run.
3. WHEN a pull request targeting the main branch is opened or updated, THE CI_Pipeline SHALL trigger a build-and-test run.
4. THE CI_Pipeline SHALL run on the `ubuntu-latest` runner image and complete within 10 minutes or be terminated by a workflow-level timeout.
5. THE CI_Pipeline SHALL use Node.js version 20 and execute `npm ci` followed by `npm run build` in the `dojo-frontend/` directory to verify the Frontend compiles with a zero exit code.
6. THE CI_Pipeline SHALL use Python version 3.12, install dependencies from `dojo-contracts/requirements.txt`, and execute `pytest` in the `dojo-contracts/` directory to run all Contract_Tests.
7. IF the Frontend build step returns a non-zero exit code, THEN THE CI_Pipeline SHALL report a failing workflow status and skip all subsequent steps in the pipeline.
8. IF any Contract_Test fails or `pytest` returns a non-zero exit code, THEN THE CI_Pipeline SHALL report a failing workflow status.
9. WHEN a build-and-test run completes successfully, THE CI_Pipeline SHALL report a passing workflow status visible as a green check on the commit or pull request in GitHub.

### Requirement 2: CI Status Badge

**User Story:** As a hackathon judge, I want a CI status badge at the top of the README, so that I can see at a glance whether the project passes its checks.

#### Acceptance Criteria

1. THE Badge SHALL be displayed as the first visual element in README.md, before the project title heading.
2. THE Badge SHALL link to the GitHub Actions workflow runs page for the CI_Pipeline.
3. WHEN the CI_Pipeline succeeds, THE Badge SHALL display a green "passing" indicator.
4. WHEN the CI_Pipeline fails, THE Badge SHALL display a red "failing" indicator.

### Requirement 3: One-Command Local Setup Script

**User Story:** As a hackathon judge evaluating the project on Windows, I want to boot the entire local stack with a single command, so that I do not need to open multiple terminals and run separate setup steps.

#### Acceptance Criteria

1. THE Setup_Script SHALL be implemented as a PowerShell script named `setup.ps1` located in the repository root.
2. WHEN the Setup_Script is executed, THE Setup_Script SHALL install Backend npm dependencies by running `npm install` in `dojo-backend/`.
3. WHEN the Setup_Script is executed, THE Setup_Script SHALL run `npx prisma generate` and `npx prisma migrate dev` in `dojo-backend/` to seed the database.
4. WHEN the Setup_Script is executed, THE Setup_Script SHALL install Frontend npm dependencies by running `npm install` in `dojo-frontend/`.
5. WHEN the Setup_Script is executed, THE Setup_Script SHALL start the Backend on port 3001 as a background process and SHALL verify readiness by polling `http://localhost:3001` until a successful HTTP response is received or a 30-second timeout elapses.
6. WHEN the Setup_Script is executed, THE Setup_Script SHALL start the Frontend on port 3000 as a background process and SHALL verify readiness by polling `http://localhost:3000` until a successful HTTP response is received or a 30-second timeout elapses.
7. WHEN both the Backend and Frontend readiness checks have received a successful HTTP response, THE Setup_Script SHALL print a summary message listing the URLs `http://localhost:3001` and `http://localhost:3000`.
8. IF `npm install` fails in either directory, THEN THE Setup_Script SHALL print an error message identifying the failing directory and exit with a non-zero exit code.
9. IF `prisma migrate dev` fails, THEN THE Setup_Script SHALL print a database migration error message and exit with a non-zero exit code.
10. IF the Backend or Frontend readiness check does not receive a successful HTTP response within 30 seconds, THEN THE Setup_Script SHALL print an error message identifying which service failed to start and exit with a non-zero exit code.
11. THE Setup_Script SHALL include a companion `Makefile` at the repository root with targets `setup`, `dev`, and `stop` that wrap equivalent commands for Linux and macOS users.
12. THE Setup_Script SHALL provide a `stop` function or companion script (`stop.ps1`) at the repository root that terminates the Backend and Frontend background processes started by the Setup_Script.

### Requirement 4: Integration Test — Task Creation and Escrow Lock

**User Story:** As a developer, I want an automated test that creates a task via the Backend API and verifies the escrow is locked on-chain, so that I can prove the backend-to-contract path works.

#### Acceptance Criteria

1. THE Integration_Test SHALL be implemented as a pytest module located at `tests/integration/test_task_lifecycle.py` in the repository root.
2. WHEN the Integration_Test executes the task-creation step, THE Integration_Test SHALL send an HTTP POST request to the Backend endpoint `POST /api/tasks` with a JSON payload containing `onChainTaskId` (a unique string identifier), `clientAddress` (a valid Algorand address), `agentAddress` (a valid Algorand address), `description` (a non-empty string of at most 500 characters), and `bountyUsdc` (an integer greater than zero).
3. WHEN the Backend responds with a 201 status code, THE Integration_Test SHALL extract the returned task ID from the response body.
4. IF the Backend responds with a status code other than 201, THEN THE Integration_Test SHALL fail the test with an assertion that includes the HTTP status code and response body.
5. WHEN the task ID has been extracted, THE Integration_Test SHALL call the EscrowVault `lock_bounty` method on Algorand TestNet using the Admin_Mnemonic, supplying the task ID, client address, worker address, sensei address, bounty amount in microAlgos, and a grouped payment transaction transferring exactly the bounty amount to the EscrowVault application address.
6. WHEN the `lock_bounty` transaction is confirmed, THE Integration_Test SHALL query the EscrowVault `get_task` method with the same task ID and SHALL assert that the returned 137-byte box contains the client address at bytes 0–31, the worker address at bytes 32–63, the sensei address at bytes 64–95, and the bounty amount at bytes 96–103, all matching the values supplied in the `lock_bounty` call, and that the status byte at offset 104 equals 0 (LOCKED).
7. IF the `lock_bounty` call is rejected by the network or reverts with an assertion error, THEN THE Integration_Test SHALL fail the test with an assertion that includes the transaction error message.
8. THE Integration_Test SHALL complete the full task-creation-and-escrow-lock sequence within 60 seconds; if any step exceeds this duration, the test SHALL fail with a timeout error.

### Requirement 5: Integration Test — Task Submission with Provenance Hash

**User Story:** As a developer, I want the integration test to simulate an agent submitting completed work with a provenance hash, so that I can prove the submission path updates on-chain state correctly.

#### Acceptance Criteria

1. WHEN the escrow box is confirmed locked, THE Integration_Test SHALL call the EscrowVault `submit_task` method with the task ID and a valid 32-byte Provenance_Hash signed by the worker account.
2. AFTER submitting, THE Integration_Test SHALL query the EscrowVault `get_task` method and verify the task status byte equals 1 (SUBMITTED).
3. AFTER submitting, THE Integration_Test SHALL verify the stored kite_hash matches the Provenance_Hash that was submitted.

### Requirement 6: Integration Test — Payment Release and Distribution

**User Story:** As a developer, I want the integration test to release payment and verify funds reach the correct accounts, so that I can prove end-to-end settlement works on TestNet.

#### Acceptance Criteria

1. WHEN the task status is SUBMITTED and the kite_hash is non-zero, THE Integration_Test SHALL record the current ALGO balances of the sensei account and the treasury account, then call the EscrowVault `release_payment` method signed by the client account or the admin, passing the task ID and treasury address, and SHALL wait up to 10 seconds for the transaction to confirm on TestNet.
2. WHEN the release_payment transaction confirms successfully, THE Integration_Test SHALL query the EscrowVault `get_task` method and verify that the task status byte at box offset 104 equals 2 (COMPLETED).
3. WHEN the release_payment transaction confirms successfully, THE Integration_Test SHALL verify that the sensei account balance increased by at least `bounty - ((bounty * 200) // 10000) - 5000` microAlgos compared to the pre-release balance, where the 5000 microAlgo tolerance accounts for a maximum of 5 inner-transaction minimum fees (1000 microAlgos each).
4. WHEN the release_payment transaction confirms successfully, THE Integration_Test SHALL verify that the treasury account balance increased by exactly `(bounty * 200) // 10000` microAlgos compared to the pre-release balance, with a tolerance of 1000 microAlgos for a single transaction minimum fee.
5. IF the release_payment transaction fails or does not confirm within 10 seconds, THEN THE Integration_Test SHALL fail the test with an error indication that includes the task ID and the reason for the transaction failure or timeout.

### Requirement 7: Integration Test Configuration and Secrets

**User Story:** As a developer, I want the integration test to load credentials securely from environment variables, so that secrets are never committed to source control.

#### Acceptance Criteria

1. THE Integration_Test SHALL read the Admin_Mnemonic from the environment variable `ADMIN_MNEMONIC`.
2. THE Integration_Test SHALL read the Algorand node URL from the environment variable `ALGOD_SERVER`, defaulting to `https://testnet-api.algonode.cloud` when not set.
3. THE Integration_Test SHALL read the EscrowVault app ID from the environment variable `ESCROW_VAULT_APP_ID`, defaulting to `761941677` when not set.
4. IF the `ADMIN_MNEMONIC` environment variable is not set, THEN THE Integration_Test SHALL skip all test cases with a clear message indicating the missing secret.
5. THE Integration_Test SHALL use a `.env` file in the repository root for local development, loaded via the `python-dotenv` library.
6. THE CI_Pipeline SHALL inject `ADMIN_MNEMONIC` from GitHub Actions secrets when running the Integration_Test in CI.

### Requirement 8: Integration Test Isolation

**User Story:** As a developer, I want each integration test run to use unique task IDs, so that tests do not conflict with previous runs or other developers.

#### Acceptance Criteria

1. THE Integration_Test SHALL generate a unique task ID for each test run using a UUID or timestamp-based identifier.
2. THE Integration_Test SHALL use dedicated test accounts (derived from Admin_Mnemonic) that are pre-funded on TestNet.
3. IF a test fails mid-lifecycle, THEN THE Integration_Test SHALL not leave the EscrowVault in an inconsistent state that blocks subsequent test runs (each run uses a fresh task ID).
