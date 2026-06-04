# 0RCA SWARM DOJO — Implementation Roadmap

## Five New Capabilities

This document details the full implementation strategy for five new platform capabilities being added to the 0rca Swarm Dojo. Each section explains what we're building, why, exactly which files are created or modified, the data structures involved, and how we migrate from the current system without breaking existing functionality.

---

## Implementation Order & Dependencies

```
┌─────────────────────────────┐
│  1. Structured Input Schema │  ← Pure backend/frontend, no contract changes
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  2. Formal Dispute Windows  │  ← New EscrowVaultV2 contract
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  3. NFT/Portable Identity   │  ← New ASA minting + DojoRegistry V2
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  4. DIDs & Verifiable Creds │  ← Layers on top of NFT identity
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  5. MCP Server Integration  │  ← Exposes all capabilities externally
└─────────────────────────────┘
```

Each phase builds on the previous. Input Schema is foundational (no contract work). Dispute Windows require a new escrow contract. NFT Identity requires new ASA logic. DIDs attach to NFTs. MCP exposes everything to external AI agents.

---

## Phase 1: Structured Input Schema

### What It Is

Currently, clients submit tasks as free-form text prompts. This phase introduces a formal schema system where each agent publishes a structured definition of what inputs it accepts — field types, validation rules, required/optional flags, and options. Clients fill out a dynamic form instead of typing a raw string.

### Why It Matters

- Eliminates ambiguous task submissions that waste agent compute
- Enables client-side validation before bounty is locked
- Creates an integrity hash of inputs for on-chain provenance
- Required foundation for MCP integration (Phase 5) where external agents need to know what inputs to provide

### Files Created

```
dojo-backend/src/services/schemaService.ts        — Schema validation engine
dojo-frontend/src/components/DynamicTaskForm.tsx   — Dynamic form renderer
```

### Files Modified

```
dojo-backend/src/routes/agentRoutes.ts    — New endpoints for schema CRUD
dojo-backend/src/routes/taskRoutes.ts     — Input validation before task creation
dojo-backend/src/services/taskExecutor.ts — Pass structured data to agents
dojo-backend/prisma/schema.prisma         — New fields on Agent and Task models
dojo-frontend/src/app/hire/page.tsx       — Replace textarea with DynamicTaskForm
dojo-agents/lanes/research.py             — Define default research schema
dojo-agents/lanes/code.py                 — Define default code schema
dojo-agents/lanes/data.py                 — Define default data schema
dojo-agents/lanes/outreach.py             — Define default outreach schema
```

### Data Structures

#### Agent Input Schema (stored as JSON in database)

```typescript
interface InputField {
  id: string;              // Unique field key (e.g., "topic", "language")
  type: 'string' | 'number' | 'boolean' | 'option' | 'file';
  name: string;            // Display label shown to client
  required: boolean;
  data?: {
    placeholder?: string;  // Hint text in the form field
    description?: string;  // Help text below the field
    values?: string[];     // Dropdown options (for 'option' type)
    maxLength?: number;    // Character limit (for 'string' type)
    min?: number;          // Minimum value (for 'number' type)
    max?: number;          // Maximum value (for 'number' type)
  };
  validations?: Array<{
    validation: 'min' | 'max' | 'format' | 'pattern' | 'required';
    value: string;
  }>;
}

interface AgentInputSchema {
  version: number;         // Schema version for backward compatibility
  fields: InputField[];    // Ordered list of input fields
}
```

#### Example: Research Lane Default Schema

```json
{
  "version": 1,
  "fields": [
    {
      "id": "topic",
      "type": "string",
      "name": "Research Topic",
      "required": true,
      "data": {
        "placeholder": "e.g., DeFi yield farming strategies on Algorand",
        "description": "The main subject you want researched",
        "maxLength": 500
      }
    },
    {
      "id": "depth",
      "type": "option",
      "name": "Research Depth",
      "required": true,
      "data": {
        "values": ["Brief (1-2 paragraphs)", "Standard (full report)", "Deep Dive (comprehensive analysis)"]
      }
    },
    {
      "id": "format",
      "type": "option",
      "name": "Output Format",
      "required": false,
      "data": {
        "values": ["Markdown", "Plain Text", "Bullet Points", "Executive Summary"]
      }
    },
    {
      "id": "sources_required",
      "type": "boolean",
      "name": "Require Citations",
      "required": false,
      "data": {
        "description": "Agent must include source URLs for all claims"
      }
    }
  ]
}
```

### Database Changes (Prisma)

```prisma
model Agent {
  // ... existing fields ...
  inputSchema    Json?       // The agent's published input schema
  schemaVersion  Int         @default(0)
}

model Task {
  // ... existing fields ...
  inputData      Json?       // Structured input submitted by client
  inputHash      String?     // SHA-256 of canonical JSON input
}
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents/:id/input-schema` | Returns the agent's published schema |
| PUT | `/agents/:id/input-schema` | Sensei updates their agent's schema |
| POST | `/tasks/create` | Modified — validates inputData against schema before creating task |

### Validation Flow

```
Client fills DynamicTaskForm
        │
        ▼
Frontend validates locally (required fields, types, patterns)
        │
        ▼
POST /tasks/create { agentId, inputData }
        │
        ▼
Backend: schemaService.validateInput(agent.inputSchema, inputData)
        │
        ├── PASS → compute inputHash = SHA-256(canonicalJSON(inputData))
        │          → create task record with inputData + inputHash
        │          → proceed to bounty lock
        │
        └── FAIL → return 400 { errors: [{ field: "topic", message: "Required" }] }
```

### Input Hash Computation

The `inputHash` provides integrity verification — proof that the input hasn't been tampered with after submission:

```typescript
import { createHash } from 'crypto';

function computeInputHash(inputData: Record<string, any>): string {
  // Canonical JSON: keys sorted lexicographically, no whitespace
  const canonical = JSON.stringify(inputData, Object.keys(inputData).sort());
  return createHash('sha256').update(canonical).digest('hex');
}
```

### Migration Strategy

- No contract changes required — this is purely backend/frontend/database
- Add `inputSchema` column as nullable — existing agents have no schema (backward compatible)
- Existing agents continue to accept free-text prompts (schema is optional)
- New agents registered via Build page must define a schema
- Run a migration script that generates default schemas for existing agents based on their lane

---

## Phase 2: Formal Dispute Time Windows

### What It Is

Currently, task resolution is binary: client clicks "Satisfied" (release payment) or "Not Satisfied" (slash). There's no time-based structure. This phase introduces a multi-phase escrow lifecycle with explicit deadlines:

```
LOCKED → SUBMITTED → REVIEW WINDOW → DISPUTE WINDOW → SETTLED
```

If the client does nothing within the dispute window, payment auto-releases to the Sensei. If the client raises a dispute, an admin resolves it.

### Why It Matters

- Protects Senseis from clients who never respond (funds locked forever)
- Gives clients a formal window to review and dispute
- Creates an auditable timeline for every task
- Enables future automated dispute resolution (AI arbitrator)
- Aligns with how Masumi handles escrow deadlines

### Files Created

```
dojo-contracts/projects/smart_contracts/escrow_vault_v2/contract.py  — New escrow contract
dojo-contracts/projects/smart_contracts/escrow_vault_v2/__init__.py
dojo-backend/src/services/disputeService.ts    — Dispute logic and deadline calculations
dojo-backend/src/services/autoSettler.ts       — Cron job for auto-settlement
dojo-frontend/src/components/DisputePanel.tsx  — Dispute UI component
dojo-frontend/src/components/CountdownTimer.tsx — Deadline countdown display
```

### Files Modified

```
dojo-backend/src/routes/taskRoutes.ts          — New dispute/accept/resolve endpoints
dojo-backend/src/services/indexerListener.ts   — Listen for V2 escrow events
dojo-backend/src/index.ts                      — Start autoSettler cron
dojo-backend/src/lib/types.ts                  — New task status types
dojo-backend/src/lib/socket.ts                 — New WebSocket event types
dojo-backend/prisma/schema.prisma              — New fields on Task model
dojo-frontend/src/app/dashboard/page.tsx       — Show dispute status and timers
dojo-frontend/src/components/TaskDetail.tsx     — Accept/Dispute buttons with deadlines
```

### Smart Contract: EscrowVaultV2

#### Box Storage Format (161 bytes)

```
Offset  Size  Field              Description
──────  ────  ─────              ───────────
0       32    client             Client Algorand address
32      32    worker             Agent Algorand address
64      32    sensei             Sensei Algorand address (receives payment)
96      8     bounty             Bounty amount in microAlgos
104     1     status             Task lifecycle status (0-5)
105     32    kite_hash          SHA-256 hash of task output (provenance)
137     8     submit_time        Unix timestamp when agent submitted result
145     8     review_deadline    Unix timestamp — client must act by this time
153     8     dispute_deadline   Unix timestamp — disputes must be raised by this time
```

#### Status Values

```
0 = LOCKED       — Bounty deposited, agent working
1 = SUBMITTED    — Agent delivered result, review window starts
2 = ACCEPTED     — Client explicitly accepted (triggers payment release)
3 = DISPUTED     — Client raised dispute within window
4 = COMPLETED    — Payment released to sensei (98/2 split)
5 = REFUNDED     — Bounty returned to client (slash)
```

#### Contract Methods

```python
class EscrowVaultV2(ARC4Contract):

    @abimethod(create="require")
    def create(self, admin: Address) -> None:
        """Initialize vault with admin and configurable durations."""

    @abimethod
    def lock_bounty(
        self,
        task_id: ARC4String,
        client: Address,
        worker: Address,
        sensei: Address,
        bounty_amount: ARC4UInt64,
        review_duration: ARC4UInt64,    # seconds (e.g., 86400 = 24h)
        dispute_duration: ARC4UInt64,   # seconds (e.g., 172800 = 48h)
        bounty_txn: gtxn.PaymentTransaction,
    ) -> Bool:
        """Lock bounty with configurable review and dispute windows."""

    @abimethod
    def submit_task(self, task_id: ARC4String, kite_hash: Bytes) -> Bool:
        """Agent submits result. Sets submit_time and calculates deadlines."""
        # review_deadline = Global.latest_timestamp + review_duration
        # dispute_deadline = review_deadline + dispute_duration

    @abimethod
    def accept_result(self, task_id: ARC4String) -> Bool:
        """Client accepts result within review window. Triggers release."""
        # assert Txn.sender == client
        # assert Global.latest_timestamp <= review_deadline
        # Calls internal release logic

    @abimethod
    def raise_dispute(self, task_id: ARC4String, reason_hash: Bytes) -> Bool:
        """Client raises dispute within dispute window."""
        # assert Txn.sender == client
        # assert Global.latest_timestamp <= dispute_deadline
        # assert Global.latest_timestamp > review_deadline (dispute window only)
        # Sets status to DISPUTED

    @abimethod
    def resolve_dispute(
        self, task_id: ARC4String, in_favor_of_client: Bool, treasury: Address
    ) -> Bool:
        """Admin resolves dispute. Releases or refunds based on ruling."""
        # assert Txn.sender == admin
        # if in_favor_of_client: refund 100% to client
        # else: release 98/2 to sensei/treasury

    @abimethod
    def auto_settle(self, task_id: ARC4String, treasury: Address) -> Bool:
        """Anyone can call after dispute_deadline passes. Auto-releases payment."""
        # assert Global.latest_timestamp > dispute_deadline
        # assert status == SUBMITTED (no dispute was raised)
        # Releases 98/2 to sensei/treasury

    @abimethod
    def release_payment(self, task_id: ARC4String, treasury: Address) -> Bool:
        """Internal: distributes 98% sensei, 2% treasury."""

    @abimethod
    def slash_bounty(self, task_id: ARC4String) -> Bool:
        """Admin slashes on dispute resolution favoring client."""
```

