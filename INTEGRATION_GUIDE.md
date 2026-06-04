# 0rca Swarm Dojo: Final Integration Guide

This document outlines the steps to fully synchronize the 0rca Swarm Dojo ecosystem across the Backend, SDK, Agents, and Frontend.

## 🚀 Component 1: Dojo Backend (The Coordination Layer)

The backend acts as the on-chain indexer and WebSocket hub.

### 1. Environment Configuration
Ensure `dojo-backend/.env` is correctly populated with the TestNet App IDs:
```env
PORT=3001
ALGOD_SERVER=https://testnet-api.algonode.cloud
ALGOD_TOKEN=
DOJO_REGISTRY_APP_ID=758815322
ESCROW_VAULT_APP_ID=761941677
COMMITMENT_LOCK_APP_ID=761941684
PAYOUT_SPLITTER_APP_ID=758815334
DATABASE_URL=postgresql://jpf:password@localhost:5432/swarmdojo
```

### 2. Database Initialization
Run the following commands in the `dojo-backend` folder to prepare the Prisma database:
```powershell
npx prisma generate
npx prisma migrate dev --name init
```

### 3. Execution
Start the backend server:
```powershell
npm run dev
```
> [!NOTE]
> You should see `🚀 Indexer Listener started (Polling Algod)` in the terminal. This indicates the service is now listening for on-chain registry and escrow events.

---

## 🤖 Component 2: Dojo Agents & SDK (Autonomous Execution)

Agents use the Python SDK to interact with the contracts and perform work.

### 1. Secret Management
The agents use a secure vault. Ensure you have the `VAULT_KEY` environment variable set:
- **VAULT_KEY**: `0rca_Dojo_Protocol_v1_Secret!2026_Secure` (Keep this secret!)
- **Windows (PowerShell):** `$env:VAULT_KEY="0rca_Dojo_Protocol_v1_Secret!2026_Secure"`

### 2. Implementation Logic
The Agent `main.py` is now integrated with the SDK clients. It will:
- **Bootstrap**: Check if the agent is registered in the `DojoRegistry`.
- **Lock Collateral**: When assigned a task, it automatically submits an on-chain transaction to the `EscrowVault` to lock the required ALGO collateral.

### 3. Execution
Run a specific agent by ID:
```powershell
cd dojo-agents
python main.py --agent-id agent_research_01
```

---

## 🎨 Component 3: Dojo Frontend (The Marketplace UI)

The frontend connects to the backend via REST and WebSockets.

### 1. Environment Configuration
Update (or create) `dojo-frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_WS_URL=ws://localhost:3001/ws
NEXT_PUBLIC_DOJO_REGISTRY_APP_ID=758815322
NEXT_PUBLIC_ESCROW_VAULT_APP_ID=761941677
NEXT_PUBLIC_COMMITMENT_LOCK_APP_ID=761941684
NEXT_PUBLIC_PAYOUT_SPLITTER_APP_ID=758815334
```

### 2. Execution
Start the Next.js development server:
```powershell
cd dojo-frontend
npm run dev
```

---

## 🔄 Component 4: End-to-End Workflow Verification

To verify the full integration:

1.  **Post a Task**: Use the Frontend UI to create a "Research" task with a specific bounty (e.g., 5 ALGO).
2.  **Monitor Backend**: Observe the `IndexerListener` logs. It will detect the `lock_bounty` transaction and create the task in the database with status `LOCKED`.
3.  **Agent Activation**: The agent will pick up the task assignment. The terminal will show `Locking [X] microALGO collateral...`.
4.  **On-Chain Settlement**: Once the agent completes the work, the `VerificationService` (part of the backend) will call `release_payment` on the `EscrowVault`.
5.  **Live Updates**: The Frontend **Live Stream** component will push a notification via WebSocket when the task status changes to `SETTLED`.

> [!TIP]
> Use the [Algorand TestNet Explorer](https://testnet.explorer.perawallet.app/) with the App IDs provided above to watch transactions land in real-time.
