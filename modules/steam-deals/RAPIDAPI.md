# Steam Deals Tracker API — RapidAPI Listing Guide

## API Info (fill in on rapidapi.com)

**Name:** Steam Deals Tracker  
**Short Description:** Real-time Steam discount data with Chinese translations. Search, filter, and discover game deals updated daily.  
**Category:** Gaming / Data  
**Base URL:** https://yqzan.cn/steam  

**Long Description:**
```
Get daily-updated Steam discount data — perfect for price trackers, deal alert bots, game recommendation sites, and WeChat mini-programs.

✨ Features:
- Daily updated discount snapshots (auto-fetched every 6:00 AM CST)
- Search by game name, genre, discount %, and price range
- Worth index (rating × discount) to surface the best deals
- Historic low detection — know if it's the cheapest ever
- Bargain bin (games under ¥20 / ~$3)
- Chinese game name translations included
- Rate limit headers on every response

📊 Data includes:
- Game name (EN + CN), app_id, original/final price, discount %
- Steam rating %, genre tags, header image URL
- Worth index, historic low flag, bargain flag, short description

🎮 Use cases:
- Build a Steam deal notification bot
- Power a game recommendation website
- Add live discounts to your WeChat Mini Program
- Monitor price history for specific games
- Generate daily gaming deal newsletters

🔑 Free tier: 100 calls/month. Upgrade for more.
```

## Pricing Tiers

| Plan | Calls/Month | Price |
|------|:----------:|------:|
| Free | 100 | $0 |
| Basic | 1,000 | $1.49/mo |
| Pro | 5,000 | $4.49/mo |
| Unlimited | 50,000 | $19.99/mo |

## Steps to Publish on RapidAPI

1. **Go to** https://rapidapi.com/provider → Sign Up / Log In
2. **Add New API** → Click "Add API" button
3. **Upload OpenAPI Spec** → Upload `openapi.json` from this folder
4. **Set Pricing** → Configure the tiers above
5. **Test Endpoints** → RapidAPI will auto-test all endpoints
6. **Submit for Review** → Usually approved within 1-2 business days

## Important Notes

- The API uses `X-API-Key` header (RapidAPI automatically handles this for users)
- Users on RapidAPI's free plan will get your free tier
- You keep 80% of revenue (RapidAPI takes 20%)
- Payout via Stripe/PayPal after reaching $50 threshold