### Task Lifecycle Timeline

```
Time ─────────────────────────────────────────────────────────────────────►

│ LOCKED │        SUBMITTED        │   REVIEW    │    DISPUTE    │ SETTLED │
│        │                         │   WINDOW    │    WINDOW     │         │
│ Client │  Agent works on task    │ Client can  │ Client can    │ Payment │
│ locks  │  and submits result     │ accept or   │ raise dispute │ released│
│ bounty │                         │ do nothing  │ or do nothing │ or      │
│        │                         │             │               │ refunded│
│        │         submit_time     │review_deadline│dispute_deadline│       │
│        │              ▼          │      ▼      │       ▼       │         │

Possible outcomes:
  A) Client accepts during review window → immediate release (98/2)
  B) Client raises dispute during dispute window → admin resolves
  C) Client does nothing → auto_settle after dispute_deadline (98/2)
  D) Admin resolves dispute in client's favor → 100% refund
  E) Admin resolves dispute in sensei's favor → release (98/2)
```

### Default Durations (Configurable Per Task)

| Window | Default | Description |
|--------|---------|-------------|
| Review | 24 hours | Client reviews the delivered result |
| Dispute | 48 hours | Client can raise a formal dispute |
| Total | 72 hours | Maximum time from submission to auto-settlement |

### Backend: Auto-Settler Service

```typescript
// src/services/autoSettler.ts
// Runs every 5 minutes via setInterval

async function checkAutoSettle(): Promise<void> {
  // 1. Query tasks WHERE status = 'SUBMITTED'
  //    AND dispute_deadline < NOW
  //    AND no dispute raised
  //
  // 2. For each eligible task:
  //    - Call EscrowVaultV2.auto_settle(taskId, treasuryAddress)
  //    - Update local database status to COMPLETED
  //    - Emit WebSocket event: AUTO_SETTLED
  //    - Log settlement for audit trail
}
```

### API Endpoints (New)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks/:id/accept` | Client accepts result (within review window) |
| POST | `/tasks/:id/dispute` | Client raises dispute with reason (within dispute window) |
| POST | `/tasks/:id/resolve` | Admin resolves dispute (in favor of client or sensei) |
| GET | `/tasks/:id/timeline` | Returns all deadline timestamps and current phase |

### WebSocket Events (New)

```typescript
type DisputeEvents =
  | { type: 'TASK_SUBMITTED'; taskId: string; reviewDeadline: number; disputeDeadline: number }
  | { type: 'TASK_ACCEPTED'; taskId: string }
  | { type: 'DISPUTE_RAISED'; taskId: string; reasonHash: string }
  | { type: 'DISPUTE_RESOLVED'; taskId: string; inFavorOf: 'client' | 'sensei' }
  | { type: 'AUTO_SETTLED'; taskId: string };
```

### Database Changes (Prisma)

```prisma
model Task {
  // ... existing fields ...
  escrowVersion     Int       @default(1)    // 1 = old contract, 2 = new
  submitTime        DateTime?
  reviewDeadline    DateTime?
  disputeDeadline   DateTime?
  disputeReason     String?                  // Hash of dispute reason
  disputeResolution String?                  // 'client' | 'sensei'
  resolvedAt        DateTime?
}
```

### Migration Strategy

1. Deploy EscrowVaultV2 as a **new contract** with a new App ID on TestNet
2. Keep the original EscrowVault running — existing in-progress tasks settle through V1
3. Add `escrowVersion` field to Task model (default = 1 for existing tasks)
4. All **new** tasks created after deployment use V2 (escrowVersion = 2)
5. Update environment variable: add `ESCROW_VAULT_V2_APP_ID` alongside the existing one
6. Backend routes check `escrowVersion` to determine which contract client to use
7. Once all V1 tasks are settled (no more active V1 escrows), V1 can be deprecated
8. Frontend shows deadline timers only for V2 tasks; V1 tasks keep the old Satisfied/Not Satisfied flow

---

## Phase 3: NFT/Portable Agent Identity

### What It Is

Currently, agent identity lives in DojoRegistry Box Storage — a 97-byte record tied to the contract's state. It's not portable, not transferable, and not independently verifiable without querying our specific contract.

This phase mints an Algorand Standard Asset (ASA) NFT for each registered agent. The NFT lives in the Sensei's wallet, encodes the agent's full metadata, and serves as the canonical proof of registration. Anyone with an Algorand explorer can verify an agent's identity without touching our backend.

### Why It Matters

- Agent identity becomes a portable, wallet-held asset (Sensei truly owns it)
- Verifiable by anyone on-chain without querying our API
- Enables cross-platform agent discovery (other dApps can read the NFT)
- Foundation for DIDs and Verifiable Credentials (Phase 4)
- NFT can be displayed in wallet apps as proof of agent ownership

### Files Created

```
dojo-contracts/projects/smart_contracts/agent_nft/contract.py    — NFT minting/burning contract
dojo-contracts/projects/smart_contracts/agent_nft/__init__.py
dojo-backend/src/services/nftIdentityService.ts   — Mint, burn, verify NFT logic
dojo-backend/src/services/metadataService.ts      — Generate ARC-69 metadata JSON
dojo-backend/src/algorand/AgentNFTClient.ts       — Generated ARC-56 client
dojo-backend/src/artifacts/AgentNFT.arc56.json    — Contract ABI artifact
dojo-frontend/src/components/NFTBadge.tsx          — Visual NFT indicator on agent cards
dojo-frontend/src/app/verify/page.tsx              — Public agent verification page
scripts/migrate_existing_agents_nft.ts             — Retroactive NFT minting for existing agents
```

### Files Modified

```
dojo-backend/src/routes/agentRoutes.ts       — NFT endpoints + mint on registration
dojo-backend/src/services/indexerListener.ts — Listen for ASA creation/destruction
dojo-backend/prisma/schema.prisma            — NFT fields on Agent model
dojo-frontend/src/components/AgentCard.tsx    — Show NFT badge and explorer link
dojo-frontend/src/app/build/page.tsx         — Show minted NFT after registration
```

### ASA (Algorand Standard Asset) Configuration

```
Total Supply:    1          (true NFT — unique, non-fungible)
Decimals:        0          (indivisible)
Unit Name:       DOJO-ID    (8 chars max, identifies all Dojo agent NFTs)
Asset Name:      {agent_id} (up to 32 chars, e.g., "research-8xly6y")
URL:             ipfs://{CID} or https://api.dojo.0rca.io/metadata/{agent_id}
Manager:         AgentNFT contract address (can update metadata URL)
Reserve:         Sensei address (indicates ownership)
Freeze:          Zero address (not freezable)
Clawback:        AgentNFT contract address (enables burning on deregistration)
```

### Metadata Format (ARC-69 Standard)

Stored as the transaction note when creating the ASA, or at the URL endpoint:

```json
{
  "standard": "arc69",
  "description": "0rca Dojo Agent Identity NFT",
  "mime_type": "application/json",
  "properties": {
    "agent_id": "research-8xly6y",
    "lane": "research",
    "sensei_address": "ALGO_ADDRESS_HERE",
    "status": "LISTED",
    "capabilities": ["research", "citations", "analysis", "summarization"],
    "pricing": {
      "type": "bounty",
      "currency": "ALGO",
      "min_bounty": 1000000,
      "max_bounty": 50000000
    },
    "api_endpoint": "https://api.dojo.0rca.io/agents/research-8xly6y",
    "input_schema_version": 1,
    "registry_app_id": 758815322,
    "escrow_app_id": 761941677,
    "created_at": "2026-05-30T00:00:00Z",
    "stats": {
      "tasks_completed": 47,
      "tasks_failed": 2,
      "success_rate": 95.9
    }
  }
}
```

### Smart Contract: AgentNFT

```python
class AgentNFT(ARC4Contract):
    """Mints and manages agent identity NFTs as Algorand Standard Assets."""

    @abimethod(create="require")
    def create(self, admin: Address) -> None:
        """Initialize with admin address."""

    @abimethod
    def mint_identity(
        self,
        agent_id: ARC4String,
        sensei: Address,
        metadata_url: ARC4String,
    ) -> ARC4UInt64:
        """Mint a new agent identity NFT.
        
        Creates an ASA with:
        - total=1, decimals=0
        - unit_name="DOJO-ID"
        - asset_name=agent_id (truncated to 32 chars)
        - url=metadata_url (IPFS or HTTP)
        - manager=this contract
        - reserve=sensei
        - clawback=this contract
        
        Returns: the created ASA ID
        """

    @abimethod
    def burn_identity(self, asset_id: ARC4UInt64, sensei: Address) -> Bool:
        """Burn an agent identity NFT (deregistration).
        
        Only callable by admin or the sensei who owns the NFT.
        Uses clawback to reclaim the asset, then destroys it.
        """

    @abimethod
    def update_metadata_url(
        self, asset_id: ARC4UInt64, new_url: ARC4String
    ) -> Bool:
        """Update the metadata URL for an existing agent NFT.
        
        Only callable by admin. Uses asset config transaction
        to update the URL field.
        """
```

### Registration Flow (Updated)

```
Sensei clicks "Deploy Agent" on Build page
        │
        ▼
Backend: register_agent() on DojoRegistry (existing — creates box)
        │
        ▼
Backend: metadataService.generateMetadata(agentId, lane, sensei, schema)
        │
        ▼
Backend: Pin metadata to IPFS → get CID
        │
        ▼
Backend: nftIdentityService.mintAgentNFT(agentId, senseiAddress, ipfs://CID)
        │
        ▼
Contract: AgentNFT.mint_identity() → creates ASA, returns assetId
        │
        ▼
Backend: Store assetId in database (Agent.nftAssetId)
        │
        ▼
Frontend: Display "Agent NFT minted! Asset ID: 12345678"
          + Link to Pera Explorer: https://testnet.explorer.perawallet.app/asset/12345678
```

### Deregistration Flow

```
Sensei clicks "Deregister Agent"
        │
        ▼
Backend: nftIdentityService.burnAgentNFT(assetId, senseiAddress)
        │
        ▼
Contract: AgentNFT.burn_identity() → clawback + destroy ASA
        │
        ▼
Backend: delist_agent() on DojoRegistry (existing — sets status to DELISTED)
        │
        ▼
Backend: Set Agent.nftAssetId = null in database
        │
        ▼
Frontend: "Agent deregistered. NFT burned."
```

### Database Changes (Prisma)

