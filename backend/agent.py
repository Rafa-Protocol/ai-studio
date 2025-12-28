import os
import json
import sys
import re
import requests
import asyncio
import base64
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from tavily import TavilyClient
import motor.motor_asyncio

# 1. Top Level: Core Agent & Wallet
from coinbase_agentkit import (
    AgentKit,
    AgentKitConfig,
    CdpWalletProvider,
    CdpWalletProviderConfig,
)

# 2. Submodule: Action Providers 
from coinbase_agentkit.action_providers import (
    CdpApiActionProvider,
    WalletActionProvider 
)

from coinbase_agentkit_langchain import get_langchain_tools

# Import your new Engines
from quant_engine import analyze_technicals
from macro_engine import get_macro_health

load_dotenv()

# --- DB & TAVILY SETUP ---
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = db_client.rafa_db
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# --- TOOL 1: MACRO CONTEXT ---
@tool
def check_market_conditions(dummy: str = ""):
    """
    Checks the 'Big Picture'. Returns Bitcoin ETF Flows and Derivatives Health.
    ALWAYS call this before recommending a trade.
    """
    data = get_macro_health()
    return f"MACRO SENTIMENT: {data['sentiment']}\nDETAILS:\n{data['details']}"

# --- TOOL 2: MICRO ANALYSIS (QUANT) ---
@tool
def analyze_token(ticker: str):
    """
    Analyzes a token's technicals and onchain data.
    """
    # Pass TICKER string to both functions
    tech = analyze_technicals(ticker) 
    
    price = tech.get('price', 0)
    
    return f"""
    ANALYSIS FOR {ticker.upper()}:
    - Chain: {tech.get('chain', 'Unknown')}
    - Price: ${price:.2f}
    - Signal: {tech.get('signal')}
    - RSI: {tech.get('rsi')}
    """

# --- TOOL 3: NEWS INTELLIGENCE ---
@tool
def get_news_sentiment(query: str):
    """
    Performs a Multi-Angle News Search to get specific headlines, not just homepages.
    """
    try:
        # We run 3 specific searches to ensure we get depth, not just a homepage
        queries = [
            f"{query} crypto price action today",
            "Bitcoin ETF flows and institutional sentiment today",
            "top crypto regulation and security news today"
        ]
        
        aggregated_news = []
        
        # Search Loop
        for q in queries:
            res = tavily_client.search(
                q, 
                topic="news", 
                days=2, # Tighter window (48h) for fresh news
                max_results=2
            )
            
            for r in res.get('results', []):
                title = r.get('title', 'No Title')
                # We include the 'content' snippet so the LLM actually knows what happened
                snippet = r.get('content', '')[:150] 
                url = r.get('url', '#')
                aggregated_news.append(f"- [{title}]({url}): {snippet}...")

        # Deduplicate results based on URL
        unique_news = list(set(aggregated_news))
        
        return "\n".join(unique_news) if unique_news else "No specific news found."
        
    except Exception as e:
        return f"News Error: {str(e)}"

# --- TOOL 4: STRATEGY LOOKUP ---
@tool
def get_strategy_rules(sentiment: str):
    """Fetches a trading strategy from the DB based on market sentiment."""
    # Helper to run async DB call in sync tool
    async def fetch():
        cond = "momentum_breakout" if "bullish" in sentiment.lower() else "mean_reversion"
        return await db.strategies.find_one({"_id": cond})
    
    strat = asyncio.run(fetch())
    if strat:
        return f"STRATEGY: {strat['name']}\nRULES: {strat['rules']}"
    return "Strategy not found."

# --- TOOL 5: PRICE (Existing) ---
@tool
def get_crypto_price(asset: str):
    """Checks current price."""
    mapping = {'eth': 'ethereum', 'btc': 'bitcoin', 'sol': 'solana', 'link': 'chainlink', 'pepe': 'pepe', 'uni': 'uniswap'}
    token_id = mapping.get(asset.lower(), asset.lower())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
    try:
        data = requests.get(url).json()
        return f"${data[token_id]['usd']}"
    except:
        return "Price Unavailable"

