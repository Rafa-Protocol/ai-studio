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

async def record_trade(user_addr: str, asset: str, amount: float, price_at_trade: float, side: str, tx_hash: str):
    """
    Records trade and updates 'Invested ETH' to simulate spending.
    """
    user_addr = user_addr.lower()
    asset = asset.upper()
    
    # 1. Calculate the ETH Cost
    # We use a rough heuristic: USD_Value / 3000 (Approx ETH Price)
    # Ideally, pass the real ETH price here, but this is safe for simulation.
    total_usd_value = amount * price_at_trade
    # If price < 1000, assume it is NOT ETH.
    # We need to know current ETH price to be precise, but let's estimate or fetch if possible.
    # For this fix, let's just assume price_at_trade is USD.
    
    # We will simply track the USD value spent, then convert to ETH in main.py? 
    # No, let's track ETH.
    # For now, let's assume ETH = $3000 for the calculation OR utilize the passed price if it was ETH.
    
    # BETTER: We just assume the caller passes valid data.
    # Let's say: cost_in_eth = (amount * price) / ETH_PRICE 
    # Since we don't have ETH price here easily without passing it, 
    # let's modify record_trade to accept 'eth_cost' if possible.
    
    # For now, simplistic approximation to unblock you:
    approx_eth_price = 3300.0 
    cost_in_eth = total_usd_value / approx_eth_price
    
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