```prisma
model Agent {
  // ... existing fields ...
  nftAssetId     BigInt?     // Algorand ASA ID of the identity NFT
  metadataUrl    String?     // IPFS or HTTP URL to full metadata JSON
  metadataCid    String?     // IPFS CID (if using IPFS)
  nftMintedAt    DateTime?   // When the NFT was minted
}
```

### API Endpoints (New)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents/:id/nft` | Returns NFT asset ID, metadata URL, mint timestamp |
| GET | `/agents/verify/:assetId` | Public — verify agent by ASA ID (no auth) |
| DELETE | `/agents/:id` | Deregister agent — burns NFT + delists from registry |

### Public Verification Page

A new page at `/verify` allows anyone to verify an agent's identity:

1. Enter an ASA ID or agent ID
2. Backend queries Algorand indexer for the ASA
3. Reads ARC-69 metadata from the creation transaction note
4. Displays: agent name, lane, sensei address, capabilities, stats
5. Shows on-chain proof: transaction ID, block number, timestamp
6. No login required — fully public

### Migration Strategy

1. Deploy AgentNFT contract to TestNet
2. Run `scripts/migrate_existing_agents_nft.ts`:
   - Reads all agents from DojoRegistry boxes
   - For each active agent: generates metadata, pins to IPFS, mints NFT
   - Updates database with `nftAssetId` for each agent
3. Sensei must opt-in to the ASA (Algorand requirement) — send opt-in notification via WebSocket
4. New agents get NFTs automatically on registration
5. Agents without NFTs still function (backward compatible) but show "Unverified" badge

---

## Phase 4: DIDs & Verifiable Credentials

### What It Is

NFT identity (Phase 3) answers "which agent is this?" but not "who built it and should I trust them?" This phase adds W3C Decentralized Identifiers (DIDs) and Verifiable Credentials (VCs) so Senseis can cryptographically prove their real-world identity, expertise, and compliance status.

### Why It Matters

- Clients can verify who built an agent before hiring it
- Platform can auto-issue credentials based on performance (Lane Expert, Stake Committed)
- Enables future regulatory compliance (KYB verification)
- Builds trust without centralized identity providers
- Differentiator vs competitors — on-chain reputation backed by cryptographic proofs

### Files Created

```
dojo-backend/src/services/didService.ts            — DID creation, resolution, verification
dojo-backend/src/services/credentialService.ts     — VC issuance, verification, storage
dojo-backend/src/services/autoCredentialIssuer.ts  — Auto-issues VCs based on metrics
dojo-backend/src/routes/identityRoutes.ts          — DID and VC API endpoints
dojo-frontend/src/components/CredentialBadge.tsx   — Visual credential indicators
dojo-frontend/src/components/DIDViewer.tsx         — Full DID document display
dojo-frontend/src/app/verify/credentials/page.tsx  — Public credential verification
```

### Files Modified

```
dojo-backend/src/index.ts                    — Mount identity routes
dojo-backend/prisma/schema.prisma            — DID and VC models
dojo-frontend/src/components/AgentCard.tsx    — Show credential badges
dojo-frontend/src/app/profile/page.tsx       — Sensei verification request flow
dojo-backend/src/services/nftIdentityService.ts — Link DID to NFT metadata
```

### DID Method: `did:algo`

We use a custom DID method anchored to Algorand addresses. The Sensei's Ed25519 keypair (which is their Algorand keypair) serves as the DID verification key.

#### DID Document Structure

```json
{
  "@context": [
    "https://www.w3.org/ns/did/v1",
    "https://w3id.org/security/suites/ed2519-2020/v1"
  ],
  "id": "did:algo:SENSEI_ALGORAND_ADDRESS",
  "verificationMethod": [
    {
      "id": "did:algo:SENSEI_ALGORAND_ADDRESS#key-1",
      "type": "Ed25519VerificationKey2020",
      "controller": "did:algo:SENSEI_ALGORAND_ADDRESS",
      "publicKeyMultibase": "zBase58EncodedPublicKey..."
    }
  ],
  "authentication": [
    "did:algo:SENSEI_ALGORAND_ADDRESS#key-1"
  ],
  "assertionMethod": [
    "did:algo:SENSEI_ALGORAND_ADDRESS#key-1"
  ],
  "service": [
    {
      "id": "did:algo:SENSEI_ALGORAND_ADDRESS#dojo-profile",
      "type": "DojoSenseiProfile",
      "serviceEndpoint": "https://api.dojo.0rca.io/senseis/SENSEI_ADDRESS"
    },
    {
      "id": "did:algo:SENSEI_ALGORAND_ADDRESS#agents",
      "type": "DojoAgentRegistry",
      "serviceEndpoint": "https://api.dojo.0rca.io/senseis/SENSEI_ADDRESS/agents"
    }
  ]
}
```

### Verifiable Credential Types

| Credential Type | Issued By | Trigger | Description |
|----------------|-----------|---------|-------------|
| `DojoSenseiVerified` | Platform admin | Manual review | Sensei's real-world identity verified |
| `LaneExpert` | Auto-issuer | 90%+ success rate, 50+ tasks | Proven expertise in a specific lane |
| `StakeCommitted` | Auto-issuer | Active stake in CommitmentLock | Has skin in the game |
| `HighVolume` | Auto-issuer | 200+ tasks completed | Reliable, high-throughput agent |
| `AuditPassed` | Platform admin | Manual | Agent code has been security audited |
| `EarlyAdopter` | Platform admin | One-time | Registered during TestNet phase |

### Verifiable Credential Structure (W3C Standard)

```json
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://dojo.0rca.io/credentials/v1"
  ],
  "id": "urn:uuid:credential-unique-id",
  "type": ["VerifiableCredential", "LaneExpert"],
  "issuer": "did:algo:DOJO_PLATFORM_ADMIN_ADDRESS",
  "issuanceDate": "2026-06-15T00:00:00Z",
  "expirationDate": "2027-06-15T00:00:00Z",
  "credentialSubject": {
    "id": "did:algo:SENSEI_ADDRESS",
    "lane": "research",
    "tasksCompleted": 87,
    "successRate": 94.2,
    "achievedAt": "2026-06-15T00:00:00Z"
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "created": "2026-06-15T00:00:00Z",
    "verificationMethod": "did:algo:DOJO_PLATFORM_ADMIN_ADDRESS#key-1",
    "proofPurpose": "assertionMethod",
    "proofValue": "zBase58EncodedSignature..."
  }
}
```

### Credential Issuance Flow

#### Auto-Issued (LaneExpert example)

```
autoCredentialIssuer runs daily cron
        │
        ▼
Query: agents WHERE tasksCompleted >= 50 AND successRate >= 90
       AND NOT already has LaneExpert credential for this lane
        │
        ▼
For each qualifying agent:
  1. Build credential JSON (credentialSubject with current stats)
  2. Sign with platform admin Ed25519 key (proofValue)
  3. Store in VerifiableCredential table
  4. Update NFT metadata to reference new credential
  5. Emit WebSocket: CREDENTIAL_ISSUED { agentId, type: "LaneExpert" }
```

#### Manually Issued (DojoSenseiVerified)

```
Sensei requests verification on Profile page
        │
        ▼
Admin reviews request in admin dashboard
        │
        ▼
Admin approves → credentialService.issueCredential(senseiDID, "DojoSenseiVerified", claims)
        │
        ▼
Credential signed, stored, linked to agent NFT metadata
        │
        ▼
Sensei sees "Verified" badge on their profile and agent cards
```

### Cryptographic Implementation

```typescript
// Using tweetnacl (already in project dependencies)
import nacl from 'tweetnacl';
import { decodeAddress } from 'algosdk';

function signCredential(credential: object, adminMnemonic: string): string {
  // 1. Derive Ed25519 keypair from Algorand mnemonic
  const account = algosdk.mnemonicToSecretKey(adminMnemonic);
  const secretKey = account.sk; // 64 bytes (32 private + 32 public)

  // 2. Canonical JSON of credential (without proof field)
  const { proof, ...credentialWithoutProof } = credential;
  const message = JSON.stringify(credentialWithoutProof, Object.keys(credentialWithoutProof).sort());

  // 3. Sign with Ed25519
  const signature = nacl.sign.detached(
    new TextEncoder().encode(message),
    secretKey
  );

  // 4. Return base58-encoded signature
  return base58Encode(signature);
}

function verifyCredential(credential: object): boolean {
  // 1. Extract issuer DID → resolve to public key
  const issuerAddress = credential.issuer.replace('did:algo:', '');
  const publicKey = decodeAddress(issuerAddress).publicKey;

  // 2. Reconstruct signed message
  const { proof, ...credentialWithoutProof } = credential;
  const message = JSON.stringify(credentialWithoutProof, Object.keys(credentialWithoutProof).sort());

  // 3. Verify Ed25519 signature
  const signature = base58Decode(proof.proofValue);
  return nacl.sign.detached.verify(
    new TextEncoder().encode(message),
    signature,
    publicKey
  );
}
```

### Database Changes (Prisma)

```prisma
model DIDDocument {
  id              String   @id @default(uuid())
  senseiAddress   String   @unique
  didString       String   @unique    // "did:algo:ADDRESS"
  document        Json                // Full DID document JSON
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  agents          Agent[]             // Agents linked to this DID
}

model VerifiableCredential {
  id              String   @id @default(uuid())
  agentId         String
  agent           Agent    @relation(fields: [agentId], references: [id])
  type            String              // "LaneExpert", "StakeCommitted", etc.
  credential      Json                // Full VC JSON including proof
  issuedAt        DateTime @default(now())
  expiresAt       DateTime?
  revoked         Boolean  @default(false)
  revokedAt       DateTime?
}

model Agent {
  // ... existing fields ...
  didId           String?
  did             DIDDocument? @relation(fields: [didId], references: [id])
  credentials     VerifiableCredential[]
}
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/identity/did` | Create DID for a Sensei (auto-generated from address) |
| GET | `/identity/did/:address` | Resolve DID document for an address |
| GET | `/agents/:id/credentials` | List all VCs for an agent |
| GET | `/verify/credential/:id` | Public — verify a specific credential |
| POST | `/agents/:id/verify-request` | Sensei requests manual verification |
| POST | `/admin/credentials/issue` | Admin manually issues a credential |
| POST | `/admin/credentials/revoke` | Admin revokes a credential |

### Migration Strategy

1. No contract changes — DIDs and VCs are stored off-chain (database + IPFS)
2. Auto-generate DIDs for all existing Senseis based on their Algorand addresses
3. Run auto-credential-issuer once to backfill credentials for qualifying agents
4. Update existing NFT metadata URLs to include DID references
5. Existing agents without credentials show "No credentials yet" — not broken

---

## Phase 5: MCP Server Integration

### What It Is

Model Context Protocol (MCP) is the standard for connecting AI agents to external tools and services. This phase exposes the entire 0rca Dojo as an MCP server — meaning any MCP-compatible AI client (Claude, Cursor, VS Code Copilot, custom agents) can discover, hire, and pay Dojo agents programmatically without using our web frontend.

### Why It Matters

- External AI agents can hire Dojo agents as sub-contractors (agent-to-agent economy)
- Developers can integrate Dojo into their AI workflows via standard tooling
- Massively expands the addressable market beyond web UI users
- Positions 0rca Dojo as infrastructure, not just a marketplace
- Aligns with ATXP's vision of agents paying for tools autonomously

