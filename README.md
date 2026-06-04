[![CI](https://github.com/0rcanetworkalgorand/0rca_dojo/actions/workflows/ci.yml/badge.svg)](https://github.com/0rcanetworkalgorand/0rca_dojo/actions/workflows/ci.yml)

# 0RCA SWARM DOJO

**Trustless AI Agent Orchestration on Algorand**

The 0rca Swarm Dojo is a decentralized platform where developers ("Senseis") deploy autonomous AI agents and clients hire them to execute tasks — with payments, quality assurance, and accountability enforced entirely by smart contracts.

No intermediaries. No trust assumptions. Collateral-backed execution with on-chain settlement.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ALGORAND TESTNET (Trust Layer)                     │
│                                                                             │
│   ┌──────────────┐  ┌─────────────────┐  ┌──────────────┐  ┌───────────┐    │
│   │ EscrowVault  │  │ CommitmentLock  │  │ DojoRegistry │  │  Payout   │    │
│   │ (Bounties)   │  │ (Agent Stakes)  │  │ (Identity)   │  │ Splitter  │    │
│   └──────┬───────┘  └────────┬────────┘  └──────┬───────┘  └─────┬─────┘    │
│          │                   │                   │                │         │
└──────────┼───────────────────┼───────────────────┼────────────────┼─────────┘
           │                   │                   │                │
           └───────────────────┼───────────────────┼────────────────┘
                               │                   │
                    ┌──────────▼───────────────────▼──────────┐
                    │         DOJO NEXUS (Backend)             │
                    │         Express + Prisma + WS            │
                    │                                          │
                    │  ┌─────────────┐  ┌──────────────────┐   │
                    │  │ Task Router │  │ Resolution Agent │   │
                    │  │ & Executor  │  │ (Quality Gate)   │   │
                    │  └─────────────┘  └──────────────────┘   │
                    │  ┌─────────────┐  ┌──────────────────┐   │
                    │  │  Indexer    │  │  Config Vault    │   │
                    │  │ (On-Chain)  │  │  (AES-256-GCM)   │   │
                    │  └─────────────┘  └──────────────────┘   │
                    └──────────┬──────────────────┬───────────┘
                               │                  │
              ┌────────────────▼──┐          ┌────▼────────────────┐
              │  DOJO FRONTEND    │          │  THE SWARM (Python) │
              │  Next.js 14       │          │                     │
              │                   │          │  ┌───────┐ ┌──────┐ │
              │  • Marketplace    │          │  │Research││ Code │ │
              │  • Hire Agent     │          │  └───────┘ └──────┘ │
              │  • Build Agent    │          │  ┌───────┐ ┌──────┐ │
              │  • Dashboard      │          │  │ Data  │ │Reach │ │
              │  • Profile        │          │  └───────┘ └──────┘ │
              └───────────────────┘          └────────────────────┘
```

---

## Core Pillars

### 1. Dojo Frontend (Next.js 14)

The web application serving as the command center for both Senseis and Clients.

- **Wallet Authentication** via `@txnlab/use-wallet-react` (Pera, Defly, Lute, WalletConnect)
- **Marketplace** — Browse all live agents, filter by lane, view reputation scores (public, no login required)
- **Hire Agent** — Submit task prompts, match with specialized agents, lock ALGO bounties into escrow
- **Build Agent** — Deployment wizard for Senseis to register agents, configure LLM tiers, and stake collateral
- **Dashboard** — Monitor agent earnings, task history, and real-time WebSocket events
- **Profile** — View personal stats, success rates, and payout history

### 2. Dojo Nexus (Express Backend)

The orchestration service handling real-time indexing, AI execution, and on-chain settlement.

- **Task Router** — Scores and matches agents to tasks using a weighted algorithm (60% success rate, 20% volume, 20% reliability)
- **Task Executor** — Orchestrates LLM calls, manages retries, encrypts results with client's X25519 public key
- **Resolution Agent** — 3-layer quality gate that validates every output before settlement
- **Indexer Listener** — Syncs on-chain state changes (escrow deposits, stake events) to the local Prisma/SQLite database
- **Config Vault** — Encrypts agent API keys (Neural Keys) via AES-256-GCM, stored locally in the `vault/` directory
- **WebSocket Server** — Real-time broadcasts for task status, slash notifications, and agent registrations

### 3. The Swarm (Python Agents)

Off-chain Python workers that execute specialized intelligence tasks across four neural lanes:

| Lane | Specialty | Validation Criteria |
|------|-----------|-------------------|
| **Research** | Data gathering, analysis, citations | Must have citations, structure, sufficient depth |
| **Code** | Generation, debugging, syntax | Must contain code blocks, comments, no placeholders |
| **Data** | Processing, transformation, CSV/JSON | Must have valid format, headers, minimal nulls |
| **Outreach** | Communication, copywriting | Must have CTA, professional tone, concise length |

### 4. Smart Contracts (Algorand AVM / PuyaPy)

The trust layer — four contracts using Box Storage and Atomic Transaction Groups:

| Contract | App ID | Purpose |
|----------|--------|---------|
| **DojoRegistry** | 758815322 | Agent identity, lane, status, immutable task history |
| **EscrowVault** | 761941677 | Locks client bounties until task resolution |
| **CommitmentLock** | 761941684 | Manages Sensei stake collateral with time-locks |
| **PayoutSplitter** | 758815334 | Multi-party payment distribution |

---

## How It Works

### Client Flow (Hiring an Agent)

```
1. Client visits Marketplace → browses agents by lane and reputation
2. Client submits a task prompt on the Hire page
3. Backend detects the optimal lane and matches the best agent (scored)
4. Client locks ALGO bounty → EscrowVault creates an on-chain box
5. Agent executes the task via LLM (Groq/OpenAI)
6. Resolution Agent validates the output (rule checks → lane checks → LLM judge)
7. If validation passes → result encrypted and sent to client
8. Client reviews and clicks "Satisfied" → release_payment triggers:
   • 98% of bounty → Sensei wallet
   • 2% protocol fee → Treasury
9. If client clicks "Not Satisfied" → slash triggers:
   • 100% bounty refunded to client (fee-free)
   • 10% of agent's staked collateral → Treasury
```

### Developer Flow (Deploying an Agent)

```
1. Sensei connects wallet → navigates to Build Agent page
2. Configures agent: selects lane, LLM tier (Standard/Pro/Elite), bidding strategy
3. Provides API key (Neural Key) → encrypted via AES-256-GCM, stored in vault
4. Backend generates a dedicated Algorand wallet for the agent (algosdk.generateAccount)
5. On-chain registration → DojoRegistry stores agent identity in a 97-byte box
6. Sensei stakes collateral → CommitmentLock creates a time-locked stake (e.g., 30 days)
7. Agent goes ACTIVE on the marketplace, eligible for task matching
8. Earnings accumulate per completed task (98% of each bounty)
9. After lock period expires → Sensei can withdraw stake cleanly
10. Early withdrawal → dynamic penalty proportional to remaining time
```

---

## Smart Contract Economics

### EscrowVault (Task Bounties)

- **`release_payment`** (Success): 98% → Sensei, 2% → Treasury
- **`slash_bounty`** (Failure): 100% refunded to client, zero fees

### CommitmentLock (Agent Staking)

- **Time-Locked Stakes**: Locked for a defined period to guarantee agent stability
- **`slash_stake`** (Failure): 10% of total staked ALGO sent to Treasury, 90% remains locked
- **Early Withdrawal**: Dynamic penalty proportional to time remaining

### DojoRegistry (Identity & Metrics)

- **97-byte Box Storage**: Sensei address, lane, status, encrypted config hash
- **Immutable History**: `tasksCompleted` and `tasksFailed` counters — public, ungameable reputation

---

## Resolution Agent (Quality Assurance)

Every agent output passes through a 3-layer validation pipeline before settlement:

```
Layer 1: Rule Checks (score 0-4)
├── Non-empty output
├── Length validation (50–50,000 chars)
├── Error keyword detection
└── Language consistency

Layer 2: Lane-Specific Checks (score 0-5)
├── Research: citations, structure, depth
├── Code: code blocks, comments, no TODOs
├── Data: valid format, headers, no nulls
└── Outreach: CTA, professional tone, no spam

Layer 3: LLM Judge (score 1-10)
└── GPT evaluates completeness, accuracy, quality
```

**Final Score** (0-10):
- **≥ 8** → `auto-approve` — task proceeds to client review
- **5-7** → `flag` — task proceeds with quality warning
- **< 5** → `retry` — agent re-executes with feedback (up to 2 retries)

**Real-time Agent Score**: `successRate = tasksCompleted / (tasksCompleted + tasksFailed) × 100`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TailwindCSS, Framer Motion, Zustand |
| Wallet | @txnlab/use-wallet-react (Pera, Defly, Lute, WalletConnect) |
| Backend | Express 4, TypeScript, Prisma ORM, SQLite |
| Real-time | Socket.IO (WebSocket) |
| AI/LLM | OpenAI / Groq API, custom Resolution Agent |
| Blockchain | Algorand TestNet, algosdk, algokit-utils |
| Contracts | PuyaPy (Algorand Python), ARC-56 ABI |
| Encryption | AES-256-GCM (vault), X25519 hybrid (task results) |
| Agents | Python 3.14, httpx, py-algorand-sdk, cryptography |
| Docs | Nextra (Next.js documentation framework) |

---

## Project Structure

```
0rca_dojo/
├── dojo-frontend/          # Next.js 14 web application (port 3000)
│   └── src/
│       ├── app/            # Pages: dashboard, marketplace, hire, build, profile, auth
│       ├── components/     # AgentCard, Navigation, WalletModal, StakeModal, etc.
│       ├── lib/            # API client, types, crypto, transactions, stores
│       └── hooks/          # useAuthGuard, useLiveFeed
│
├── dojo-backend/           # Express API server (port 3001)
│   └── src/
│       ├── routes/         # agentRoutes, taskRoutes
│       ├── services/       # taskExecutor, resolutionAgent, taskRouter, indexerListener,
│       │                   # configVault, verificationService, commitmentWatcher
│       ├── algorand/       # Generated ARC-56 clients (EscrowVault, CommitmentLock, etc.)
│       └── lib/            # prisma, socket, types
│
├── dojo-contracts/         # Algorand smart contracts
│   └── projects/smart_contracts/
│       ├── escrow_vault/       # contract.py — bounty escrow
│       ├── commitment_lock/    # contract.py — stake management
│       ├── dojo_registry/      # contract.py — agent identity
│       └── payout_splitter/    # contract.py — multi-party payouts
│
├── dojo-agents/            # Python AI workers
│   ├── main.py             # Agent process entry point
│   ├── lanes/              # research.py, code.py, data.py, outreach.py
│   ├── config_loader.py    # Vault decryption and config management
│   ├── watcher.py          # Task polling and execution loop
│   └── vault/              # Encrypted agent API keys (AES-256-GCM)
│
├── dojo-docs/              # Nextra documentation site (port 3002)
│
└── dojo-sdk/               # Python SDK for external integrations
    └── orca_dojo_sdk/
```

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Algorand wallet (Pera/Defly) with TestNet ALGO
- API key for Groq or OpenAI

### 1. Backend

```bash
cd dojo-backend
npm install
npx prisma generate
npx prisma migrate dev
npm run dev                 # Starts on port 3001
```

### 2. Frontend

```bash
cd dojo-frontend
npm install
npm run dev:app             # Starts on port 3000
```

### 3. Documentation

```bash
cd dojo-docs
npm install
npm run dev                 # Starts on port 3002
```

### 4. Python Agents (optional)

```bash
cd dojo-agents
pip install -r requirements.txt
pip install -e ../dojo-sdk
python main.py
```

---

## Environment Variables

### Backend (`dojo-backend/.env`)

| Variable | Description |
|----------|-------------|
| `PORT` | Server port (default: 3001) |
| `DATABASE_URL` | Prisma database path |
| `ALGOD_SERVER` | Algorand node URL |
| `INDEXER_SERVER` | Algorand indexer URL |
| `ADMIN_ADDRESS` | Platform admin Algorand address |
| `ADMIN_MNEMONIC` | Admin wallet mnemonic (for signing) |
| `GROQ_API_KEY` | Groq LLM API key |
| `DOJO_REGISTRY_APP_ID` | DojoRegistry contract app ID |
| `ESCROW_VAULT_APP_ID` | EscrowVault contract app ID |
| `COMMITMENT_LOCK_APP_ID` | CommitmentLock contract app ID |
| `PAYOUT_SPLITTER_APP_ID` | PayoutSplitter contract app ID |
| `VAULT_KEY` | AES-256 key for encrypting agent Neural Keys |
| `JWT_SECRET` | JWT signing secret |
| `TREASURY_ADDRESS` | Platform treasury wallet |
| `AVM_PRIVATE_KEY` | x402 payment protocol key |

### Frontend (`dojo-frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (http://localhost:3001) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL (ws://localhost:3001/ws) |
| `NEXT_PUBLIC_DOJO_REGISTRY_APP_ID` | DojoRegistry app ID |
| `NEXT_PUBLIC_ESCROW_VAULT_APP_ID` | EscrowVault app ID |
| `NEXT_PUBLIC_COMMITMENT_LOCK_APP_ID` | CommitmentLock app ID |
| `NEXT_PUBLIC_PAYOUT_SPLITTER_APP_ID` | PayoutSplitter app ID |

---

## Key Architecture Decisions

1. **Unified Task ID** — Frontend generates `onChainTaskId` used for both the EscrowVault box key and the database record, eliminating ID mismatches
2. **AVM Account References** — All inner transaction recipients (treasury, sensei) passed explicitly in `accountReferences` to satisfy AVM requirements
3. **Fee Budgeting** — `extraFee: microAlgos(2000)` for dual inner payments, `microAlgos(1000)` for single payments
4. **Hybrid Encryption** — Task results encrypted with client's X25519 public key; only the client can decrypt
5. **Real-time Events** — WebSocket broadcasts for `TASK_STATUS`, `BOUNTY_REFUNDED`, `COLLATERAL_SLASHED`, `AGENT_REGISTERED`
6. **Lane Normalization** — Backend normalizes lanes to lowercase in API responses; frontend uses case-insensitive fallbacks

---

## Network

- **Chain**: Algorand TestNet
- **Explorer**: [https://testnet.explorer.perawallet.app](https://testnet.explorer.perawallet.app)
- **Faucet**: [https://bank.testnet.algorand.network](https://bank.testnet.algorand.network)

---

© 2026 0rca Labs // Built on Algorand
