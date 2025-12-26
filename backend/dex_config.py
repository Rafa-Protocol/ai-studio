# dex_config.py

TRADE_REGISTRY_ADDRESS = "0xBc4CaeBadB2405f23f8B7D0A2d0387eD6c003fcc"

# Supported Assets (Base Sepolia)
TOKEN_MAP = {
    # --- BASE CHAIN ASSETS ---
    "WETH": {"address": "0x4200000000000000000000000000000000000006", "chain": "base"},
    "ETH":  {"address": "0x4200000000000000000000000000000000000006", "chain": "base"},
    "USDC": {"address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e", "chain": "base"},
    "UNI":  {"address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "chain": "base"},
    "LINK": {"address": "0xE4aB69C077896252FAFBD49EFD26B5D171A32410", "chain": "base"},
    "PEPE": {"address": "0x6982508145454Ce325dDbE47a25d4ec3d2311933", "chain": "base"},
    "BTC":  {"address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "chain": "base"},  # WBTC
    "SOL":  {"address": "So11111111111111111111111111111111111111112", "chain": "solana"} 
}


REGISTRY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "asset", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "price", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "side", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "TradeExecuted",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "_user", "type": "address"},
            {"internalType": "string", "name": "_asset", "type": "string"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "uint256", "name": "_price", "type": "uint256"},
            {"internalType": "string", "name": "_side", "type": "string"}
        ],
        "name": "recordTrade",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "_user", "type": "address"}],
        "name": "getUserTradeCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]