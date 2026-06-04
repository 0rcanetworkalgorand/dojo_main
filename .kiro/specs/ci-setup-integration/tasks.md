# Implementation Plan: CI Setup & Integration

## Overview

This plan implements CI/CD infrastructure, local setup automation, and integration testing for the 0rca Swarm Dojo project. Tasks are ordered for maximum early visibility (green badge first) and build incrementally toward the full TestNet lifecycle test.

## Tasks

- [x] 1. Create CI workflow file
  - [x] 1.1 Create `.github/workflows/ci.yml` with build-and-test job
    - Define workflow triggers: `push` to `main`, `pull_request` targeting `main`
    - Set `timeout-minutes: 10` at workflow level
    - Create `build-and-test` job on `ubuntu-latest`
    - Add step: checkout with `actions/checkout@v4`
    - Add step: setup Node.js 20 with `actions/setup-node@v4`
    - Add step: `npm ci` in `dojo-frontend/`
    - Add step: `npm run build` in `dojo-frontend/`
    - Add step: setup Python 3.12 with `actions/setup-python@v5`
    - Add step: `pip install -r requirements.txt` in `dojo-contracts/`
    - Add step: `pytest` in `dojo-contracts/`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

- [x] 2. Add CI status badge to README
  - [x] 2.1 Determine GitHub owner/repo from git remote and insert badge at the top of README.md
    - Parse the git remote URL to extract `{owner}/{repo}`
    - Insert badge markdown as the very first line of `README.md`: `[![CI](https://github.com/{owner}/{repo}/actions/workflows/ci.yml/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/ci.yml)`
    - Ensure badge appears before the project title heading
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Checkpoint - Verify CI and badge
  - Ensure the CI workflow YAML is valid and the badge markdown is correctly placed. Ask the user if questions arise.

- [x] 4. Create local setup script (setup.ps1 + stop.ps1)
  - [x] 4.1 Create `setup.ps1` in the repository root
    - Step 1: Run `npm install` in `dojo-backend/` with error handling (exit code 1 on failure, message identifying directory)
    - Step 2: Run `npx prisma generate` and `npx prisma migrate dev` in `dojo-backend/` with error handling (exit code 1 on DB error)
    - Step 3: Run `npm install` in `dojo-frontend/` with error handling
    - Step 4: Use `Start-Process` to launch backend on port 3001 as background process
    - Step 5: Use `Start-Process` to launch frontend on port 3000 as background process
    - Step 6: Poll `http://localhost:3001` with 30-second timeout, exit with error if timeout
    - Step 7: Poll `http://localhost:3000` with 30-second timeout, exit with error if timeout
    - Step 8: Print success summary with both URLs
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

  - [x] 4.2 Create `stop.ps1` in the repository root
    - Find and terminate processes listening on port 3000 and 3001
    - Print confirmation of stopped services
    - _Requirements: 3.12_

- [x] 5. Create Makefile for Linux/macOS
  - [x] 5.1 Create `Makefile` in the repository root with `setup`, `dev`, and `stop` targets
    - `setup` target: install deps in both directories, run prisma migrate
    - `dev` target: start backend and frontend in background, poll for readiness
    - `stop` target: kill processes on ports 3000 and 3001
    - _Requirements: 3.11_

