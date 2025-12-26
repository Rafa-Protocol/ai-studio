import time
from web3 import Web3
from dex_config import TRADE_REGISTRY_ADDRESS, REGISTRY_ABI, TOKEN_MAP

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
    # FIX: Increased Gas Limit to 500,000 to prevent 'Out of Gas' errors
    tx = contract.functions.recordTrade(
        user_sum,       
        ticker,         
        amount_wei,     
        price_wei,      
        side          
    ).build_transaction({
        'from': agent_account.address,
        'nonce': web3.eth.get_transaction_count(agent_account.address),
        'gas': 500000,  
        'maxFeePerGas': web3.to_wei('3', 'gwei'),     
        'maxPriorityFeePerGas': web3.to_wei('1.5', 'gwei'),
        'chainId': 84532 
    })

    # 5. Sign & Send
    signed_tx = web3.eth.account.sign_transaction(tx, agent_account.key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    return web3.to_hex(tx_hash)