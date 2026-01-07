import os
from dotenv import load_dotenv
from coinbase_agentkit import AgentKit, AgentKitConfig, CdpWalletProvider, CdpWalletProviderConfig
from coinbase_agentkit_langchain import get_langchain_tools

load_dotenv()

def debug_faucet_tool():
    print("🔍 --- DEBUGGING FAUCET VIA TOOLS ---")

    # 1. Setup Credentials
    api_key_name = os.getenv("CDP_API_KEY_NAME")
    private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY").replace('\\n', '\n')

    # 2. Init Provider (Force Base Sepolia)
    config = CdpWalletProviderConfig(
        api_key_name=api_key_name,
        api_key_private_key=private_key,
        network_id="base-sepolia" 
    )
    wallet_provider = CdpWalletProvider(config)
    
    # 3. Init AgentKit
    agent_kit = AgentKit(AgentKitConfig(wallet_provider=wallet_provider))

    # 4. Get Tools List
    tools = get_langchain_tools(agent_kit)
    print(f"🛠️  Found {len(tools)} tools.")

    # 5. Search for the Faucet Tool
    faucet_tool = None
    for tool in tools:
        if "faucet" in tool.name.lower():
            faucet_tool = tool
            print(f"✅ Found Tool: {tool.name}")
            break
    
    if not faucet_tool:
        print("❌ Faucet tool NOT found in tool list. Check network_id='base-sepolia'.")
        # Print all tools to see what IS there
        print("Available tools:", [t.name for t in tools])
        return

    # 6. FORCE EXECUTE THE TOOL
    print("🚀 Invoking Faucet Tool directly...")
    try:
        # The input argument might vary, usually it expects 'asset_id' or empty dict
        result = faucet_tool.invoke({"asset_id": "eth"}) 
        print("\n🎉 RESULT:")
        print(result)
    except Exception as e:
        print(f"\n❌ Tool Execution Failed: {e}")

if __name__ == "__main__":
    debug_faucet_tool()