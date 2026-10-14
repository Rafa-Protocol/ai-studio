import os
import time
from web3 import Web3
from dex_config import TRADE_REGISTRY_ADDRESS, REGISTRY_ABI, TOKEN_MAP

# --- CONFIGURATION (FROM ENVIRONMENT, NOT HARD-CODED) ---
# These values SHOULD be overridden in production via environment variables.
# Hard-coded fallbacks are provided ONLY as local development defaults and
# MUST NOT be used on mainnet or testnet without explicit review.
GAS_LIMIT_DEFAULT = int(os.getenv("TRADE_GAS_LIMIT", "500000"))
MAX_FEE_PER_GAS_GWEI = int(os.getenv("MAX_FEE_PER_GAS_GWEI", "3"))
MAX_PRIORITY_FEE_PER_GWEI = int(os.getenv("MAX_PRIORITY_FEE_PER_GWEI", "1.5"))
CHAIN_ID = int(os.getenv("CHAIN_ID", "84532"))  # Base Sepolia

def execute_swap(web3: Web3, agent_account, ticker: str, amount: float, user_address: str, price: float, side: str = "BUY"):
    """
    Records a trade on the RafaTradeRegistry contract.
    """
    # 1. Validation
    ticker = ticker.upper()
    if ticker not in TOKEN_MAP:
        raise ValueError(f"Asset {ticker} not supported.")

    # 2. Setup Contract
    registry_sum = Web3.to_checksum_address(TRADE_REGISTRY_ADDRESS)
    contract = web3.eth.contract(address=registry_sum, abi=REGISTRY_ABI)
    
    # 3. Prepare Data
    amount_wei = int(amount * 10**18) 
    price_wei = int(price * 10**18) 
    
    try:
        user_sum = Web3.to_checksum_address(user_address)
    except:
        raise ValueError(f"Invalid User Address: {user_address}")

    print(f">> RECORDING ON-CHAIN: {user_sum} {ticker} {amount} @ ${price}")

    # 4. Build Transaction
    # Configuration values are sourced from environment variables with
    # safe local development defaults. Review before production use.
    tx = contract.functions.recordTrade(
        user_sum,
        ticker,
        amount_wei,
        price_wei,
        side
    ).build_transaction({
        'from': agent_account.address,
        'nonce': web3.eth.get_transaction_count(agent_account.address),
        'gas': GAS_LIMIT_DEFAULT,
        'maxFeePerGas': web3.to_wei(str(MAX_FEE_PER_GAS_GWEI), 'gwei'),
        'maxPriorityFeePerGas': web3.to_wei(str(MAX_PRIORITY_FEE_PER_GWEI), 'gwei'),
        'chainId': CHAIN_ID
    })

    # 5. Sign & Send
    signed_tx = web3.eth.account.sign_transaction(tx, agent_account.key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    return web3.to_hex(tx_hash)