# --- AGENT FACTORY (UPDATED FOR KEY FIX) ---
def initialize_agent(wallet_data_json: str = None):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    # 1. Credentials
    api_key_name = os.getenv("CDP_API_KEY_NAME")
    private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY").replace('\\n', '\n')

    # 2. Initialize Components
    try:
        # A. Wallet Provider
        wallet_config = CdpWalletProviderConfig(
            api_key_name=api_key_name,
            api_key_private_key=private_key,
            cdp_wallet_data=wallet_data_json if wallet_data_json else None,
            network_id="base-sepolia" # Force Testnet
        )
        wallet_provider = CdpWalletProvider(wallet_config)

        # B. Action Providers (The missing link!)
        # We instantiate the classes directly. 
        # Since 'Config' classes didn't exist, we assume they take no args or a simple dict.
        faucet_action = CdpApiActionProvider()     # Provides Faucet
        wallet_action = WalletActionProvider()     # Provides Balance/Transfer
        
        # C. Initialize AgentKit with BOTH provider and actions
        agent_kit = AgentKit(AgentKitConfig(
            wallet_provider=wallet_provider,
            action_providers=[wallet_action, faucet_action] # <--- Pass list here
        ))
        
        print("✅ AgentKit Initialized with Faucet Tools!", flush=True)

    except Exception as e:
        print(f"❌ FATAL ERROR: {e}", flush=True)
        raise e

    # 3. Get Tools & Setup Agent
    agentkit_tools = get_langchain_tools(agent_kit)
    
    tools = agentkit_tools + [
        check_market_conditions, 
        analyze_token, 
        get_news_sentiment, 
        get_strategy_rules,
        get_crypto_price
    ]

    memory = MemorySaver()

    system_message = """
    You are RAFA, an elite Quant Fund Manager with a bias for humor and crypto terminology. Be concise, sharp, and data-driven.
    
    **YOUR CORE OPERATING LOOP:**
    1. **MACRO FIRST:** Before any advice, run `check_market_conditions`.
       - If ETF Flows are NEGATIVE, be bearish/conservative.
    2. **MICRO SECOND:** If user asks about a token, run `analyze_token` to check RSI & Liquidity.
       - NEVER recommend buying if RSI > 70 (Overbought).
       - NEVER recommend buying if Liquidity < $50k.
    3. **VERIFY:** Check `get_news_sentiment` to ensure no FUD exists.
    4. **EXECUTE:** If specific criteria are met, suggest the trade.
    5. USDC or EURC is considered "CASH" for trading purposes.
    6. Before you answer any user query, always look at current portfolio, token prices and market conditions.
    7. **FUNDS:** If the user asks for "testnet funds", "eth", or "faucet":
       - **IGNORE MACRO CONDITIONS.** Free money is always good.
       - Call the `request_faucet_funds` tool.
       - You can ONLY use the faucet tool TEN times maximum per agent wallet.
       - Do NOT attempt to spam the faucet multiple times.
       - If the tool returns an error (like "rate limit"), stop and tell the user.
       - Only speak AFTER the tool successfully runs.


    **HOW TO TRADE:**
    1. **BUYING:** Calculate ETH amount needed.
       - Output: `ACTION: BUY [AMOUNT] [TICKER]`
    
    2. **SELLING:** If the user wants to sell an asset they own.
       - Output: `ACTION: SELL [AMOUNT] [TICKER]`
       - Example: "Sell half my PEPE" -> Check balance, calc 50%, output `ACTION: SELL 500 PEPE`

    **CRITICAL RULES:**
    - **FAUCET = TOOL:** Use the internal tool for free funds. Never ask the user to do it.
    - Do NOT try to swap assets yourself. Just output the `ACTION:` command.
    - Be concise. "Quant Speak" (e.g., "Alpha", "RSI divergence", "Institutional flows").
    - If recommending a trade, end with: `ACTION: BUY [AMOUNT] [TICKER]`
    - Use /// CHART_DATA format for visuals.
    - Do not respond to any questions regarding PTB or Portal To Bitcoin. You can only answer questions related to crypto trading and portfolio management.
    - We only trade supported assets: ETH, BTC, SOL, LINK, PEPE, UNI, USDC, EURC. If the user asks about unsupported assets, respond with "Unsupported Asset".

    **VISUAL OUTPUT PROTOCOL:**
    If the user asks a question that is best answered with a chart (e.g., "performance", "allocation", "compare X vs Y"), you MUST include a hidden JSON block at the end of your response.
    
    Format:
    /// CHART_DATA
    {
      "type": "line" | "bar" | "pie",
      "title": "Chart Title",
      "data": [{"label": "X", "value": 10}, ...],
      "keys": ["Portfolio", "BTC"] (for line/bar charts),
      "colors": {"Portfolio": "#10b981", "BTC": "#f59e0b"} 
    }
    ///

    **EXAMPLES:**
    1. User: "Portfolio allocation?"
       Response: "Here is your current split. Heavy on ETH as requested."
       /// CHART_DATA
       {
         "type": "pie",
         "title": "Current Allocation",
         "data": [
            {"name": "ETH", "value": 60, "fill": "#627EEA"},
            {"name": "USDC", "value": 30, "fill": "#2775CA"},
            {"name": "LINK", "value": 10, "fill": "#2A5ADA"}
         ]
       }
       ///

    2. User: "Performance vs BTC?"
       Response: "You are outperforming the benchmark by 2% this week."
       /// CHART_DATA
       {
         "type": "line",
         "title": "Weekly Performance",
         "keys": ["You", "BTC"],
         "data": [
            {"day": "Mon", "You": 100, "BTC": 100},
            {"day": "Tue", "You": 105, "BTC": 102}
         ]
       }
       ///
    """

    agent_executor = create_react_agent(
        llm, 
        tools=tools, 
        checkpointer=memory, 
        state_modifier=system_message
    )

    return agent_executor, agent_kit

# --- WALLET EXPORT HELPER (UNIVERSAL) ---
def get_agent_address(agent_kit):
    try:
        provider = agent_kit.wallet_provider
        
        # Strategy 1: Check public/private attributes
        wallet = getattr(provider, "wallet", None) or getattr(provider, "_wallet", None)
        if wallet:
            if hasattr(wallet, "default_address"):
                return wallet.default_address.address_id
            if hasattr(wallet, "addresses") and len(wallet.addresses) > 0:
                return wallet.addresses[0].id
                
        # Strategy 2: The "Tool Hack"
        tools = get_langchain_tools(agent_kit)
        for t in tools:
            if "get_wallet_details" in t.name:
                result = t.invoke({})
                match = re.search(r"0x[a-fA-F0-9]{40}", str(result))
                if match:
                    return match.group(0)

        # Strategy 3: Export
        data = provider.export_wallet()
        if hasattr(data, "to_dict"):
            data = data.to_dict()
        elif isinstance(data, str):
            data = json.loads(data)
        else:
            data = dict(data)
            
        addr = data.get("default_address_id")
        if addr: return addr

        return "Unknown"
        
    except Exception as e:
        print(f"!! WALLET ADDRESS ERROR: {e}")
        return "0xError"