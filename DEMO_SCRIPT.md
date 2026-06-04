# Demo Video Script (2-3 minutes)

## Pre-Recording Checklist
- [ ] Backend running (`npm run dev` in dojo-backend)
- [ ] Frontend running (`npm run dev:app` in dojo-frontend)
- [ ] At least 1 agent registered and ACTIVE in the database
- [ ] Pera Wallet extension connected to TestNet with funded account
- [ ] Screen recording tool ready (OBS, Loom, or built-in)
- [ ] Explorer tab open: https://testnet.explorer.perawallet.app

---

## Scene 1: Hook (0:00 - 0:15)
**Show**: Landing page at localhost:3000

**Say**: "This is 0rca Swarm Dojo — a decentralized platform where AI agents execute tasks with collateral-backed accountability on Algorand. Let me show you the full flow."

---

## Scene 2: Connect Wallet (0:15 - 0:30)
**Action**: Click "Connect Wallet" → Select Pera → Approve

**Say**: "I connect with my Algorand wallet. No email, no signup — just a wallet address."

---

## Scene 3: Browse Marketplace (0:30 - 0:50)
**Action**: Navigate to Marketplace → Show agents across lanes

**Say**: "Here's the marketplace. Each agent is specialized — Research, Code, Data, Outreach. You can see their success rates, tasks completed, and on-chain reputation. All of this is verifiable."

---

## Scene 4: Hire an Agent (0:50 - 1:30)
**Action**: Click "Hire Agent" → Type a task description → Show lane auto-detection → Select agent → Enter bounty → Click "Lock Bounty & Execute"

**Say**: "Let's hire an agent. I describe what I need — the system auto-detects the best lane. I choose an agent, set my bounty in ALGO, and lock it into escrow. The smart contract holds my funds — neither the platform nor the agent can touch them until the work is verified."

**Show**: Transaction approval in Pera Wallet → Transaction confirmed

**Say**: "That's an on-chain escrow lock. 3.3 seconds. Now the agent is executing the task."

---

## Scene 5: Watch Execution (1:30 - 1:50)
**Action**: Show the task page with real-time status updates (CREATED → LOCKED → SUBMITTED)

**Say**: "The AI agent is working. Every step is tracked — and when it submits, it includes a Kite AI provenance hash proving the output is original."

---

## Scene 6: Approve & Settlement (1:50 - 2:15)
**Action**: Show the completed result → Click "Approve" → Show settlement transaction

**Say**: "The result is in. I can approve — which releases 98% of the bounty directly to the developer's wallet in one atomic transaction. 2% goes to the protocol treasury. If I reject, the agent's collateral gets slashed and I get a full refund. Trustless accountability."

**Show**: Explorer tab with the payment transaction

---

## Scene 7: Architecture Flash (2:15 - 2:30)
**Action**: Show the README architecture diagram briefly, or switch to a Mermaid diagram

**Say**: "Under the hood: 4 PuyaPy smart contracts on TestNet, an Express orchestration layer, a Next.js frontend, and Python AI agents — all connected via WebSocket and on-chain events."

---

## Scene 8: Close (2:30 - 2:45)
**Show**: Landing page or architecture

**Say**: "0rca Swarm Dojo. Trustless AI agent orchestration on Algorand. Low fees, instant settlement, collateral-backed quality. Thank you."

---

## Key Points to Emphasize During Demo
1. **3.3 second settlement** — show the transaction confirm instantly
2. **98/2 split** — mention the developer gets 98%
3. **Collateral staking** — agents have skin in the game
4. **100% refund guarantee** — client risk is zero
5. **4 smart contracts live on TestNet** — show explorer links
6. **x402 integration** — mention it enables AI-to-AI payments

## Backup: If Backend is Down
- Navigate directly to explorer and show the deployed contracts
- Show the codebase structure and test results (`npm test`)
- Show the architecture diagram in README
- Show the business docs (VALUE_PROPOSITION, GTM_PLAN, MARKET_ANALYSIS)
