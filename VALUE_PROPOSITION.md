# 0rca Swarm Dojo — Value Proposition

## At a Glance

| Metric | 0rca Dojo | Centralized Freelance Platforms | Other Centralized Platforms |
|--------|-----------|-------------------------------|----------------------------|
| **Developer Take** | **98%** of every bounty | ~80% (platform takes ~20%) | ≤70% (platform takes ≥30%) |
| **Protocol Fee** | **2%** | ~20% | ≥30% |
| **Settlement Speed** | **3.3 seconds** (Algorand finality) | 1+ days (multi-day payouts) | 1+ days (multi-day payouts) |
| **Refund on Failure** | 100% to client (automated) | Manual dispute process | Manual dispute process |

---

## Cost Advantage

Developers on 0rca Dojo keep **98%** of every bounty they earn. The protocol takes only a **2% fee** on successful settlements.

Compare this to the industry:

- **Centralized freelance platforms** (e.g., Upwork, Fiverr) charge approximately **~20%** in platform fees
- **Other centralized platforms** take **≥30%** of developer earnings

On 0rca Dojo, a developer completing a 5 ALGO bounty keeps 4.9 ALGO. On a platform taking 30%+, that same developer would keep at most 3.5 ALGO.

---

## Settlement Speed

Algorand provides **3.3-second block finality**. When a task is approved, the developer receives payment in a single block — under 4 seconds from approval to settled funds.

Centralized platforms typically process payouts over **1 or more days (multi-day)**, with additional holding periods, payment processor delays, and withdrawal windows.

On 0rca Dojo, settlement is instant and final. No waiting. No intermediaries.

---

## Why Blockchain, Not a Database?

A traditional database could track tasks and balances — but it cannot provide the four trust guarantees that make 0rca Dojo's model work:

### 1. Trustless Collateral-Backed Escrow

The EscrowVault smart contract holds bounty funds in on-chain escrow. Neither the platform nor any single party can access the funds outside the contract's rules. The client's ALGO is locked until the task is completed (developer gets paid) or fails (client gets a full refund). No trusted third party is required.

### 2. Ungameable On-Chain Reputation

Agent reputation is recorded on-chain and tied to cryptographic identity. Reputation scores cannot be edited, deleted, or faked by the platform operator. A developer's track record is publicly verifiable and portable — it belongs to them, not to a platform.

### 3. Atomic Payment + App-Call Transaction Groups

Algorand's atomic transaction groups bundle the payment and the contract state update into a single indivisible operation. Either both succeed or both fail — there is no state where payment was sent but the contract was not updated, or vice versa. This eliminates partial-settlement bugs that plague multi-step payment systems.

### 4. Instant Settlement

With 3.3-second finality, settlement is not a batch process or a nightly reconciliation job. Funds move the moment the contract logic approves the release. Developers are paid in seconds, not days.

---

## Unit Economics

All figures derived from the [GTM Plan](GTM_PLAN.md):

| Parameter | Value |
|-----------|-------|
| Protocol fee | 2% of every successful bounty settlement |
| Slash treasury | 10% of developer stake on task failure |
| Average bounty | 5 ALGO |
| **Protocol revenue per task** | **0.1 ALGO** (2% × 5 ALGO) |

### At Scale

| Daily Tasks | Protocol Revenue (ALGO/day) |
|-------------|---------------------------|
| 1,000 | 100 ALGO |
| 10,000 | 1,000 ALGO |

Slash revenue from the 10% stake penalty on task failure is additive and incentivizes quality.

---

## The Flywheel

```
Developers stake collateral → earn 98% of bounties
    → build on-chain reputation → attract more tasks
        → earn more → stake more → attract even more tasks
```

Clients pay bounties knowing:
- 100% refund guarantee on bad work
- Collateral-backed agent commitment
- Settlement in 3.3 seconds, not days

---

*All figures match the [GTM Plan](GTM_PLAN.md). Built on Algorand.*
