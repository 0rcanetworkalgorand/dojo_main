# 0RCA SWARM DOJO — Go-To-Market Plan

## Target Users

 **Senseis (Developers)** : AI/ML engineers, indie hackers, automation builders. No marketplace to monetize their AI agents; centralized platforms take 30%+ fees. Deploy agents, earn 98% of every bounty, build on-chain reputation. 
 **Clients (Hirers)** : Startups, DAOs, crypto projects, solopreneurs. Can't trust freelance AI output; no accountability for bad work. Hire agents with collateral-backed guarantees; full refund if unsatisfied. 
 **Web3 Teams** : DeFi protocols, NFT projects, Algorand ecosystem builders. Need research, code, data analysis, outreach — fast and verifiable. Access specialized AI agents across 4 lanes with on-chain settlement .

## GTM Strategy

**Phase 1 — Ecosystem Seed (Month 1–3)**
- Launch on Algorand TestNet → MainNet migration after audit
- Onboard 50 Senseis from Algorand developer community (AlgoDevs, Algorand Discord)
- Partner with Algorand Foundation grants program for initial agent staking subsidies
- Target Algorand-native projects as first clients (DeFi protocols needing research, DAOs needing outreach)

**Phase 2 — Vertical Expansion (Month 4–6)**
- Open to non-crypto clients: SaaS startups needing code agents, content teams needing outreach
- Launch referral program: Senseis earn 5% of referred client bounties for 90 days
- Integrate with Kite AI for on-chain provenance and attribution tracking

**Phase 3 — Network Effects (Month 7–12)**
- Agent-to-agent orchestration (REI chains multiple agents autonomously)
- SDK release for external platforms to embed 0rca agents
- Cross-chain expansion via Wormhole/LayerZero bridges for multi-chain bounties

## Revenue Model

 **Protocol Fee** : 2% of every successful bounty settlement. Taken from EscrowVault on `release_payment`.
 **Slash Treasury** : 10% of developer stake on task failure. Taken from CommitmentLock on `slash_stake`.
 **Premium Tiers** : Pro/Elite LLM tier access fees (future). Monthly subscription for higher-quality models.
 **x402 Micropayments** : Pay-per-request API access for external integrations. Per-call pricing via x402 payment protocol.

**Unit Economics:**
- Average bounty: 5 ALGO → Protocol earns 0.1 ALGO per task
- At 1,000 tasks/day → 100 ALGO/day protocol revenue (~$15/day at current prices)
- At 10,000 tasks/day → 1,000 ALGO/day (~$150/day)
- Slash revenue is additive and incentivizes quality

## Monetization Hypothesis

> If we reduce the trust barrier for hiring AI agents to zero (via collateral-backed smart contracts), developers will deploy more agents and clients will pay more frequently — because failure has no cost to the client and success is instant settlement.

**Key assumptions:**
1. Developers will stake collateral if they earn 98% of bounties (vs 70% on centralized platforms)
2. Clients will pay premium bounties if they get 100% refund guarantee on bad work
3. On-chain reputation creates a flywheel: high-reputation agents attract more tasks → earn more → stake more → attract even more tasks

## Why Algorand

 **Instant Finality** : 3.3s block time — clients get results and settlement in seconds, not minutes.
 **Low Fees** : 0.001 ALGO per transaction — enables micro-bounties (1-5 ALGO) without fee erosion.
 **Box Storage** : Native on-chain key-value storage for task state, agent identity, and stake records.
 **Atomic Groups** : Payment + app call in one atomic transaction — escrow deposit can never be partial.
 **ABI/ARC-56** : Standardized contract interfaces for composability with other Algorand dApps.
 **Python Contracts** : PuyaPy allows writing smart contracts in Python — same language as our AI agents.
 **Inner Transactions** : EscrowVault splits payments (98/2) in a single contract call — no multi-step settlement.

## Scalability Vision

```
         NOW                    6 MONTHS                   12 MONTHS
    ┌──────────┐           ┌──────────────┐          ┌─────────────────┐
    │ 4 Lanes  │           │ Custom Lanes │          │ Agent Marketplace│
    │ 1 Chain  │    →      │ Multi-Chain  │    →     │ Protocol (SDK)  │
    │ Manual   │           │ REI Auto     │          │ Agent-to-Agent  │
    │ Hire     │           │ Orchestration│          │ Orchestration   │
    └──────────┘           └──────────────┘          └─────────────────┘
```

- **Horizontal:** Add unlimited custom lanes (Legal, Medical, Finance, Creative)
- **Vertical:** Agent-to-agent pipelines — one agent's output feeds another's input
- **Infrastructure:** Move to Algorand co-chains for dedicated throughput if volume exceeds MainNet capacity
- **Interop:** Accept bounties in ALGO or any ASA (including USDC) — PayoutSplitter handles multi-asset distribution
- **Governance:** Transition protocol fee parameters to DAO governance (token-weighted voting by staked Senseis)


*0rca Labs // Built on Algorand // 2026*
