import os
from dotenv import load_dotenv

load_dotenv()


RPCS = {
    "Base": os.getenv("BASE_RPC_URL"),
    "Arbitrum": os.getenv("ARBITRUM_RPC_URL"),
    "Ethereum": os.getenv("ETH_RPC_URL"),
    "Optimism": os.getenv("OP_RPC_URL"),
}

CHAIN_IDS = {
    "Base": 8453,
    "Arbitrum": 42161,
    "Ethereum": 1,
    "Optimism": 10,
}