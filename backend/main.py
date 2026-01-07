import traceback
import time
import requests
import os
import re
import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

# Custom Modules
from database import get_user, create_user, record_trade, get_portfolio_value, users_collection
from agent import initialize_agent, get_agent_address
from trader import execute_swap
from dex_config import TOKEN_MAP

# --- 1. SETUP WEB3 CONNECTION ---
RPC_URL = "https://sepolia.base.org" 
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# --- 2. SETUP GLOBAL AGENT WALLET ---
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "YOUR_PRIVATE_KEY_HERE") 
try:
    if "YOUR_PRIVATE_KEY" in PRIVATE_KEY or len(PRIVATE_KEY) < 60:
        # Don't crash on local if key is missing, just warn
        print("WARNING: 'PRIVATE_KEY' not set. Real swaps will fail.")
        agent_account = None
    else:
        agent_account = Account.from_key(PRIVATE_KEY)
        print(f"INFO: Global Agent Address: {agent_account.address}")
except Exception as e:
    print(f"WARNING: Could not load Global Agent Wallet ({e}).")
    agent_account = None

app = FastAPI(title="AI Studio", description="Playground for AI Agents on Blockchain", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_CACHE = {}

PRICE_CACHE = {
    "eth": 0, "btc": 0, "sol": 0, "usdc": 1.0, "last_updated": 0
}

def update_price_cache():
    if time.time() - PRICE_CACHE["last_updated"] < 60:
        return
    try:
        ids = "ethereum,bitcoin,solana,chainlink,uniswap,compound-governance-token,aave,pepe"
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        data = requests.get(url, timeout=5).json()
        
        PRICE_CACHE["eth"] = data.get("ethereum", {}).get("usd", 0)
        PRICE_CACHE["btc"] = data.get("bitcoin", {}).get("usd", 0)
        PRICE_CACHE["sol"] = data.get("solana", {}).get("usd", 0)
        PRICE_CACHE["link"] = data.get("chainlink", {}).get("usd", 0)
        PRICE_CACHE["uni"] = data.get("uniswap", {}).get("usd", 0)
        PRICE_CACHE["comp"] = data.get("compound-governance-token", {}).get("usd", 0)
        PRICE_CACHE["aave"] = data.get("aave", {}).get("usd", 0)
        PRICE_CACHE["pepe"] = data.get("pepe", {}).get("usd", 0)
        
        PRICE_CACHE["last_updated"] = time.time()
    except Exception as e:
        print(f"!! Price fetch failed: {e}")

@app.on_event("startup")
async def startup_event():
    update_price_cache()

# --- API ENDPOINTS ---

class InitRequest(BaseModel):
    user_address: str

@app.post("/api/init-user") 
async def init_user(req: InitRequest):
    try:
        user_addr = req.user_address.lower()
        
        # 1. Try to fetch existing user
        user = await get_user(user_addr)
        
        # 2. Initialize or Retrieve Agent
        if user_addr in AGENT_CACHE:
            # Use cached agent if active
            agentkit = AGENT_CACHE[user_addr]["agentkit"]
            agent_addr = get_agent_address(agentkit)
            
            # If user didn't exist in DB but was in cache (rare), sync them
            if not user:
                wallet_data = agentkit.wallet_provider.export_wallet() if hasattr(agentkit.wallet_provider, "export_wallet") else None
                if hasattr(wallet_data, "to_dict"): wallet_data = wallet_data.to_dict()
                user = await create_user(user_addr, wallet_data, agent_addr)
        else:
            # Cold start logic
            if not user:
                # New User: Create fresh agent
                executor, agentkit = initialize_agent(wallet_data_json=None)
                wallet_data = agentkit.wallet_provider.export_wallet()
                if hasattr(wallet_data, "to_dict"): wallet_data = wallet_data.to_dict()
                
                agent_addr = get_agent_address(agentkit)
                user = await create_user(user_addr, wallet_data, agent_addr)
            else:
                # Existing User: Restore agent
                executor, agentkit = initialize_agent(user.get("agent_wallet_data"))
                agent_addr = get_agent_address(agentkit)
            
            # Cache the running instance
            AGENT_CACHE[user_addr] = {"executor": executor, "agentkit": agentkit}
        
        update_price_cache()

        # --- 3. SYNC LOGIC (HYBRID MODE) ---
        try:
            if not agent_addr or "0x" not in agent_addr:
                print(f"!! SYNC SKIPPED: Agent Address invalid ({agent_addr})")
            else:
                # Safety check for checksum
                if agent_addr != "0xError":
                    checksum_addr = Web3.to_checksum_address(agent_addr)
                    
                    # A. Get REAL Blockchain Balance
                    wei_bal = web3.eth.get_balance(checksum_addr)
                    real_eth_bal = float(web3.from_wei(wei_bal, 'ether'))
                    
                    # B. Get VIRTUAL Spend (if tracking)
                    invested_eth = user.get("invested_eth", 0.0) if user else 0.0
                    
                    # C. Calculate Display Balance
                    display_eth_bal = max(0.0, real_eth_bal - invested_eth)
                    
                    # Update DB
                    await users_collection.update_one({"_id": user_addr}, {"$set": {"portfolio.ETH": display_eth_bal}})
                    
                    # Update local variable
                    if user:
                        if "portfolio" not in user: user["portfolio"] = {}
                        user["portfolio"]["ETH"] = display_eth_bal
                
        except Exception as e:
            print(f"!! SYNC ERROR: {e}")
            traceback.print_exc()

        # --- 4. CRITICAL FIX FOR RETURN STATEMENT ---
        # If user was just created or something failed, 'user' might be None or stale.
        # We manually construct the response object to ensure stability.
        
        response_user = user if user else {
            "portfolio": {},
            "trades": []
        }
        
        total_val = await get_portfolio_value(user_addr, PRICE_CACHE)
        
        return {
            "agent_address": agent_addr,
            "portfolio": response_user.get("portfolio", {}),
            "trades": response_user.get("trades", []),
            "total_usd": total_val,
            "prices": PRICE_CACHE
        }
        
    except Exception as e:
        print(f"!! FATAL INIT ERROR: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

class StrategyRequest(BaseModel):
    user_address: str
    input: str
    thread_id: str

@app.post("/api/run-strategy") 
async def run_strategy(request: StrategyRequest):
    try:
        cmd = request.input.lower().strip()
        user_addr = request.user_address.lower()
        
        update_price_cache() 
        
        if user_addr in AGENT_CACHE:
            executor = AGENT_CACHE[user_addr]["executor"]
            agentkit = AGENT_CACHE[user_addr]["agentkit"]
        else:
            user = await get_user(user_addr)
            if not user: raise HTTPException(status_code=404, detail="User not found.")
            executor, agentkit = initialize_agent(user.get("agent_wallet_data"))
            AGENT_CACHE[user_addr] = {"executor": executor, "agentkit": agentkit}
        
        user_db = await get_user(user_addr)
        if user_db is None:
             # Fallback if DB is slow
             portfolio_str = "ETH Only"
        else:
            portfolio = user_db.get("portfolio", {})
            portfolio_str = ", ".join([f"{k}: {v:.4f}" for k, v in portfolio.items() if v > 0])
            if not portfolio_str:
                portfolio_str = "ETH Only"

        context_injection = (
            f"\n\n[SYSTEM DATA INJECTION]"
            f"\n- Live Prices: ETH=${PRICE_CACHE['eth']}, UNI=${PRICE_CACHE['uni']}, LINK=${PRICE_CACHE['link']}, SOL=${PRICE_CACHE['sol']}, PEPE=${PRICE_CACHE['pepe']}"
            f"\n- User Portfolio: {portfolio_str}" 
            f"\n[END DATA]"
        )
        
        config = {"configurable": {"thread_id": request.thread_id or "default"}}
        final_text = "..."
        
        events = executor.stream(
            {"messages": [("user", request.input + context_injection)]}, 
            stream_mode="values",
            config=config
        )
        for event in events:
            if "messages" in event:
                final_text = event["messages"][-1].content

        action_match = re.search(r"ACTION:\s*(BUY|SELL)\s*([\d\.]+)\s*(\w+)", final_text, re.IGNORECASE)
        
        if action_match:
            if agent_account is None:
                final_text += "\n\n> **EXECUTION FAILED**\n> Error: Server Wallet not configured."
                return {"result": final_text, "agent_address": get_agent_address(agentkit)}

            command = action_match.group(1).upper()
            amount = float(action_match.group(2))
            ticker = action_match.group(3).upper()
            
            if ticker in TOKEN_MAP:
                try:
                    print(f">> EXECUTING {command}: {amount} {ticker}")
                    asset_price = PRICE_CACHE.get(ticker.lower(), 0)
                    
                    tx_hash = execute_swap(
                        web3=web3, 
                        agent_account=agent_account, 
                        ticker=ticker, 
                        amount=amount, 
                        user_address=user_addr,
                        price=asset_price,
                        side=command
                    )
                    
                    await record_trade(user_addr, ticker, amount, asset_price, command, tx_hash)
                    
                    final_text += f"\n\n> **{command} CONFIRMED**\n> Asset: {ticker}\n> Amount: {amount}\n> Hash: {tx_hash}"
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"!! TRADE ERROR: {error_msg}")
                    final_text += f"\n\n> **EXECUTION FAILED**\n> Error: {error_msg}"
            else:
                final_text += f"\n\n> **ERROR**: Asset '{ticker}' not supported."

        return {
            "result": final_text,
            "agent_address": get_agent_address(agentkit)
        }
    except Exception as e:
        print(f"!! STRATEGY ERROR: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "Agent execution failed."})

@app.get("/api/agent-status")
async def agent_status():
    return {"status": "running", "prices": PRICE_CACHE}

# --- STATIC FILES (REACT HOSTING) ---
frontend_build_path = "../frontend/build"
static_dir = f"{frontend_build_path}/static"

if os.path.exists(frontend_build_path) and os.path.exists(static_dir):
    print("✅ SERVING REACT STATIC FILES")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/"):
             raise HTTPException(status_code=404, detail="API Endpoint not found")

        file_path = f"{frontend_build_path}/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        return FileResponse(f"{frontend_build_path}/index.html")
else:
    print("⚠️  DEV MODE: React Static Files NOT found (skipping mount)")