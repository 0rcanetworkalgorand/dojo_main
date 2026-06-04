# Infrastructure Cost Analysis

## Current Stack (MVP / TestNet)

| Service | Provider | Monthly Cost | Notes |
|---------|----------|-------------|-------|
| Database | Supabase (Free tier) | $0 | PostgreSQL, 500MB, 2 projects |
| Backend hosting | Railway / Render (Free) | $0 | Express server, auto-sleep |
| Frontend hosting | Vercel (Free tier) | $0 | Next.js, 100GB bandwidth |
| Algorand TestNet | Algonode (Free) | $0 | Public endpoint, no rate limit |
| LLM (Groq) | Groq Free tier | $0 | Rate-limited, sufficient for demo |
| **Total MVP** | | **$0/month** | |

---

## Production Stack (MainNet, 1,000 tasks/day)

| Service | Provider | Monthly Cost | Notes |
|---------|----------|-------------|-------|
| Database | Supabase Pro | $25 | 8GB, daily backups, no pause |
| Backend | Railway Pro | $20 | Always-on, 8GB RAM |
| Frontend | Vercel Pro | $20 | Unlimited bandwidth, analytics |
| Algorand MainNet | Algonode Pro | $0 | Free public endpoint |
| On-chain txn fees | Algorand | ~$3 | 1,000 txn/day × 0.001 ALGO × $0.15 |
| LLM (Groq Pro) | Groq | $20 | Higher rate limits |
| Monitoring | Sentry Free | $0 | Error tracking |
| **Total Production** | | **~$88/month** | |

---

## Scale Stack (MainNet, 10,000 tasks/day)

| Service | Provider | Monthly Cost | Notes |
|---------|----------|-------------|-------|
| Database | Supabase Team | $599 | Dedicated compute, high IOPS |
| Backend | Railway (2 instances) | $80 | Load-balanced, 16GB RAM each |
| Frontend | Vercel Team | $150 | Edge functions, ISR |
| Algorand MainNet | Algonode + Custom indexer | $50 | Dedicated node for indexing |
| On-chain txn fees | Algorand | ~$30 | 10,000 txn/day |
| LLM | Multi-provider (Groq + OpenAI) | $200 | Fallback between providers |
| Redis (caching) | Upstash | $20 | WebSocket state, rate limiting |
| Monitoring | Sentry Team | $26 | Full APM |
| **Total Scale** | | **~$1,155/month** | |

---

## Revenue vs. Costs at Scale

| Daily Tasks | Monthly Revenue | Monthly Infra Cost | Net |
|-------------|----------------|-------------------|-----|
| 100 | $2.25 | $0 (free tier) | +$2.25 |
| 1,000 | $22.50 | $88 | -$65.50 |
| 5,000 | $112.50 | $500 | -$387.50 |
| 10,000 | $225 | $1,155 | -$930 |
| 50,000 | $1,125 | $2,500 | -$1,375 |
| 100,000 | $2,250 | $4,000 | -$1,750 |

**Break-even point**: ~200,000 tasks/day (at 5 ALGO average bounty, $0.15/ALGO)

### Path to profitability:
1. **Higher average bounties** (10-50 ALGO) reduce break-even to 20,000-100,000 tasks/day
2. **Premium tier subscriptions** ($50-200/month for Pro/Elite LLM access) add recurring revenue
3. **x402 micropayments** on MCP API access (0.01 USDC per call) adds per-request revenue
4. **Slash treasury** income (10% of staked collateral on failures) is additive

---

## Scaling Strategy

| Phase | Tasks/Day | Infra Approach |
|-------|-----------|----------------|
| MVP | 0-100 | Free tiers everywhere |
| Growth | 100-5,000 | Pro tiers, single instance |
| Scale | 5,000-50,000 | Multi-instance, dedicated DB |
| Enterprise | 50,000+ | Algorand co-chain, dedicated infra |

### Key scaling decisions:
- **Database**: Move to dedicated PostgreSQL at 5,000 tasks/day
- **Indexer**: Custom indexer node at 10,000 tasks/day (replace polling with WebSocket subscription)
- **LLM**: Multi-provider fallback at 1,000 tasks/day (Groq primary, OpenAI fallback)
- **Algorand**: Consider co-chain at 50,000+ tasks/day for dedicated throughput