### Files Created

```
dojo-backend/src/mcp/                          — MCP server directory
dojo-backend/src/mcp/index.ts                  — MCP server entry point
dojo-backend/src/mcp/transport.ts              — HTTP SSE + stdio transport handlers
dojo-backend/src/mcp/auth.ts                   — API key / ATXP connection auth
dojo-backend/src/mcp/tools/listAgents.ts       — Tool: discover available agents
dojo-backend/src/mcp/tools/getAgentSchema.ts   — Tool: get input requirements
dojo-backend/src/mcp/tools/hireAgent.ts        — Tool: create task + lock bounty
dojo-backend/src/mcp/tools/checkStatus.ts      — Tool: poll task progress
dojo-backend/src/mcp/tools/getResult.ts        — Tool: retrieve completed output
dojo-backend/src/mcp/tools/verifyAgent.ts      — Tool: check NFT + DID + credentials
dojo-backend/src/mcp/tools/raiseDispute.ts     — Tool: dispute a task result
mcp-config.json                                — Client configuration template
docs/MCP_INTEGRATION.md                        — Integration guide for developers
```

### Files Modified

```
dojo-backend/src/index.ts          — Mount MCP routes, start MCP server
dojo-backend/src/routes/index.ts   — Register MCP route handler
dojo-backend/package.json          — Add @modelcontextprotocol/sdk dependency
```

### MCP Tools Registry

Each tool follows the MCP specification with a name, description, and JSON Schema for inputs/outputs.

#### Tool: `dojo_list_agents`

```json
{
  "name": "dojo_list_agents",
  "description": "Browse available AI agents on the 0rca Dojo marketplace. Filter by lane (research, code, data, outreach), minimum success rate, or capabilities.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "lane": {
        "type": "string",
        "enum": ["research", "code", "data", "outreach"],
        "description": "Filter by agent specialization lane"
      },
      "minSuccessRate": {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
        "description": "Minimum success rate percentage"
      },
      "limit": {
        "type": "number",
        "default": 10,
        "description": "Maximum number of agents to return"
      },
      "capabilities": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Filter by specific capabilities"
      }
    }
  }
}
```

**Output**: Array of agent summaries:
```json
[
  {
    "agentId": "research-8xly6y",
    "lane": "research",
    "successRate": 95.9,
    "tasksCompleted": 47,
    "capabilities": ["research", "citations", "analysis"],
    "pricing": { "minBounty": "1 ALGO", "maxBounty": "50 ALGO" },
    "verified": true,
    "credentials": ["LaneExpert", "StakeCommitted"],
    "nftAssetId": 12345678
  }
]
```

#### Tool: `dojo_get_agent_schema`

```json
{
  "name": "dojo_get_agent_schema",
  "description": "Get the structured input schema for a specific agent. Use this to understand what inputs are required before hiring.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agentId": { "type": "string", "description": "The agent's unique identifier" }
    },
    "required": ["agentId"]
  }
}
```

**Output**: The agent's full InputSchema (from Phase 1).

#### Tool: `dojo_hire_agent`

```json
{
  "name": "dojo_hire_agent",
  "description": "Hire an agent to execute a task. Locks ALGO bounty in escrow. Returns a task ID for monitoring.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agentId": { "type": "string" },
      "inputData": { "type": "object", "description": "Structured input matching the agent's schema" },
      "bountyAmount": { "type": "number", "description": "Bounty in microAlgos" },
      "callerAddress": { "type": "string", "description": "Your Algorand address for escrow" },
      "reviewDuration": { "type": "number", "default": 86400, "description": "Review window in seconds" },
      "disputeDuration": { "type": "number", "default": 172800, "description": "Dispute window in seconds" }
    },
    "required": ["agentId", "inputData", "bountyAmount", "callerAddress"]
  }
}
```

**Output**:
```json
{
  "taskId": "task-abc123",
  "escrowTxnId": "ALGO_TXN_ID",
  "status": "LOCKED",
  "reviewDeadline": 1717171717,
  "disputeDeadline": 1717344517,
  "inputHash": "sha256-hex-string"
}
```

#### Tool: `dojo_check_task_status`

```json
{
  "name": "dojo_check_task_status",
  "description": "Check the current status of a task. Returns status, deadlines, and result if completed.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "taskId": { "type": "string", "description": "The task ID returned by dojo_hire_agent" }
    },
    "required": ["taskId"]
  }
}
```

**Output**:
```json
{
  "taskId": "task-abc123",
  "status": "SUBMITTED",
  "submitTime": 1717100000,
  "reviewDeadline": 1717171717,
  "disputeDeadline": 1717344517,
  "agentId": "research-8xly6y",
  "result": null
}
```

#### Tool: `dojo_get_task_result`

```json
{
  "name": "dojo_get_task_result",
  "description": "Retrieve the full result of a completed task. Only accessible by the task's client.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "taskId": { "type": "string" }
    },
    "required": ["taskId"]
  }
}
```

#### Tool: `dojo_verify_agent`

```json
{
  "name": "dojo_verify_agent",
  "description": "Verify an agent's on-chain identity, NFT, DID, and credentials. No authentication required.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agentId": { "type": "string" },
      "assetId": { "type": "number", "description": "Alternatively, verify by NFT asset ID" }
    }
  }
}
```

**Output**:
```json
{
  "verified": true,
  "agentId": "research-8xly6y",
  "nftAssetId": 12345678,
  "nftOnChain": true,
  "did": "did:algo:SENSEI_ADDRESS",
  "credentials": [
    { "type": "LaneExpert", "lane": "research", "issuedAt": "2026-06-15", "valid": true },
    { "type": "StakeCommitted", "stakeAmount": "10 ALGO", "valid": true }
  ],
  "explorerUrl": "https://testnet.explorer.perawallet.app/asset/12345678"
}
```

#### Tool: `dojo_raise_dispute`

```json
{
  "name": "dojo_raise_dispute",
  "description": "Raise a dispute on a task result within the dispute window.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "taskId": { "type": "string" },
      "reason": { "type": "string", "description": "Explanation of why the result is unsatisfactory" },
      "callerAddress": { "type": "string" }
    },
    "required": ["taskId", "reason", "callerAddress"]
  }
}
```

### MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP CLIENT                                 │
│  (Claude Desktop, Cursor, VS Code, Custom Agent)            │
└──────────────────────┬──────────────────────────────────────┘
                       │ JSON-RPC (stdio or HTTP SSE)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 DOJO MCP SERVER                               │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │Transport │  │   Auth   │  │  Tools   │  │  Algorand  │  │
│  │(SSE/stdio)│ │(API Key) │  │ Registry │  │  Client    │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                                                              │
│  Tools:                                                      │
│  • dojo_list_agents      (read-only, no auth)               │
│  • dojo_get_agent_schema (read-only, no auth)               │
│  • dojo_verify_agent     (read-only, no auth)               │
│  • dojo_hire_agent       (requires auth + funded wallet)    │
│  • dojo_check_task_status(requires auth)                    │
│  • dojo_get_task_result  (requires auth, client only)       │
│  • dojo_raise_dispute    (requires auth, client only)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              DOJO BACKEND (Express API)                       │
│              + Algorand TestNet                               │
└─────────────────────────────────────────────────────────────┘
```

### Transport Modes

**1. Local (stdio)** — For developers running Dojo locally:
```json
{
  "mcpServers": {
    "0rca-dojo": {
      "command": "node",
      "args": ["./dojo-backend/dist/mcp/index.js"],
      "env": {
        "DOJO_API_URL": "http://localhost:3001",
        "DOJO_MCP_API_KEY": "your-api-key"
      }
    }
  }
}
```

**2. Remote (HTTP SSE)** — For connecting to hosted Dojo instance:
```json
{
  "mcpServers": {
    "0rca-dojo": {
      "url": "https://api.dojo.0rca.io/mcp",
      "headers": {
        "Authorization": "Bearer your-api-key"
      }
    }
  }
}
```

### Authentication

Three auth methods supported:

1. **API Key** — Generated in Dojo dashboard, passed as Bearer token
2. **Wallet Signature** — Sign a challenge with Algorand private key (for programmatic agents)
3. **ATXP Connection String** — For agents using ATXP payment protocol (future integration)

```typescript
// src/mcp/auth.ts
async function authenticateMCPRequest(headers: Headers): Promise<AuthResult> {
  const authHeader = headers.get('Authorization');

  if (authHeader?.startsWith('Bearer ')) {
    const token = authHeader.slice(7);
    // Check if it's a Dojo API key
    const apiKey = await prisma.apiKey.findUnique({ where: { key: token } });
    if (apiKey) return { authenticated: true, address: apiKey.ownerAddress };
  }

  // Unauthenticated — only read-only tools available
  return { authenticated: false, address: null };
}
```

### Example Usage (Claude Desktop)

After adding the MCP config, a user can say:

> "Find me a research agent on 0rca Dojo with at least 90% success rate, then hire it to research Algorand AVM 11 changes. Budget: 5 ALGO."

Claude will:
1. Call `dojo_list_agents({ lane: "research", minSuccessRate: 90 })`
2. Call `dojo_get_agent_schema({ agentId: "research-8xly6y" })`
3. Call `dojo_hire_agent({ agentId: "research-8xly6y", inputData: {...}, bountyAmount: 5000000, callerAddress: "..." })`
4. Poll `dojo_check_task_status({ taskId: "..." })` until completed
5. Call `dojo_get_task_result({ taskId: "..." })` and present the research

### Migration Strategy

1. MCP is purely additive — no existing functionality changes
2. Deploy MCP server alongside existing Express routes (same process, different path)
3. MCP tools call the same internal services as the REST API (no duplication)
4. Start with read-only tools (list, schema, verify) — no auth required
5. Add write tools (hire, dispute) once auth is tested
6. Publish `mcp-config.json` template in docs for easy client setup

---

## Complete File Map

### New Files (All Phases)

```
dojo-backend/
├── src/
│   ├── mcp/                              [Phase 5]
│   │   ├── index.ts                      — MCP server entry point
│   │   ├── transport.ts                  — SSE + stdio handlers
│   │   ├── auth.ts                       — Authentication middleware
│   │   └── tools/
│   │       ├── listAgents.ts             — dojo_list_agents tool
│   │       ├── getAgentSchema.ts         — dojo_get_agent_schema tool
│   │       ├── hireAgent.ts              — dojo_hire_agent tool
│   │       ├── checkStatus.ts            — dojo_check_task_status tool
│   │       ├── getResult.ts              — dojo_get_task_result tool
│   │       ├── verifyAgent.ts            — dojo_verify_agent tool
│   │       └── raiseDispute.ts           — dojo_raise_dispute tool
│   ├── services/
│   │   ├── schemaService.ts              [Phase 1] — Input schema validation
│   │   ├── disputeService.ts             [Phase 2] — Dispute logic
│   │   ├── autoSettler.ts                [Phase 2] — Auto-settlement cron
│   │   ├── nftIdentityService.ts         [Phase 3] — NFT mint/burn/verify
│   │   ├── metadataService.ts            [Phase 3] — ARC-69 metadata generation
│   │   ├── didService.ts                 [Phase 4] — DID creation/resolution
│   │   ├── credentialService.ts          [Phase 4] — VC issuance/verification
│   │   └── autoCredentialIssuer.ts       [Phase 4] — Auto-issue VCs on metrics
│   ├── routes/
│   │   └── identityRoutes.ts             [Phase 4] — DID and VC endpoints
│   ├── algorand/
│   │   └── AgentNFTClient.ts             [Phase 3] — Generated contract client
│   └── artifacts/
│       └── AgentNFT.arc56.json           [Phase 3] — Contract ABI

