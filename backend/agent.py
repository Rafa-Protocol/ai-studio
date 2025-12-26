import os
import json
import requests
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from tavily import TavilyClient
import motor.motor_asyncio
from coinbase_agentkit import AgentKit, AgentKitConfig, CdpWalletProvider, CdpWalletProviderConfig

try:
    # 1. Try Top-Level Import (Newest Version)
    from coinbase_agentkit import AgentKit, AgentKitConfig, CdpWalletProvider, CdpWalletProviderConfig
    print("✅ Loaded Coinbase AgentKit from Top-Level")
except ImportError:
    try:
        # 2. Try Submodule Import (Fallback)
        from coinbase_agentkit import AgentKit, AgentKitConfig
        from coinbase_agentkit.wallet_providers import CdpWalletProvider, CdpWalletProviderConfig
        print("⚠️ Loaded Coinbase AgentKit from Submodule (wallet_providers)")
    except ImportError as e:
        # 3. DEBUG MODE: What version is actually installed?
        import coinbase_agentkit
        print(f"❌ CRITICAL IMPORT ERROR. Installed Version: {getattr(coinbase_agentkit, '__version__', 'Unknown')}")
        print(f"❌ Error Detail: {e}")
        raise e

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
    Analyzes a token's technicals and fundamentals.
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
    # (Keep your existing implementation here)
    mapping = {'eth': 'ethereum', 'btc': 'bitcoin', 'sol': 'solana', 'link': 'chainlink', 'pepe': 'pepe', 'uni': 'uniswap'}
    token_id = mapping.get(asset.lower(), asset.lower())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
    try:
        data = requests.get(url).json()
        return f"${data[token_id]['usd']}"
    except:
        return "Price Unavailable"

# --- AGENT FACTORY (UPDATED) ---

def initialize_agent(wallet_data_json: str = None):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    
    # 1. Configure Wallet Provider
    # Using CdpWalletProviderConfig to handle wallet data or ENV vars
    wallet_config = CdpWalletProviderConfig(
        cdp_wallet_data=wallet_data_json if wallet_data_json else None
    )
    wallet_provider = CdpWalletProvider(wallet_config)

    # 2. Initialize AgentKit with the provider
    agent_kit = AgentKit(AgentKitConfig(wallet_provider=wallet_provider))

    # 3. Get Tools using the new get_langchain_tools function
    agentkit_tools = get_langchain_tools(agent_kit)
    
    # REGISTER ALL TOOLS
    tools = agentkit_tools + [
        check_market_conditions, 
        analyze_token, 
        get_news_sentiment, 
        get_strategy_rules,
        get_crypto_price
    ]

    memory = MemorySaver()

    # THE QUANT SYSTEM PROMPT
    system_message = """
    You are RAFA, an elite Quant Fund Manager with a bias for humor and cyberpunk aesthetics.

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

    **HOW TO TRADE:**
    1. **BUYING:** Calculate ETH amount needed.
       - Output: `ACTION: BUY [AMOUNT] [TICKER]`
    
    2. **SELLING:** If the user wants to sell an asset they own.
       - Output: `ACTION: SELL [AMOUNT] [TICKER]`
       - Example: "Sell half my PEPE" -> Check balance, calc 50%, output `ACTION: SELL 500 PEPE`

    **CRITICAL RULES:**
    - Do NOT try to swap assets yourself. Just output the `ACTION:` command.
    - Be concise. "Quant Speak" (e.g., "Alpha", "RSI divergence", "Institutional flows").
    - If recommending a trade, end with: `ACTION: BUY [AMOUNT] [TICKER]`
    - Use /// CHART_DATA format for visuals.

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

    # Return the executor and the agent_kit (which contains the wallet provider)
    return agent_executor, agent_kit

# --- WALLET EXPORT HELPER (UPDATED) ---
def get_agent_address(agent_kit):
    try:
        # Export now returns a 'WalletData' object, not a string
        data = agent_kit.wallet_provider.export_wallet()
        
        # We must convert it to a dictionary first
        wallet_dict = data.to_dict()
        
        return wallet_dict.get("default_address_id", "Unknown")
        
    except Exception as e:
        print(f"!! WALLET EXPORT ERROR: {e}")
        return "0xError"