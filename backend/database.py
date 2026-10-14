import motor.motor_asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client.rafa_db
users_collection = db.users

# --- USER MANAGEMENT ---

async def get_user(wallet_address: str):
    return await users_collection.find_one({"_id": wallet_address.lower()})

async def create_user(wallet_address: str, wallet_data: str, agent_address: str):
    user_doc = {
        "_id": wallet_address.lower(),
        "agent_wallet_data": wallet_data,
        "agent_address": agent_address,
        "created_at": time.time(),
        "portfolio": {}, 
        "invested_eth": 0.0,  # <--- NEW FIELD: Tracks total ETH spent on trades
        "trades": []
    }
    try:
        await users_collection.insert_one(user_doc)
        return user_doc
    except:
        return await get_user(wallet_address)

# --- TRADING & PORTFOLIO ---

# SECURITY/HYGIENE FIX: Global ETH price source. Sourced from environment
# variable at module load. This must be set in production; a value of 0
# indicates an unconfigured price and will trigger warnings in record_trade.
ETH_PRICE_FALLBACK = float(os.getenv("ETH_PRICE_USD", "0") or "0")


# --- TRADING & PORTFOLIO ---

async def record_trade(user_addr: str, asset: str, amount: float, price_at_trade: float, side: str, tx_hash: str):
    """
    Records trade and updates 'Invested ETH' to simulate spending.
    """
    user_addr = user_addr.lower()
    asset = asset.upper()
    
    # 1. Calculate the ETH Cost
    # Use configurable ETH price (from environment), not hard-coded approximation.
    total_usd_value = amount * price_at_trade
    
    # Resolve ETH price at runtime (allows direct env var or external override)
    global ETH_PRICE_FALLBACK
    if ETH_PRICE_FALLBACK <= 0:
        ETH_PRICE_FALLBACK = float(os.getenv("ETH_PRICE_USD", "0") or "0")
    
    if ETH_PRICE_FALLBACK <= 0:
        print("!! PRICE WARNING: ETH price not configured (ETH_PRICE_USD).")
        cost_in_eth = 0.0
    else:
        cost_in_eth = total_usd_value / ETH_PRICE_FALLBACK
    
    if side.upper() == "BUY":
        # Spending ETH
        inc_invested = cost_in_eth
        inc_asset = amount
    else:
        # Selling Asset (Getting ETH back)
        inc_invested = -cost_in_eth
        inc_asset = -amount

    trade_doc = {
        "asset": asset,
        "amount": amount,
        "price": price_at_trade,
        "value_usd": total_usd_value,
        "side": side,
        "tx_hash": tx_hash,
        "timestamp": time.time()
    }

    await users_collection.update_one(
        {"_id": user_addr},
        {
            "$push": {"trades": trade_doc},
            "$inc": {
                f"portfolio.{asset}": inc_asset,
                "invested_eth": inc_invested  # <--- Track the spend
            }
        }
    )
    
    print(f">> DB LOGGED: {side} {amount} {asset} (Cost: {cost_in_eth:.5f} ETH)")

async def get_portfolio_value(user_addr: str, current_prices: dict):
    user = await get_user(user_addr.lower())
    if not user: return 0.0

    total_usd = 0.0
    portfolio = user.get("portfolio", {})
    
    # We must calculate ETH value carefully now
    # But since this function just sums assets * price, it works automatically!
    # The 'portfolio.ETH' in the DB will be updated by main.py to be (Real - Invested)
    
    for asset, qty in portfolio.items():
        if qty <= 0: continue
        
        if asset == "USDC" or asset == "USDT":
            price = 1.0
        else:
            price = current_prices.get(asset.lower(), 0)
        
        total_usd += (qty * price)

    return total_usd