dojo-contracts/
└── projects/smart_contracts/
    ├── escrow_vault_v2/                  [Phase 2]
    │   ├── contract.py                   — EscrowVaultV2 with dispute windows
    │   └── __init__.py
    └── agent_nft/                        [Phase 3]
        ├── contract.py                   — NFT minting/burning contract
        └── __init__.py

dojo-frontend/
└── src/
    ├── components/
    │   ├── DynamicTaskForm.tsx            [Phase 1] — Schema-driven form
    │   ├── DisputePanel.tsx              [Phase 2] — Dispute UI
    │   ├── CountdownTimer.tsx            [Phase 2] — Deadline countdown
    │   ├── NFTBadge.tsx                  [Phase 3] — NFT indicator
    │   ├── CredentialBadge.tsx           [Phase 4] — VC badges
    │   └── DIDViewer.tsx                 [Phase 4] — DID document display
    └── app/
        └── verify/
            ├── page.tsx                  [Phase 3] — Public agent verification
            └── credentials/
                └── page.tsx              [Phase 4] — Public credential verification

Root:
├── mcp-config.json                       [Phase 5] — MCP client config template
├── docs/MCP_INTEGRATION.md              [Phase 5] — Developer integration guide
└── scripts/
    └── migrate_existing_agents_nft.ts    [Phase 3] — Retroactive NFT minting
```

### Modified Files (All Phases)

```
dojo-backend/src/routes/agentRoutes.ts        [Phase 1, 3] — Schema + NFT endpoints
dojo-backend/src/routes/taskRoutes.ts         [Phase 1, 2] — Validation + dispute endpoints
dojo-backend/src/services/taskExecutor.ts     [Phase 1]    — Structured input passing
dojo-backend/src/services/indexerListener.ts  [Phase 2, 3] — V2 escrow + ASA events
dojo-backend/src/index.ts                     [Phase 2, 4, 5] — Cron + routes + MCP
dojo-backend/src/lib/types.ts                 [Phase 2]    — New status types
dojo-backend/src/lib/socket.ts                [Phase 2]    — New WebSocket events
dojo-backend/prisma/schema.prisma             [Phase 1-4]  — All database changes
dojo-backend/package.json                     [Phase 5]    — MCP SDK dependency
dojo-frontend/src/app/hire/page.tsx           [Phase 1]    — DynamicTaskForm integration
dojo-frontend/src/app/build/page.tsx          [Phase 1, 3] — Schema config + NFT display
dojo-frontend/src/app/dashboard/page.tsx      [Phase 2]    — Dispute status + timers
dojo-frontend/src/app/profile/page.tsx        [Phase 4]    — Verification request flow
dojo-frontend/src/components/AgentCard.tsx     [Phase 3, 4] — NFT badge + credentials
dojo-agents/lanes/research.py                 [Phase 1]    — Default schema definition
dojo-agents/lanes/code.py                     [Phase 1]    — Default schema definition
dojo-agents/lanes/data.py                     [Phase 1]    — Default schema definition
dojo-agents/lanes/outreach.py                 [Phase 1]    — Default schema definition
```

---

## Environment Variables (New)

```env
# Phase 2: EscrowVaultV2
ESCROW_VAULT_V2_APP_ID=           # New contract App ID
DEFAULT_REVIEW_DURATION=86400     # 24 hours in seconds
DEFAULT_DISPUTE_DURATION=172800   # 48 hours in seconds
AUTO_SETTLE_INTERVAL=300000       # 5 minutes in milliseconds

# Phase 3: NFT Identity
AGENT_NFT_APP_ID=                 # AgentNFT contract App ID
IPFS_PINATA_API_KEY=              # Pinata API key for IPFS pinning
IPFS_PINATA_SECRET=               # Pinata secret
METADATA_BASE_URL=                # Fallback HTTP URL for metadata

# Phase 4: DIDs & Credentials
PLATFORM_DID=                     # did:algo:ADMIN_ADDRESS
CREDENTIAL_EXPIRY_DAYS=365        # Default VC expiry

# Phase 5: MCP Server
MCP_ENABLED=true                  # Enable/disable MCP server
MCP_API_KEY_PREFIX=dojo_mcp_      # Prefix for MCP API keys
MCP_SSE_PATH=/mcp                 # HTTP SSE endpoint path
```

---

## Database Schema (Complete Additions)

```prisma
// ─── Phase 1: Structured Input Schema ───

model Agent {
  // ... existing fields ...
  inputSchema      Json?          // Published input schema
  schemaVersion    Int     @default(0)
  
  // Phase 3
  nftAssetId       BigInt?        // Algorand ASA ID
  metadataUrl      String?        // IPFS or HTTP metadata URL
  metadataCid      String?        // IPFS CID
  nftMintedAt      DateTime?
  
  // Phase 4
  didId            String?
  did              DIDDocument?   @relation(fields: [didId], references: [id])
  credentials      VerifiableCredential[]
}

model Task {
  // ... existing fields ...
  
  // Phase 1
  inputData        Json?          // Structured input from client
  inputHash        String?        // SHA-256 of canonical JSON input
  
  // Phase 2
  escrowVersion    Int     @default(1)  // 1=V1, 2=V2
  submitTime       DateTime?
  reviewDeadline   DateTime?
  disputeDeadline  DateTime?
  disputeReason    String?
  disputeResolution String?       // 'client' | 'sensei'
  resolvedAt       DateTime?
  resolvedBy       String?        // Admin address who resolved
}

// ─── Phase 4: DIDs & Verifiable Credentials ───

model DIDDocument {
  id              String   @id @default(uuid())
  senseiAddress   String   @unique
  didString       String   @unique
  document        Json
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  agents          Agent[]
}

model VerifiableCredential {
  id              String   @id @default(uuid())
  agentId         String
  agent           Agent    @relation(fields: [agentId], references: [id])
  type            String
  credential      Json
  issuedAt        DateTime @default(now())
  expiresAt       DateTime?
  revoked         Boolean  @default(false)
  revokedAt       DateTime?
}

// ─── Phase 5: MCP API Keys ───

model ApiKey {
  id              String   @id @default(uuid())
  key             String   @unique
  ownerAddress    String
  name            String
  permissions     String[] // ['read', 'write', 'dispute']
  createdAt       DateTime @default(now())
  lastUsedAt      DateTime?
  revoked         Boolean  @default(false)
}
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| EscrowVaultV2 has a bug | Funds locked/lost | Deploy on TestNet first; run parallel with V1; formal audit before MainNet |
| NFT minting fails mid-registration | Agent registered but no NFT | Make NFT minting non-blocking; retry queue; agent works without NFT |
| IPFS pinning service goes down | Metadata URLs return 404 | Store metadata hash on-chain; fallback to HTTP endpoint on our server |
| Auto-settler misses a deadline | Funds stuck in escrow | Anyone can call auto_settle (permissionless); add monitoring alerts |
| DID key compromise | Fake credentials issued | Credential revocation list; short expiry (1 year); re-issuance flow |
| MCP protocol breaking changes | External integrations break | Pin SDK version; version the MCP endpoint (/mcp/v1); deprecation notices |
| Algorand ASA opt-in requirement | Sensei can't receive NFT | Auto-send opt-in transaction during registration; clear UI guidance |

---

## How Each Phase Connects to Existing Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ALGORAND TESTNET (Trust Layer)                     │
│                                                                             │
│   ┌──────────────┐  ┌─────────────────┐  ┌──────────────┐  ┌───────────┐  │
│   │ EscrowVault  │  │ CommitmentLock  │  │ DojoRegistry │  │  Payout   │  │
│   │ V1 (Legacy)  │  │ (Agent Stakes)  │  │ (Identity)   │  │ Splitter  │  │
│   └──────────────┘  └─────────────────┘  └──────────────┘  └───────────┘  │
│                                                                             │
│   ┌──────────────┐  ┌─────────────────┐                                    │
│   │ EscrowVault  │  │   AgentNFT      │  ← NEW CONTRACTS                  │
│   │ V2 (Dispute) │  │ (ASA Minting)   │                                    │
│   └──────────────┘  └─────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               │
                    ┌──────────▼──────────────────────────────┐
                    │         DOJO NEXUS (Backend)             │
                    │                                          │
                    │  ┌─────────────┐  ┌──────────────────┐  │
                    │  │Schema Service│  │ Dispute Service  │  │ ← NEW SERVICES
                    │  └─────────────┘  └──────────────────┘  │
                    │  ┌─────────────┐  ┌──────────────────┐  │
                    │  │NFT Identity │  │  DID + Creds     │  │ ← NEW SERVICES
                    │  └─────────────┘  └──────────────────┘  │
                    │  ┌─────────────┐  ┌──────────────────┐  │
                    │  │ MCP Server  │  │  Auto-Settler    │  │ ← NEW SERVICES
                    │  └─────────────┘  └──────────────────┘  │
                    │                                          │
                    │  ┌─────────────┐  ┌──────────────────┐  │
                    │  │ Task Router │  │ Resolution Agent │  │ ← EXISTING
                    │  └─────────────┘  └──────────────────┘  │
                    └──────────────────────────────────────────┘
                               │                  │
              ┌────────────────▼──┐          ┌────▼────────────────┐
              │  DOJO FRONTEND    │          │  THE SWARM (Python) │
              │                   │          │                     │
              │  + DynamicForm    │          │  + Default Schemas  │
              │  + DisputePanel   │          │    per lane         │
              │  + NFT Badge      │          │                     │
              │  + Credentials    │          │                     │
              │  + Verify Page    │          │                     │
              └───────────────────┘          └────────────────────┘
                                                      │
                                             ┌────────▼────────────┐
                                             │   MCP CLIENTS       │
                                             │  (Claude, Cursor,   │
                                             │   Custom Agents)    │
                                             └─────────────────────┘
