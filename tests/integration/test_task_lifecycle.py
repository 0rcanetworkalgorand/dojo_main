"""
Integration test: Full EscrowVault task lifecycle on Algorand TestNet.

This module exercises the complete flow:
  1. Task creation via Backend API + escrow lock on-chain
  2. Task submission with provenance hash
  3. Payment release and fund distribution verification

Configuration is loaded from environment variables (with .env fallback).
All tests are skipped if ADMIN_MNEMONIC is not set.
"""

import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

import algosdk
from algosdk.v2client.algod import AlgodClient

# ---------------------------------------------------------------------------
# Configuration: load .env from repository root
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")

ADMIN_MNEMONIC = os.environ.get("ADMIN_MNEMONIC")
ALGOD_SERVER = os.environ.get("ALGOD_SERVER", "https://testnet-api.algonode.cloud")
ESCROW_VAULT_APP_ID = int(os.environ.get("ESCROW_VAULT_APP_ID", "761941677"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:3001")

# ---------------------------------------------------------------------------
# Module-level skip: if ADMIN_MNEMONIC is not available, skip all tests
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    ADMIN_MNEMONIC is None,
    reason=(
        "ADMIN_MNEMONIC environment variable is not set. "
        "Integration tests require a funded Algorand TestNet account. "
        "Set ADMIN_MNEMONIC in your .env file or as an environment variable."
    ),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def algod_client() -> AlgodClient:
    """Create an AlgodClient connected to the configured Algorand node."""
    return AlgodClient("", ALGOD_SERVER)


@pytest.fixture(scope="module")
def admin_account() -> dict:
    """Derive admin account (private key + address) from ADMIN_MNEMONIC."""
    assert ADMIN_MNEMONIC is not None
    sk = algosdk.mnemonic.to_private_key(ADMIN_MNEMONIC)
    addr = algosdk.account.address_from_private_key(sk)
    return {"sk": sk, "address": addr}


@pytest.fixture(scope="module")
def worker_account(admin_account: dict) -> dict:
    """
    Worker account for testing.

    For simplicity on TestNet, we reuse the admin account as the worker.
    This avoids needing to fund separate accounts for each test run.
    """
    return {"sk": admin_account["sk"], "address": admin_account["address"]}


@pytest.fixture(scope="module")
def sensei_account(admin_account: dict) -> dict:
    """
    Sensei account for testing.

    For simplicity on TestNet, we reuse the admin account as the sensei.
    """
    return {"sk": admin_account["sk"], "address": admin_account["address"]}


@pytest.fixture(scope="module")
def client_account(admin_account: dict) -> dict:
    """
    Client account for testing.

    For simplicity on TestNet, we reuse the admin account as the client.
    """
    return {"sk": admin_account["sk"], "address": admin_account["address"]}


@pytest.fixture(scope="module")
def task_id() -> str:
    """Generate a unique task ID for this test run to avoid collisions."""
    return f"test-{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="module")
def app_id() -> int:
    """Return the EscrowVault application ID."""
    return ESCROW_VAULT_APP_ID


@pytest.fixture(scope="module")
def backend_url() -> str:
    """Return the backend API base URL."""
    return BACKEND_URL


@pytest.fixture(scope="module")
def shared_state() -> dict:
    """
    Mutable shared state passed between ordered lifecycle test phases.

    This allows sequential tests to share data (e.g., the task ID returned
    by the backend, transaction IDs, balances) without relying on class-level
    state or global variables.
    """
    return {}


# ---------------------------------------------------------------------------
# Test class: Task Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.timeout(60)
class TestTaskLifecycle:
    """
    End-to-end task lifecycle tests against Algorand TestNet.

    Tests are ordered sequentially:
      1. Create task + lock bounty
      2. Submit task with provenance hash
      3. Release payment and verify distribution
    """

    def test_create_task_and_lock_bounty(
        self,
        algod_client: AlgodClient,
        admin_account: dict,
        worker_account: dict,
        sensei_account: dict,
        client_account: dict,
        task_id: str,
        app_id: int,
        backend_url: str,
        shared_state: dict,
    ):
        """Req 4: POST task → lock_bounty → verify box status=LOCKED."""
        import struct

        import requests
        from algosdk import logic
        from algosdk.abi import Method
        from algosdk.atomic_transaction_composer import (
            AccountTransactionSigner,
            AtomicTransactionComposer,
            TransactionWithSigner,
        )
        from algosdk.transaction import PaymentTxn

        # Store task_id in shared state for downstream tests
        shared_state["task_id"] = task_id

        bounty_amount = 100_000  # 0.1 ALGO in microAlgos

        # --- Step 1: Optional backend POST ---
        # Try to create the task via the backend API; if the backend isn't
        # running, proceed with just the on-chain lock (the critical assertion).
        backend_task_created = False
        try:
            resp = requests.post(
                f"{backend_url}/api/tasks",
                json={
                    "onChainTaskId": task_id,
                    "clientAddress": client_account["address"],
                    "agentAddress": worker_account["address"],
                    "description": f"Integration test task {task_id}",
                    "bountyUsdc": bounty_amount,
                },
                timeout=10,
            )
            if resp.status_code == 201:
                backend_task_created = True
                body = resp.json()
                shared_state["backend_task_id"] = body.get("id") or body.get("taskId")
            else:
                # Non-201 from a running backend is a real failure
                assert resp.status_code == 201, (
                    f"Backend returned {resp.status_code}: {resp.text}"
                )
        except requests.exceptions.ConnectionError:
            # Backend not running — acceptable, proceed with on-chain test
            pass

        shared_state["backend_task_created"] = backend_task_created

        # --- Step 2: Call lock_bounty on EscrowVault ---
        app_address = logic.get_application_address(app_id)
        sp = algod_client.suggested_params()

        # Define the ABI method for lock_bounty
        lock_bounty_method = Method.from_signature(
            "lock_bounty(string,address,address,address,uint64,pay)bool"
        )

        # Build the payment transaction for the bounty
        payment_txn = PaymentTxn(
            sender=client_account["address"],
            sp=sp,
            receiver=app_address,
            amt=bounty_amount,
        )

        signer = AccountTransactionSigner(admin_account["sk"])

        # Compose the atomic transaction group
        atc = AtomicTransactionComposer()
        atc.add_method_call(
            app_id=app_id,
            method=lock_bounty_method,
            sender=client_account["address"],
            sp=sp,
            signer=signer,
            method_args=[
                task_id,
                client_account["address"],
                worker_account["address"],
                sensei_account["address"],
                bounty_amount,
                TransactionWithSigner(payment_txn, signer),
            ],
            boxes=[(app_id, task_id.encode())],
        )

        # Execute the transaction group
        try:
            result = atc.execute(algod_client, wait_rounds=4)
            shared_state["lock_tx_id"] = result.tx_ids[0]
        except Exception as e:
            pytest.fail(f"lock_bounty reverted: {e}")

        # --- Step 3: Query get_task and verify box contents ---
        get_task_method = Method.from_signature("get_task(string)byte[]")

        atc_query = AtomicTransactionComposer()
        atc_query.add_method_call(
            app_id=app_id,
            method=get_task_method,
            sender=admin_account["address"],
            sp=algod_client.suggested_params(),
            signer=signer,
            method_args=[task_id],
            boxes=[(app_id, task_id.encode())],
        )

        query_result = atc_query.execute(algod_client, wait_rounds=4)
        box_data: bytes = query_result.abi_results[0].return_value

        # Ensure box_data is bytes (some SDK versions return list of ints)
        if isinstance(box_data, list):
            box_data = bytes(box_data)

        # Verify box is 137 bytes
        assert len(box_data) == 137, (
            f"Expected 137-byte box, got {len(box_data)} bytes"
        )

        # Parse and verify box contents
        # Client address at bytes 0-31
        from algosdk import encoding

        stored_client = encoding.encode_address(box_data[0:32])
        assert stored_client == client_account["address"], (
            f"Client mismatch: {stored_client} != {client_account['address']}"
        )

        # Worker address at bytes 32-63
        stored_worker = encoding.encode_address(box_data[32:64])
        assert stored_worker == worker_account["address"], (
            f"Worker mismatch: {stored_worker} != {worker_account['address']}"
        )

        # Sensei address at bytes 64-95
        stored_sensei = encoding.encode_address(box_data[64:96])
        assert stored_sensei == sensei_account["address"], (
            f"Sensei mismatch: {stored_sensei} != {sensei_account['address']}"
        )

        # Bounty amount at bytes 96-103 (big-endian uint64)
        stored_bounty = struct.unpack(">Q", box_data[96:104])[0]
        assert stored_bounty == bounty_amount, (
            f"Bounty mismatch: {stored_bounty} != {bounty_amount}"
        )

        # Status byte at offset 104 equals 0 (LOCKED)
        status_byte = box_data[104]
        assert status_byte == 0, (
            f"Expected status LOCKED (0), got {status_byte}"
        )

    def test_submit_task_with_provenance(
        self,
        algod_client: AlgodClient,
        worker_account: dict,
        task_id: str,
        app_id: int,
        shared_state: dict,
    ):
        """Req 5: submit_task → verify status=SUBMITTED, kite_hash stored."""
        import hashlib

        from algosdk.abi import Method
        from algosdk.atomic_transaction_composer import (
            AccountTransactionSigner,
            AtomicTransactionComposer,
        )

        # Generate a deterministic 32-byte provenance hash
        provenance_hash = hashlib.sha256(b"test-provenance").digest()
        assert len(provenance_hash) == 32

        # Store in shared state for downstream tests
        shared_state["provenance_hash"] = provenance_hash

        # --- Step 1: Call submit_task signed by the worker ---
        submit_method = Method.from_signature("submit_task(string,byte[])bool")

        signer = AccountTransactionSigner(worker_account["sk"])
        sp = algod_client.suggested_params()

        atc = AtomicTransactionComposer()
        atc.add_method_call(
            app_id=app_id,
            method=submit_method,
            sender=worker_account["address"],
            sp=sp,
            signer=signer,
            method_args=[task_id, provenance_hash],
            boxes=[(app_id, task_id.encode())],
        )

        try:
            result = atc.execute(algod_client, wait_rounds=4)
            shared_state["submit_tx_id"] = result.tx_ids[0]
        except Exception as e:
            pytest.fail(f"submit_task reverted: {e}")

        # --- Step 2: Query get_task and verify status + kite_hash ---
        get_task_method = Method.from_signature("get_task(string)byte[]")

        atc_query = AtomicTransactionComposer()
        atc_query.add_method_call(
            app_id=app_id,
            method=get_task_method,
            sender=worker_account["address"],
            sp=algod_client.suggested_params(),
            signer=signer,
            method_args=[task_id],
            boxes=[(app_id, task_id.encode())],
        )

        query_result = atc_query.execute(algod_client, wait_rounds=4)
        box_data: bytes = query_result.abi_results[0].return_value

        # Ensure box_data is bytes (some SDK versions return list of ints)
        if isinstance(box_data, list):
            box_data = bytes(box_data)

        # Verify status byte at offset 104 == 1 (SUBMITTED)
        status_byte = box_data[104]
        assert status_byte == 1, (
            f"Expected status SUBMITTED (1), got {status_byte}"
        )

        # Verify kite_hash at bytes 105:137 matches submitted provenance hash
        stored_hash = bytes(box_data[105:137]) if isinstance(box_data[105:137], list) else box_data[105:137]
        assert stored_hash == provenance_hash, (
            f"Provenance hash mismatch:\n"
            f"  stored:    {stored_hash.hex()}\n"
            f"  submitted: {provenance_hash.hex()}"
        )

    def test_release_payment_and_verify_distribution(
        self,
        algod_client: AlgodClient,
        admin_account: dict,
        sensei_account: dict,
        client_account: dict,
        task_id: str,
        app_id: int,
        shared_state: dict,
    ):
        """Req 6: release_payment → verify status=COMPLETED, balances correct."""
        from algosdk.abi import Method
        from algosdk.atomic_transaction_composer import (
            AccountTransactionSigner,
            AtomicTransactionComposer,
        )

        bounty_amount = 100_000  # microAlgos
        expected_fee = (bounty_amount * 200) // 10000  # 2% = 2,000 microAlgos
        expected_sensei_payment = bounty_amount - expected_fee  # 98,000 microAlgos

        # Use a separate treasury address so we can verify it receives the 2% fee.
        # Generate a random account to serve as treasury.
        treasury_sk, treasury_address = algosdk.account.generate_account()

        # Fund the treasury account with minimum balance so it can receive payments.
        # The treasury needs to exist on-chain to receive inner transactions.
        from algosdk.transaction import PaymentTxn, wait_for_confirmation

        sp = algod_client.suggested_params()
        fund_txn = PaymentTxn(
            sender=admin_account["address"],
            sp=sp,
            receiver=treasury_address,
            amt=200_000,  # 0.2 ALGO to cover minimum balance
        )
        signed_fund = fund_txn.sign(admin_account["sk"])
        try:
            fund_tx_id = algod_client.send_transaction(signed_fund)
            wait_for_confirmation(algod_client, fund_tx_id, wait_rounds=4)
        except Exception as e:
            pytest.fail(f"Failed to fund treasury account: {e}")

        # --- Step 1: Record pre-release ALGO balances ---
        pre_sensei_balance = algod_client.account_info(sensei_account["address"])["amount"]
        pre_treasury_balance = algod_client.account_info(treasury_address)["amount"]

        # --- Step 2: Call release_payment ABI method ---
        release_method = Method.from_signature("release_payment(string,address)bool")
        signer = AccountTransactionSigner(admin_account["sk"])
        sp = algod_client.suggested_params()
        sp.fee = 3000  # Extra fee budget for 2 inner payments
        sp.flat_fee = True

        atc = AtomicTransactionComposer()
        atc.add_method_call(
            app_id=app_id,
            method=release_method,
            sender=admin_account["address"],
            sp=sp,
            signer=signer,
            method_args=[task_id, treasury_address],
            boxes=[(app_id, task_id.encode())],
            accounts=[sensei_account["address"], treasury_address],
        )

        # --- Step 3: Execute and wait up to 10 seconds for confirmation ---
        try:
            result = atc.execute(algod_client, wait_rounds=10)
            shared_state["release_tx_id"] = result.tx_ids[0]
        except Exception as e:
            pytest.fail(
                f"release_payment failed for task '{task_id}': {e}"
            )

        # --- Step 4: Query get_task and assert status byte equals 2 (COMPLETED) ---
        from algosdk.abi import Method as AbiMethod

        get_task_method = AbiMethod.from_signature("get_task(string)byte[]")

        atc_query = AtomicTransactionComposer()
        atc_query.add_method_call(
            app_id=app_id,
            method=get_task_method,
            sender=admin_account["address"],
            sp=algod_client.suggested_params(),
            signer=signer,
            method_args=[task_id],
            boxes=[(app_id, task_id.encode())],
        )

        query_result = atc_query.execute(algod_client, wait_rounds=4)
        box_data: bytes = query_result.abi_results[0].return_value

        # Ensure box_data is bytes (some SDK versions return list of ints)
        if isinstance(box_data, list):
            box_data = bytes(box_data)

        status_byte = box_data[104]
        assert status_byte == 2, (
            f"Expected status COMPLETED (2), got {status_byte}"
        )

        # --- Step 5: Assert sensei balance increased correctly ---
        # Since admin == sensei, the admin paid the transaction fee but received
        # the sensei payment (98,000 microAlgos). Net effect:
        #   post_balance = pre_balance - tx_fees + sensei_payment
        # We assert: sensei balance increased by at least
        #   sensei_payment - 5000 (tolerance for up to 5 inner txn fees)
        post_sensei_balance = algod_client.account_info(sensei_account["address"])["amount"]
        sensei_balance_change = post_sensei_balance - pre_sensei_balance

        # The admin/sensei account pays the outer transaction fee (~1000-2000 microAlgos)
        # but receives 98,000 microAlgos from the inner payment.
        # Minimum expected increase: sensei_payment - 5000 (fee tolerance)
        min_expected_sensei_increase = expected_sensei_payment - 5000
        assert sensei_balance_change >= min_expected_sensei_increase, (
            f"Sensei balance change {sensei_balance_change} µAlgo is less than "
            f"minimum expected {min_expected_sensei_increase} µAlgo "
            f"(sensei_payment={expected_sensei_payment}, tolerance=5000)"
        )

        # --- Step 6: Assert treasury balance increased by the 2% fee (±1000 tolerance) ---
        post_treasury_balance = algod_client.account_info(treasury_address)["amount"]
        treasury_balance_change = post_treasury_balance - pre_treasury_balance

        assert abs(treasury_balance_change - expected_fee) <= 1000, (
            f"Treasury balance change {treasury_balance_change} µAlgo does not match "
            f"expected fee {expected_fee} µAlgo (±1000 tolerance)"
        )
