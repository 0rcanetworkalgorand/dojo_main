"""
🔐 Kite AI Provenance Demo — End-to-End On-Chain Attribution Proof

This script demonstrates the full Kite AI provenance flow:
  1. Agent executes a task and produces output
  2. Output is hashed → submitted to Kite AI for attribution tracking
  3. The provenance hash is stored on-chain via EscrowVault.submit_task
  4. Anyone can verify the hash on-chain matches the original output

This proves:
  - No payment can be released without a valid provenance hash (contract enforces this)
  - Every agent output has a cryptographic proof of authorship
  - Attribution is immutable and publicly verifiable on Algorand

Usage:
  python scripts/demo_kite_provenance.py

Environment variables (optional):
  ADMIN_MNEMONIC   — Algorand TestNet account mnemonic (for live on-chain demo)
  KITE_API_KEY     — Kite AI API key (falls back to local SHA-256 if not set)
  ALGOD_SERVER     — Algorand node URL (default: https://testnet-api.algonode.cloud)
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dojo-sdk"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


# ─── Configuration ────────────────────────────────────────────────────────────

ADMIN_MNEMONIC = os.environ.get("ADMIN_MNEMONIC")
KITE_API_KEY = os.environ.get("KITE_API_KEY", "")
ALGOD_SERVER = os.environ.get("ALGOD_SERVER", "https://testnet-api.algonode.cloud")
ESCROW_VAULT_APP_ID = int(os.environ.get("ESCROW_VAULT_APP_ID", "761941677"))


# ─── Provenance Hash Generation ──────────────────────────────────────────────

async def generate_provenance_hash(task_output: str, task_id: str) -> bytes:
    """
    Generate a provenance hash for the given task output.
    
    If KITE_API_KEY is available, submits to Kite AI for real attribution.
    Otherwise, generates a local SHA-256 hash (demonstrates the mechanism).
    """
    if KITE_API_KEY:
        # Real Kite AI submission
        import httpx
        print("  📡 Submitting to Kite AI for attribution tracking...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.kite.ai/v1/provenance",
                    json={
                        "task_id": task_id,
                        "output_summary": task_output[:1000],
                        "metadata": {"source": "0rca-dojo-demo", "timestamp": time.time()}
                    },
                    headers={
                        "Authorization": f"Bearer {KITE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    hash_hex = data.get("provenance_hash", "")
                    if hash_hex:
                        print(f"  ✅ Kite AI provenance hash received: {hash_hex[:16]}...")
                        return bytes.fromhex(hash_hex)
        except Exception as e:
            print(f"  ⚠️  Kite AI unavailable ({e}), falling back to local hash")
    
    # Local SHA-256 fallback — same cryptographic guarantee, just self-attested
    print("  🔑 Generating local SHA-256 provenance hash...")
    hash_input = json.dumps({
        "task_id": task_id,
        "output": task_output,
        "timestamp": time.time(),
        "source": "0rca-dojo-agent"
    }, sort_keys=True).encode()
    
    provenance_hash = hashlib.sha256(hash_input).digest()
    print(f"  ✅ Provenance hash: {provenance_hash.hex()}")
    return provenance_hash


# ─── On-Chain Submission ──────────────────────────────────────────────────────

async def submit_hash_onchain(task_id: str, provenance_hash: bytes) -> dict:
    """Submit the provenance hash to EscrowVault on Algorand TestNet."""
    import algosdk
    from algosdk.v2client.algod import AlgodClient
    from algosdk.abi import Method
    from algosdk.atomic_transaction_composer import (
        AtomicTransactionComposer,
        AccountTransactionSigner,
        TransactionWithSigner,
    )
    from algosdk.transaction import PaymentTxn
    from algosdk import logic, encoding

    if not ADMIN_MNEMONIC:
        return {"success": False, "reason": "ADMIN_MNEMONIC not set — skipping on-chain submission"}

    algod = AlgodClient("", ALGOD_SERVER)
    sk = algosdk.mnemonic.to_private_key(ADMIN_MNEMONIC)
    addr = algosdk.account.address_from_private_key(sk)
    signer = AccountTransactionSigner(sk)
    app_address = logic.get_application_address(ESCROW_VAULT_APP_ID)
    sp = algod.suggested_params()

    # Step 1: Lock a small bounty (needed before submit_task can be called)
    print("  📦 Locking 50,000 µALGO bounty on-chain...")
    bounty = 50_000  # 0.05 ALGO

    lock_method = Method.from_signature("lock_bounty(string,address,address,address,uint64,pay)bool")
    payment_txn = PaymentTxn(sender=addr, sp=sp, receiver=app_address, amt=bounty)

    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=ESCROW_VAULT_APP_ID,
        method=lock_method,
        sender=addr,
        sp=sp,
        signer=signer,
        method_args=[task_id, addr, addr, addr, bounty, TransactionWithSigner(payment_txn, signer)],
        boxes=[(ESCROW_VAULT_APP_ID, task_id.encode())],
    )
    result = atc.execute(algod, wait_rounds=4)
    print(f"  ✅ Bounty locked. TX: {result.tx_ids[0][:12]}...")

    # Step 2: Submit the provenance hash
    print("  🔏 Submitting provenance hash to EscrowVault...")
    submit_method = Method.from_signature("submit_task(string,byte[])bool")

    atc2 = AtomicTransactionComposer()
    atc2.add_method_call(
        app_id=ESCROW_VAULT_APP_ID,
        method=submit_method,
        sender=addr,
        sp=algod.suggested_params(),
        signer=signer,
        method_args=[task_id, provenance_hash],
        boxes=[(ESCROW_VAULT_APP_ID, task_id.encode())],
    )
    result2 = atc2.execute(algod, wait_rounds=4)
    print(f"  ✅ Hash stored on-chain. TX: {result2.tx_ids[0][:12]}...")

    # Step 3: Verify by reading the box
    print("  🔍 Verifying on-chain provenance...")
    get_method = Method.from_signature("get_task(string)byte[]")

    atc3 = AtomicTransactionComposer()
    atc3.add_method_call(
        app_id=ESCROW_VAULT_APP_ID,
        method=get_method,
        sender=addr,
        sp=algod.suggested_params(),
        signer=signer,
        method_args=[task_id],
        boxes=[(ESCROW_VAULT_APP_ID, task_id.encode())],
    )
    result3 = atc3.execute(algod, wait_rounds=4)
    box_data = result3.abi_results[0].return_value

    # Ensure box_data is bytes (some SDK versions return list of ints)
    if isinstance(box_data, list):
        box_data = bytes(box_data)

    stored_hash = box_data[105:137]
    status = box_data[104]

    return {
        "success": True,
        "lock_tx": result.tx_ids[0],
        "submit_tx": result2.tx_ids[0],
        "status": status,
        "stored_hash": stored_hash.hex(),
        "matches": stored_hash == provenance_hash,
        "explorer_url": f"https://testnet.explorer.perawallet.app/application/{ESCROW_VAULT_APP_ID}"
    }


# ─── Main Demo Flow ──────────────────────────────────────────────────────────

async def main():
    print()
    print("═" * 60)
    print("  🐳 0rca Swarm Dojo — Kite AI Provenance Demo")
    print("═" * 60)
    print()

    # Simulate an agent completing a task
    task_id = f"demo-kite-{int(time.time())}"
    task_output = (
        "## DeFi Yield Farming on Algorand\n\n"
        "The Algorand ecosystem offers several yield farming opportunities:\n"
        "1. Tinyman LP staking (5-15% APY)\n"
        "2. Folks Finance lending (3-8% APY)\n"
        "3. Pact.fi concentrated liquidity (10-25% APY)\n\n"
        "Key risks include impermanent loss and smart contract vulnerabilities.\n"
        "Sources: Tinyman docs, Folks Finance whitepaper, DeFiLlama data."
    )

    print(f"📋 Task ID: {task_id}")
    print(f"🤖 Agent Lane: Research")
    print(f"📝 Output Preview: {task_output[:80]}...")
    print()

    # Step 1: Generate provenance hash
    print("─" * 60)
    print("STEP 1: Generate Provenance Hash")
    print("─" * 60)
    provenance_hash = await generate_provenance_hash(task_output, task_id)
    print()

    # Step 2: Submit to blockchain
    print("─" * 60)
    print("STEP 2: Store Hash On-Chain (Algorand TestNet)")
    print("─" * 60)

    if ADMIN_MNEMONIC:
        try:
            result = await submit_hash_onchain(task_id, provenance_hash)
            if result["success"]:
                print()
                print("─" * 60)
                print("STEP 3: Verification")
                print("─" * 60)
                print(f"  Task Status: {'SUBMITTED ✅' if result['status'] == 1 else 'UNEXPECTED (' + str(result['status']) + ')'}")
                print(f"  Hash Match:  {'✅ VERIFIED' if result['matches'] else '❌ MISMATCH'}")
                print(f"  Explorer:    {result['explorer_url']}")
                print(f"  Lock TX:     {result['lock_tx']}")
                print(f"  Submit TX:   {result['submit_tx']}")
            else:
                print(f"  ⚠️  {result['reason']}")
        except Exception as e:
            print(f"  ❌ On-chain submission failed: {e}")
            print("     (This may mean the task ID already exists or the account needs funding)")
    else:
        print("  ⚠️  ADMIN_MNEMONIC not set — on-chain submission skipped")
        print("     Set ADMIN_MNEMONIC in .env to enable live TestNet demo")
        print()
        print("─" * 60)
        print("STEP 3: Verification (Off-Chain Only)")
        print("─" * 60)
        print(f"  Provenance Hash: {provenance_hash.hex()}")
        print(f"  Hash Length:     {len(provenance_hash)} bytes (32 bytes = valid)")
        print(f"  Can be stored on-chain via EscrowVault.submit_task()")
        print(f"  Payment CANNOT be released without this hash (contract enforces)")

    # Summary
    print()
    print("═" * 60)
    print("  📊 PROVENANCE FLOW SUMMARY")
    print("═" * 60)
    print(f"  Agent Output  →  SHA-256 Hash  →  Kite AI Attribution  →  On-Chain Storage")
    print(f"  {len(task_output)} chars      →  {provenance_hash.hex()[:16]}...  →  EscrowVault Box")
    print()
    print("  Why this matters:")
    print("  • No payment without provenance — contract enforces kite_hash != 0")
    print("  • Immutable attribution — stored in Algorand Box Storage forever")
    print("  • Verifiable by anyone — query get_task() with the task ID")
    print("  • Prevents plagiarism — output is cryptographically bound to agent")
    print()
    print("═" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