```

---

## Summary

| Phase | Capability | Contract Changes | Key Deliverable |
|-------|-----------|:---:|---|
| 1 | Structured Input Schema | None | Agents publish typed schemas; clients fill dynamic forms |
| 2 | Formal Dispute Windows | EscrowVaultV2 | Time-locked review → dispute → auto-settle lifecycle |
| 3 | NFT/Portable Identity | AgentNFT | Each agent = ASA NFT in Sensei's wallet |
| 4 | DIDs & Verifiable Credentials | None | Cryptographic proof of identity and expertise |
| 5 | MCP Server Integration | None | External AI agents can discover and hire Dojo agents |

---

## Phase 5 Addendum: MCP Client Credit & Payment Methods

### The Problem

When an external MCP client (Claude Desktop, Cursor, a custom autonomous agent) calls `dojo_hire_agent`, it needs to pay the bounty. But MCP clients don't have a built-in wallet or signing capability — they just call tools. We need a way to fund these tool calls without requiring the MCP client to sign Algorand transactions in real-time.

### Solution: Three Payment Methods (Hybrid)

We support three distinct funding mechanisms. The MCP server detects which one is being used based on the authentication header and routes accordingly.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MCP CLIENT REQUEST                               │
│                                                                     │
│  Authorization: Bearer dojo_mcp_XXXXX     → Credit Balance          │
│  Authorization: Bearer dojo_session_XXXXX → Delegated Session Key   │
│  X-402-Payment: <payment-proof>           → x402 Per-Call Payment   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    MCP AUTH RESOLVER                                  │
│                                                                      │
│  Detects funding method from headers → returns FundingContext        │
│  { type: 'credits' | 'session' | 'x402', ... }                     │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌──────────────┐ ┌──────────┐ ┌──────────────┐
     │Credit Balance│ │ Session  │ │ x402 Payment │
     │  Deduction   │ │Key Signing│ │ Verification │
     └──────┬───────┘ └────┬─────┘ └──────┬───────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
              ┌────────────────────────┐
              │  EscrowVaultV2         │
              │  lock_bounty(...)      │
              └────────────────────────┘
```

---

### Method 1: Pre-Funded Credit Balance

**Best for**: Human developers using Claude Desktop or Cursor who want zero-friction agent hiring via MCP.

**Concept**: Developer deposits ALGO into a platform-managed account upfront. Gets an API key. Every MCP tool call that costs money deducts from this balance. No wallet signing needed per-call.

#### How It Works

```
SETUP (one-time):
─────────────────
1. Developer visits Dojo dashboard → "MCP Credits" page
2. Connects wallet (Pera/Defly)
3. Deposits ALGO (e.g., 50 ALGO) → sent to platform's custodial deposit address
4. Backend creates CreditAccount record with balance = 50,000,000 microAlgos
5. Developer generates an MCP API key (prefixed: dojo_mcp_)
6. Developer adds API key to their MCP client config (Claude/Cursor)

USAGE (every hire):
───────────────────
1. MCP client calls dojo_hire_agent({ bountyAmount: 5000000, ... })
   with header: Authorization: Bearer dojo_mcp_abc123xyz
2. Backend resolves API key → finds CreditAccount
3. Backend checks: account.balance >= bountyAmount?
4. YES → Deduct bountyAmount from balance
        → Platform signs lock_bounty on EscrowVaultV2 as the "client"
        → Task created, agent starts working
5. NO  → Return error: { code: "INSUFFICIENT_CREDITS", balance: 2000000, required: 5000000 }
```

#### Pseudocode: Credit Balance Service

```typescript
// src/services/creditService.ts

interface CreditAccount {
  id: string;
  ownerAddress: string;       // Developer's real Algorand address
  apiKeyId: string;           // Linked MCP API key
  balance: bigint;            // Current balance in microAlgos
  totalDeposited: bigint;     // Lifetime deposits
  totalSpent: bigint;         // Lifetime spending
  depositAddress: string;     // Platform custodial address for this account
}

async function deductCredits(apiKey: string, amount: bigint, taskId: string): Promise<DeductResult> {
  // 1. Find the credit account linked to this API key
  const account = await prisma.creditAccount.findFirst({
    where: { apiKey: { key: apiKey } }
  });
  if (!account) throw new Error('Invalid API key');

  // 2. Check sufficient balance
  if (account.balance < amount) {
    return {
      success: false,
      error: 'INSUFFICIENT_CREDITS',
      balance: account.balance,
      required: amount
    };
  }

  // 3. Atomic deduction + transaction log (prevents race conditions)
  const [updatedAccount, txnLog] = await prisma.$transaction([
    prisma.creditAccount.update({
      where: { id: account.id },
      data: {
        balance: { decrement: amount },
        totalSpent: { increment: amount }
      }
    }),
    prisma.creditTransaction.create({
      data: {
        accountId: account.id,
        type: 'hire',
        amount: -amount,
        taskId: taskId,
        description: `Bounty for task ${taskId}`
      }
    })
  ]);

  return { success: true, remainingBalance: updatedAccount.balance };
}

async function refundCredits(taskId: string): Promise<void> {
  // Called when a task is refunded (dispute resolved in client's favor)
  const txn = await prisma.creditTransaction.findFirst({
    where: { taskId, type: 'hire' }
  });
  if (!txn) return;

  await prisma.$transaction([
    prisma.creditAccount.update({
      where: { id: txn.accountId },
      data: { balance: { increment: BigInt(Math.abs(Number(txn.amount))) } }
    }),
    prisma.creditTransaction.create({
      data: {
        accountId: txn.accountId,
        type: 'refund',
        amount: BigInt(Math.abs(Number(txn.amount))),
        taskId: taskId,
        description: `Refund for disputed task ${taskId}`
      }
    })
  ]);
}
```

#### Pseudocode: Deposit Detection (Indexer Listener)

```typescript
// Added to src/services/indexerListener.ts

async function detectCreditDeposits(): Promise<void> {
  // Poll Algorand indexer for payments TO our deposit addresses
  // with a note field containing the API key or account ID

  const recentTxns = await indexerClient
    .searchForTransactions()
    .address(PLATFORM_DEPOSIT_ADDRESS)
    .addressRole('receiver')
    .afterTime(lastCheckedTimestamp)
    .do();

  for (const txn of recentTxns.transactions) {
    const note = Buffer.from(txn.note || '', 'base64').toString();

    // Note format: "dojo_credit:{accountId}" or "dojo_credit:{apiKey}"
    if (!note.startsWith('dojo_credit:')) continue;

    const identifier = note.replace('dojo_credit:', '');
    const amount = BigInt(txn['payment-transaction'].amount);

    // Credit the account
    await prisma.$transaction([
      prisma.creditAccount.update({
        where: { id: identifier },
        data: {
          balance: { increment: amount },
          totalDeposited: { increment: amount }
        }
      }),
      prisma.creditTransaction.create({
        data: {
          accountId: identifier,
          type: 'deposit',
          amount: amount,
          txnId: txn.id,
          description: `Deposit from ${txn.sender}`
        }
      })
    ]);

    // Notify via WebSocket
    emitEvent('CREDIT_DEPOSITED', { accountId: identifier, amount, txnId: txn.id });
  }
}
```

#### On-Chain Escrow: Platform as Proxy Client

When an MCP client pays via credits, the platform itself acts as the "client" on the EscrowVault contract:

```typescript
async function lockBountyFromCredits(taskId: string, agentId: string, bountyAmount: bigint) {
  // Platform signs the lock_bounty transaction using its admin key
  // The "client" address on-chain is the platform's deposit address
  // But internally we track the real owner via CreditAccount

  const result = await escrowVaultV2Client.lockBounty({
    taskId: taskId,
    client: PLATFORM_DEPOSIT_ADDRESS,    // Platform acts as client on-chain
    worker: agent.walletAddress,
    sensei: agent.senseiAddress,
    bountyAmount: bountyAmount,
    reviewDuration: DEFAULT_REVIEW_DURATION,
    disputeDuration: DEFAULT_DISPUTE_DURATION,
    bountyTxn: paymentTxn,               // Platform sends from deposit pool
  });

  return result;
}
```

#### Refund Handling

When a credit-funded task gets refunded:
- On-chain: refund goes to `PLATFORM_DEPOSIT_ADDRESS` (since platform was the on-chain client)
- Off-chain: backend detects the refund and credits the developer's CreditAccount balance
- Developer sees their balance restored in the dashboard

#### Top-Up Methods

| Method | How | Best For |
|--------|-----|----------|
| Dashboard deposit | Connect wallet → sign payment to deposit address with note | Manual top-ups |
| Direct transfer | Send ALGO to deposit address with `dojo_credit:{id}` in note field | Programmatic |
| Auto-refill | Set threshold (e.g., "refill to 20 ALGO when below 5 ALGO") | Power users |

---

### Method 2: x402 Per-Call Payment (Non-Custodial)

**Best for**: Autonomous AI agents that have their own Algorand wallets (ATXP-powered agents, custom bots).

**Concept**: The MCP server responds with HTTP 402 (Payment Required) when a paid tool is called without payment proof. The client's x402-compatible HTTP wrapper automatically signs and submits the payment, then retries the request with proof attached.

This leverages the existing `x402Service.ts` already in the codebase.

#### How It Works

```
FIRST REQUEST (no payment):
────────────────────────────
1. MCP client calls dojo_hire_agent({ bountyAmount: 5000000, ... })
   No payment header attached
2. Backend returns HTTP 402 with payment requirements:
   {
     "x402": {
       "version": 1,
       "scheme": "exact",
       "network": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
       "payTo": "PLATFORM_TREASURY_ADDRESS",
       "price": "5000000",
       "extra": {
         "asset": "0",
         "decimals": 6,
         "description": "Bounty for research agent research-8xly6y"
       }
     }
   }

AUTOMATIC RETRY (with payment):
───────────────────────────────
3. Client's x402 fetch wrapper sees 402 → signs payment transaction
4. Client retries same request with header:
   X-402-Payment: <base64-encoded-signed-transaction>
5. Backend verifies payment on-chain (or via facilitator)
6. Payment confirmed → lock bounty in EscrowVaultV2
7. Return task ID to client
```

#### Pseudocode: x402 MCP Middleware

```typescript
// src/mcp/middleware/x402Middleware.ts

import { verifyPayment } from '../services/x402Service';

interface PaymentRequirement {
  version: number;
  scheme: 'exact';
  network: string;
  payTo: string;
  price: string;
  extra: {
    asset: string;
    decimals: number;
    description: string;
  };
}

async function handleX402Payment(
  request: MCPRequest,
  requiredAmount: bigint,
  description: string
): Promise<X402Result> {

  const paymentHeader = request.headers['x-402-payment'];

  // No payment attached → return 402 with requirements
  if (!paymentHeader) {
    return {
      status: 402,
      body: {
        x402: {
          version: 1,
          scheme: 'exact',
          network: ALGORAND_TESTNET_CAIP2,
          payTo: PLATFORM_TREASURY_ADDRESS,
          price: requiredAmount.toString(),
          extra: {
            asset: '0',  // 0 = native ALGO
            decimals: 6,
            description: description
          }
        }
      }
    };
  }

  // Payment attached → verify it
  const verification = await verifyX402Payment(paymentHeader, requiredAmount);

  if (!verification.valid) {
    return {
      status: 402,
      body: { error: 'Payment verification failed', reason: verification.reason }
    };
  }

  // Payment verified → proceed with the tool call
  return {
    status: 200,
    payerAddress: verification.senderAddress,
    txnId: verification.transactionId
  };
}

async function verifyX402Payment(
  paymentProof: string,
  expectedAmount: bigint
): Promise<VerificationResult> {

  // 1. Decode the payment proof (base64 → signed transaction)
  const signedTxn = Buffer.from(paymentProof, 'base64');

  // 2. Submit to Algorand network (or check if already confirmed)
  //    The x402 facilitator handles this, or we verify directly
  const facilitatorUrl = process.env.X402_FACILITATOR_URL;

  const response = await fetch(`${facilitatorUrl}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      signedTransaction: paymentProof,
      expectedReceiver: PLATFORM_TREASURY_ADDRESS,
      expectedAmount: expectedAmount.toString()
    })
  });

  const result = await response.json();

  if (result.verified) {
    return {
      valid: true,
      senderAddress: result.sender,
      transactionId: result.txnId,
      amount: BigInt(result.amount)
    };
  }

  return { valid: false, reason: result.error };
}
```

#### Pseudocode: x402-Enabled MCP Tool Handler

```typescript
// Inside src/mcp/tools/hireAgent.ts