- [x] 6. Checkpoint - Verify setup scripts
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create integration test infrastructure
  - [x] 7.1 Create `tests/integration/requirements.txt`
    - Include: `py-algorand-sdk>=2.6.0`, `pytest>=7.4.0`, `pytest-timeout>=2.2.0`, `python-dotenv>=1.0.0`, `requests>=2.31.0`
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [x] 7.2 Create `tests/integration/test_task_lifecycle.py` with configuration and fixtures
    - Load env vars via `python-dotenv` from root `.env` file
    - Read `ADMIN_MNEMONIC` from env; skip all tests if not set with clear message
    - Read `ALGOD_SERVER` from env, default to `https://testnet-api.algonode.cloud`
    - Read `ESCROW_VAULT_APP_ID` from env, default to `761941677`
    - Create `AlgodClient` instance from configuration
    - Generate unique task ID per run using UUID
    - Derive test accounts (worker, sensei, client) from admin mnemonic
    - Set up pytest fixtures for shared state across lifecycle phases
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2_

  - [x] 7.3 Implement task creation and escrow lock test
    - Send HTTP POST to `{BACKEND_URL}/api/tasks` with JSON payload: `onChainTaskId`, `clientAddress`, `agentAddress`, `description`, `bountyUsdc`
    - Assert response status is 201, extract task ID from response body
    - If non-201, fail with assertion including status code and response body
    - Call `lock_bounty` ABI method on EscrowVault via `py-algorand-sdk`: supply task ID, client address, worker address, sensei address, bounty amount, and grouped payment transaction
    - Query `get_task` method and assert 137-byte box contents: client at 0–31, worker at 32–63, sensei at 64–95, bounty at 96–103, status byte at 104 equals 0 (LOCKED)
    - If `lock_bounty` reverts, fail with transaction error message
    - Apply 60-second timeout via `pytest.mark.timeout(60)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 7.4 Implement task submission with provenance hash test
    - Call `submit_task` ABI method with task ID and a valid 32-byte provenance hash, signed by worker account
    - Query `get_task` and assert status byte equals 1 (SUBMITTED)
    - Assert stored `kite_hash` (bytes 105–136) matches the submitted provenance hash
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 7.5 Implement payment release and distribution test
    - Record pre-release ALGO balances of sensei and treasury accounts
    - Call `release_payment` ABI method signed by client/admin, passing task ID and treasury address
    - Wait up to 10 seconds for confirmation
    - Query `get_task` and assert status byte equals 2 (COMPLETED)
    - Assert sensei balance increased by at least `bounty - ((bounty * 200) // 10000) - 5000` microAlgos
    - Assert treasury balance increased by `(bounty * 200) // 10000` microAlgos (±1000 tolerance)
    - If transaction fails or times out, fail with task ID and reason
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 8. Checkpoint - Verify integration test structure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Wire integration test into CI as conditional job
  - [x] 9.1 Add `integration-test` job to `.github/workflows/ci.yml`
    - Add new job `integration-test` on `ubuntu-latest`
    - Add condition: `if: ${{ secrets.ADMIN_MNEMONIC != '' }}`
    - Add step: checkout with `actions/checkout@v4`
    - Add step: setup Python 3.12 with `actions/setup-python@v5`
    - Add step: `pip install -r tests/integration/requirements.txt`
    - Add step: run `pytest tests/integration/ -v` with env vars: `ADMIN_MNEMONIC` from secrets, `ALGOD_SERVER`, `ESCROW_VAULT_APP_ID`
    - Job runs independently of `build-and-test` (no `needs` dependency)
    - _Requirements: 1.4, 7.6, 8.3_

- [x] 10. Final checkpoint - Ensure all files are consistent
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- No property-based tests are applicable to this feature (CI config, setup scripts, and integration tests against external services)
- The integration test uses `py-algorand-sdk` directly, NOT `algopy_testing`
- Each integration test run generates a unique UUID-based task ID to avoid collisions (Requirement 8.1)
- The CI badge requires the correct GitHub owner/repo — determined from `git remote get-url origin`
- The `integration-test` job is conditional on `ADMIN_MNEMONIC` secret availability so PRs from forks still pass
- Setup scripts use `Start-Process` for background processes on Windows (PowerShell)
- Tasks are ordered: CI workflow → Badge → Setup scripts → Makefile → Integration test → Wire into CI

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "4.1", "5.1", "7.1"] },
    { "id": 2, "tasks": ["4.2", "7.2"] },
    { "id": 3, "tasks": ["7.3"] },
    { "id": 4, "tasks": ["7.4"] },
    { "id": 5, "tasks": ["7.5"] },
    { "id": 6, "tasks": ["9.1"] }
  ]
}
```