async function handleHireAgent(params: HireAgentParams, request: MCPRequest) {
  const { agentId, inputData, bountyAmount } = params;

  // Check for x402 payment
  const paymentResult = await handleX402Payment(
    request,
    BigInt(bountyAmount),
    `Bounty for agent ${agentId}`
  );

  // If 402 returned, send it back to client (triggers auto-payment)
  if (paymentResult.status === 402) {
    return paymentResult;
  }

  // Payment verified — the payer becomes the "client" on the escrow
  const clientAddress = paymentResult.payerAddress;

  // Lock bounty using the verified payment
  const task = await createTaskWithEscrow({
    agentId,
    inputData,
    bountyAmount: BigInt(bountyAmount),
    clientAddress: clientAddress,    // The actual payer's address
    fundingMethod: 'x402',
    paymentTxnId: paymentResult.txnId
  });

  return {
    taskId: task.id,
    status: 'LOCKED',
    clientAddress: clientAddress,
    escrowTxnId: paymentResult.txnId
  };
}
```

#### Client-Side Setup (for agent developers)

An autonomous agent using x402 needs:

```typescript
// The agent's code (e.g., an ATXP-powered agent)
import { wrapFetchWithPayment, x402Client } from '@x402-avm/fetch';
import { toClientAvmSigner, ExactAvmScheme, ALGORAND_TESTNET_CAIP2 } from '@x402-avm/avm';

// Agent has its own Algorand private key
const signer = toClientAvmSigner(process.env.AGENT_PRIVATE_KEY);
const client = new x402Client();
client.register(ALGORAND_TESTNET_CAIP2, new ExactAvmScheme(signer));

// Wrap fetch — automatically handles 402 responses
const paidFetch = wrapFetchWithPayment(fetch, client);

// Now MCP calls through this fetch will auto-pay
const response = await paidFetch('https://api.dojo.0rca.io/mcp', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'tools/call',
    params: { name: 'dojo_hire_agent', arguments: { agentId: '...', bountyAmount: 5000000 } }
  })
});
```

#### Refund Handling

When an x402-funded task gets refunded:
- On-chain: refund goes directly to the payer's Algorand address (they were the on-chain client)
- No platform intermediary needed — standard EscrowVaultV2 refund flow
- Fully non-custodial

---

### Method 3: Delegated Session Key (Non-Custodial, Batch Operations)

**Best for**: Developers running automated pipelines that hire multiple agents in sequence without manual signing each time, but who don't want to trust the platform with their main wallet.

**Concept**: Developer creates a temporary Algorand account (session key), funds it with a limited budget, and registers it with the Dojo backend. The backend uses this session key to sign escrow transactions on behalf of the developer. The session key has a TTL and budget cap — limiting blast radius if compromised.

#### How It Works

```
SETUP (per session):
────────────────────
1. Developer calls POST /sessions/create { budget: 20000000, ttlHours: 24 }
2. Backend generates a new Algorand keypair (session account)
3. Backend encrypts the private key with AES-256-GCM (same vault pattern as Neural Keys)
4. Returns: { sessionAddress: "ALGO...", sessionToken: "dojo_session_xyz", expiresAt: "..." }
5. Developer funds the session address with ALGO (sends 20 ALGO to sessionAddress)
6. Developer uses sessionToken in MCP config as the auth bearer

USAGE (every hire):
───────────────────
1. MCP client calls dojo_hire_agent({ bountyAmount: 5000000, ... })
   with header: Authorization: Bearer dojo_session_xyz
2. Backend resolves session token → finds SessionKey record
3. Backend checks:
   - Session not expired? (expiresAt > now)
   - Session has budget? (remainingBudget >= bountyAmount)
   - Session address has on-chain balance? (query algod)
4. All checks pass → Backend decrypts session private key from vault
5. Backend signs lock_bounty transaction using session key
   (session address = "client" on the escrow contract)
6. Deduct from remainingBudget tracking
7. Return task ID

COMPLETION:
───────────
- On success: bounty released to sensei (normal flow)
- On refund: ALGO returns to session address
- Developer can withdraw remaining funds from session address anytime
- Session auto-expires after TTL — remaining funds stay in session address for developer to reclaim
```

#### Pseudocode: Session Key Service

```typescript
// src/services/sessionKeyService.ts

import algosdk from 'algosdk';
import { encrypt, decrypt } from './configVault';  // Reuse existing vault encryption

interface SessionKey {
  id: string;
  ownerAddress: string;        // Developer's main address (for ownership proof)
  sessionAddress: string;      // Generated session Algorand address
  encryptedSecretKey: string;  // AES-256-GCM encrypted private key
  sessionToken: string;        // Bearer token for MCP auth (dojo_session_xxx)
  budget: bigint;              // Maximum spend limit (microAlgos)
  remainingBudget: bigint;     // How much is left to spend
  expiresAt: Date;             // TTL expiry
  createdAt: Date;
  revokedAt: Date | null;      // Null = active, Date = manually revoked
}

async function createSession(
  ownerAddress: string,
  budget: bigint,
  ttlHours: number
): Promise<CreateSessionResult> {

  // 1. Generate a fresh Algorand keypair
  const sessionAccount = algosdk.generateAccount();
  const sessionAddress = sessionAccount.addr;
  const secretKey = Buffer.from(sessionAccount.sk).toString('base64');

  // 2. Encrypt the secret key using the same vault pattern (AES-256-GCM)
  const encryptedKey = encrypt(secretKey, process.env.VAULT_KEY);

  // 3. Generate a unique session token
  const sessionToken = `dojo_session_${generateSecureRandom(24)}`;

  // 4. Calculate expiry
  const expiresAt = new Date(Date.now() + ttlHours * 60 * 60 * 1000);

  // 5. Store in database
  const session = await prisma.sessionKey.create({
    data: {
      ownerAddress,
      sessionAddress,
      encryptedSecretKey: encryptedKey,
      sessionToken,
      budget,
      remainingBudget: budget,
      expiresAt,
    }
  });

  return {
    sessionAddress,          // Developer must fund this address
    sessionToken,            // Use in MCP config: Authorization: Bearer dojo_session_xyz
    expiresAt,
    budget,
    fundingInstructions: `Send ${Number(budget) / 1_000_000} ALGO to ${sessionAddress}`
  };
}

async function useSession(
  sessionToken: string,
  amount: bigint
): Promise<UseSessionResult> {

  // 1. Find and validate session
  const session = await prisma.sessionKey.findUnique({
    where: { sessionToken }
  });

  if (!session) throw new Error('Invalid session token');
  if (session.revokedAt) throw new Error('Session revoked');
  if (session.expiresAt < new Date()) throw new Error('Session expired');
  if (session.remainingBudget < amount) {
    throw new Error(`Insufficient session budget. Remaining: ${session.remainingBudget}, Required: ${amount}`);
  }

  // 2. Verify on-chain balance of session address
  const accountInfo = await algodClient.accountInformation(session.sessionAddress).do();
  const onChainBalance = BigInt(accountInfo.amount) - BigInt(accountInfo['min-balance']);

  if (onChainBalance < amount) {
    throw new Error(`Session address underfunded. On-chain: ${onChainBalance}, Required: ${amount}`);
  }

  // 3. Decrypt the session private key
  const secretKeyBase64 = decrypt(session.encryptedSecretKey, process.env.VAULT_KEY);
  const secretKey = new Uint8Array(Buffer.from(secretKeyBase64, 'base64'));

  // 4. Deduct from budget tracking
  await prisma.sessionKey.update({
    where: { id: session.id },
    data: { remainingBudget: { decrement: amount } }
  });

  return {
    sessionAddress: session.sessionAddress,
    secretKey,               // Used to sign the escrow transaction
    ownerAddress: session.ownerAddress
  };
}

async function signEscrowWithSession(
  session: UseSessionResult,
  taskId: string,
  agentWallet: string,
  senseiAddress: string,
  bountyAmount: bigint
): Promise<string> {

  // Build the lock_bounty atomic transaction group:
  // 1. Payment: session address → EscrowVaultV2 (bounty amount)
  // 2. App call: EscrowVaultV2.lock_bounty(...)

  const suggestedParams = await algodClient.getTransactionParams().do();

  // Payment transaction
  const paymentTxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
    from: session.sessionAddress,
    to: ESCROW_VAULT_V2_ADDRESS,
    amount: Number(bountyAmount),
    suggestedParams,
  });

  // App call transaction (lock_bounty)
  const appCallTxn = algosdk.makeApplicationCallTxnFromObject({
    from: session.sessionAddress,
    appIndex: ESCROW_VAULT_V2_APP_ID,
    appArgs: [/* ABI encoded lock_bounty args */],
    accounts: [agentWallet, senseiAddress, TREASURY_ADDRESS],
    suggestedParams: { ...suggestedParams, fee: 3000 },  // Extra fee for inner txns
  });

  // Group and sign
  const group = algosdk.assignGroupID([paymentTxn, appCallTxn]);
  const signedPayment = group[0].signTxn(session.secretKey);
  const signedAppCall = group[1].signTxn(session.secretKey);

  // Submit
  const { txId } = await algodClient.sendRawTransaction([signedPayment, signedAppCall]).do();
  await algosdk.waitForConfirmation(algodClient, txId, 4);

  return txId;
}
```

#### Pseudocode: Session Management Endpoints

```typescript
// src/routes/sessionRoutes.ts

// Create a new session
router.post('/sessions/create', authMiddleware, async (req, res) => {
  const { budget, ttlHours = 24 } = req.body;
  const ownerAddress = req.user.address;  // From wallet auth

  // Validate: budget must be between 1 ALGO and 1000 ALGO
  if (budget < 1_000_000 || budget > 1_000_000_000) {
    return res.status(400).json({ error: 'Budget must be between 1 and 1000 ALGO' });
  }

  // Validate: TTL must be between 1 hour and 7 days
  if (ttlHours < 1 || ttlHours > 168) {
    return res.status(400).json({ error: 'TTL must be between 1 and 168 hours' });
  }

  const session = await createSession(ownerAddress, BigInt(budget), ttlHours);
  res.json(session);
});

// List active sessions
router.get('/sessions', authMiddleware, async (req, res) => {
  const sessions = await prisma.sessionKey.findMany({
    where: {
      ownerAddress: req.user.address,
      revokedAt: null,
      expiresAt: { gt: new Date() }
    },
    select: {
      id: true,
      sessionAddress: true,
      budget: true,
      remainingBudget: true,
      expiresAt: true,
      createdAt: true
    }
  });
  res.json(sessions);
});

// Revoke a session (emergency kill switch)
router.post('/sessions/:id/revoke', authMiddleware, async (req, res) => {
  const session = await prisma.sessionKey.findUnique({ where: { id: req.params.id } });

  if (!session || session.ownerAddress !== req.user.address) {
    return res.status(404).json({ error: 'Session not found' });
  }

  await prisma.sessionKey.update({
    where: { id: session.id },
    data: { revokedAt: new Date() }
  });

  res.json({ revoked: true, message: 'Session revoked. Remaining funds in session address can be withdrawn.' });
});

// Withdraw remaining funds from session address
router.post('/sessions/:id/withdraw', authMiddleware, async (req, res) => {
  const session = await prisma.sessionKey.findUnique({ where: { id: req.params.id } });

  if (!session || session.ownerAddress !== req.user.address) {
    return res.status(404).json({ error: 'Session not found' });
  }

  // Decrypt key, send remaining balance back to owner
  const secretKey = decrypt(session.encryptedSecretKey, process.env.VAULT_KEY);
  const balance = await getAccountBalance(session.sessionAddress);
  const withdrawAmount = balance - 100_000;  // Keep min balance for close-out

  if (withdrawAmount <= 0) {
    return res.status(400).json({ error: 'No funds to withdraw' });
  }

  // Sign close-out transaction: session → owner
  const txnId = await sendCloseOutTransaction(
    session.sessionAddress,
    secretKey,
    session.ownerAddress,
    withdrawAmount
  );

  // Mark session as revoked
  await prisma.sessionKey.update({
    where: { id: session.id },
    data: { revokedAt: new Date(), remainingBudget: 0n }
  });

  res.json({ withdrawn: withdrawAmount, txnId, to: session.ownerAddress });
});
```

#### Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Session key leaked | Limited budget + TTL. Max damage = remaining budget. Developer can revoke instantly. |
| Backend compromised | Session keys encrypted with AES-256-GCM (same as Neural Keys). Attacker needs VAULT_KEY. |
| Session address drained | Budget tracking is off-chain; on-chain balance is the real limit. Can't spend more than what's in the address. |
| Stale sessions | Cron job expires sessions past TTL. Expired sessions can't be used even if token is known. |

#### Refund Handling

When a session-funded task gets refunded:
- On-chain: refund goes to the session address (it was the on-chain client)
- Backend: increments `remainingBudget` on the session record
- Developer can withdraw the refunded amount via `/sessions/:id/withdraw`
- If session is expired, funds sit in session address until developer withdraws

---

### MCP Auth Resolver (Unified Handler)

This is the central routing logic that detects which payment method is being used and returns the appropriate funding context.

```typescript
// src/mcp/auth.ts

type FundingMethod =
  | { type: 'credits'; accountId: string; balance: bigint; ownerAddress: string }
  | { type: 'session'; sessionAddress: string; secretKey: Uint8Array; ownerAddress: string }
  | { type: 'x402'; verified: true; payerAddress: string; txnId: string }
  | { type: 'none'; readOnly: true };

async function resolveFunding(request: MCPRequest, requiredAmount?: bigint): Promise<FundingMethod> {
  const authHeader = request.headers['authorization'] || '';
  const x402Header = request.headers['x-402-payment'];

  // ─── Method 1: Credit Balance ───
  if (authHeader.startsWith('Bearer dojo_mcp_')) {
    const token = authHeader.slice(7);  // Remove "Bearer "
    const apiKey = await prisma.apiKey.findUnique({ where: { key: token, revoked: false } });

    if (!apiKey) throw new AuthError('Invalid API key');

    const account = await prisma.creditAccount.findFirst({
      where: { apiKeyId: apiKey.id }
    });

    if (!account) throw new AuthError('No credit account linked to this key');

    return {
      type: 'credits',
      accountId: account.id,
      balance: account.balance,
      ownerAddress: account.ownerAddress
    };
  }

  // ─── Method 3: Delegated Session Key ───
  if (authHeader.startsWith('Bearer dojo_session_')) {
    const token = authHeader.slice(7);
    const session = await prisma.sessionKey.findUnique({ where: { sessionToken: token } });

    if (!session) throw new AuthError('Invalid session token');
    if (session.revokedAt) throw new AuthError('Session revoked');
    if (session.expiresAt < new Date()) throw new AuthError('Session expired');

    if (requiredAmount && session.remainingBudget < requiredAmount) {
      throw new AuthError(`Insufficient session budget. Has: ${session.remainingBudget}, Needs: ${requiredAmount}`);
    }

    // Decrypt session key
    const secretKeyBase64 = decrypt(session.encryptedSecretKey, process.env.VAULT_KEY);
    const secretKey = new Uint8Array(Buffer.from(secretKeyBase64, 'base64'));

    return {
      type: 'session',
      sessionAddress: session.sessionAddress,
      secretKey,
      ownerAddress: session.ownerAddress
    };
  }

  // ─── Method 2: x402 Per-Call Payment ───
  if (x402Header) {
    const verification = await verifyX402Payment(x402Header, requiredAmount || 0n);

    if (!verification.valid) {
      throw new AuthError(`x402 payment invalid: ${verification.reason}`);
    }

    return {
      type: 'x402',
      verified: true,
      payerAddress: verification.senderAddress,
      txnId: verification.transactionId
    };
  }

  // ─── No payment method: read-only access ───
  return { type: 'none', readOnly: true };
}
```

### Unified Hire Flow (All Methods Combined)

```typescript
// src/mcp/tools/hireAgent.ts — final version using all 3 methods

async function handleHireAgent(params: HireAgentParams, request: MCPRequest) {
  const { agentId, inputData, bountyAmount } = params;
  const amount = BigInt(bountyAmount);

  // 1. Resolve funding method
  const funding = await resolveFunding(request, amount);

  if (funding.type === 'none') {
    // No payment method → return 402 with payment requirements (triggers x402 flow)
    return {
      status: 402,
      body: buildPaymentRequirements(amount, `Bounty for agent ${agentId}`)
    };
  }

  // 2. Execute based on funding type
  let taskId: string;
  let clientAddress: string;
  let escrowTxnId: string;

  switch (funding.type) {
    case 'credits':
      // Deduct from balance, platform signs escrow as proxy
      const deduction = await deductCredits(funding.accountId, amount, taskId);
      if (!deduction.success) return { status: 402, body: deduction };
      clientAddress = PLATFORM_DEPOSIT_ADDRESS;
      escrowTxnId = await lockBountyFromCredits(taskId, agentId, amount);
      break;

    case 'session':
      // Sign escrow with session key (session address = client)
      clientAddress = funding.sessionAddress;
      escrowTxnId = await signEscrowWithSession(funding, taskId, agent, amount);
      // Deduct from session budget
      await prisma.sessionKey.update({
        where: { sessionAddress: funding.sessionAddress },
        data: { remainingBudget: { decrement: amount } }
      });
      break;

    case 'x402':
      // Payment already verified — lock bounty with payer as client
      clientAddress = funding.payerAddress;
      escrowTxnId = funding.txnId;
      // Bounty already transferred via x402 payment
      break;
  }

  // 3. Create task record
  const task = await prisma.task.create({
    data: {
      id: taskId,
      agentId,
      inputData,
      inputHash: computeInputHash(inputData),
      clientAddress,
      bountyAmount: amount,
      fundingMethod: funding.type,
      escrowTxnId,
      status: 'LOCKED'
    }
  });

  // 4. Trigger agent execution
  await taskExecutor.execute(task);

  return {
    taskId: task.id,
    status: 'LOCKED',
    fundingMethod: funding.type,
    clientAddress,
    escrowTxnId
  };
}
```

---

### Database Schema (Credit System)

```prisma
model CreditAccount {
  id              String   @id @default(uuid())
  ownerAddress    String   @unique
  apiKeyId        String
  apiKey          ApiKey   @relation(fields: [apiKeyId], references: [id])
  balance         BigInt   @default(0)
  totalDeposited  BigInt   @default(0)
  totalSpent      BigInt   @default(0)
  depositAddress  String                    // Unique deposit address for this account
  autoRefill      Boolean  @default(false)
  refillThreshold BigInt?                   // Refill when below this amount
  refillAmount    BigInt?                   // Refill to this amount
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  transactions    CreditTransaction[]
}

model CreditTransaction {
  id              String   @id @default(uuid())
  accountId       String
  account         CreditAccount @relation(fields: [accountId], references: [id])
  type            String        // 'deposit' | 'hire' | 'refund' | 'withdrawal'
  amount          BigInt        // Positive for deposits/refunds, negative for hires
  taskId          String?       // Linked task (for hire/refund)
  txnId           String?       // On-chain transaction ID (for deposits/withdrawals)
  description     String?
  createdAt       DateTime @default(now())
}

model SessionKey {
  id                  String    @id @default(uuid())
  ownerAddress        String
  sessionAddress      String    @unique
  encryptedSecretKey  String                // AES-256-GCM encrypted
  sessionToken        String    @unique     // dojo_session_xxx
  budget              BigInt                // Max spend limit
  remainingBudget     BigInt                // Current remaining
  expiresAt           DateTime
  createdAt           DateTime  @default(now())
  revokedAt           DateTime?             // Null = active
}
```

---

### Files Created (Credit System)

```
dojo-backend/src/services/creditService.ts      — Credit balance management
dojo-backend/src/services/sessionKeyService.ts  — Session key lifecycle
dojo-backend/src/routes/creditRoutes.ts         — Deposit, balance, withdraw endpoints
dojo-backend/src/routes/sessionRoutes.ts        — Session CRUD endpoints
dojo-backend/src/mcp/middleware/x402Middleware.ts — x402 payment verification for MCP
dojo-backend/src/mcp/auth.ts                    — Unified funding resolver
dojo-frontend/src/app/credits/page.tsx          — Credit dashboard (balance, history, top-up)
dojo-frontend/src/app/sessions/page.tsx         — Session management UI
```

### Files Modified (Credit System)

```
dojo-backend/src/index.ts                       — Mount credit + session routes
dojo-backend/src/services/indexerListener.ts    — Detect credit deposits
dojo-backend/src/mcp/tools/hireAgent.ts         — Use resolveFunding() before locking bounty
dojo-backend/prisma/schema.prisma               — CreditAccount, CreditTransaction, SessionKey models
```

---

### Comparison Table

| Aspect | Credit Balance | x402 Per-Call | Session Key |
|--------|:---:|:---:|:---:|
| Custodial? | Yes (platform holds funds) | No (client's wallet) | No (client's session wallet) |
| Per-call signing? | No | Yes (automatic via wrapper) | No |
| Setup complexity | Low (deposit + API key) | Medium (need x402 client) | Medium (create + fund session) |
| Best for | Human devs, Claude/Cursor | Autonomous agents | Automated pipelines |
| Blast radius if key leaked | Full balance | Per-transaction only | Session budget only |
| Refund goes to | Credit balance (off-chain) | Payer's wallet (on-chain) | Session address (on-chain) |
| Requires Algorand wallet? | Only for deposit | Yes (with private key) | Only for initial funding |
| Works with ATXP agents? | No | Yes | No |

---

*0rca Labs // Built on Algorand // 2026*
