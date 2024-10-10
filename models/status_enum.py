# models/status_enum.py

from enum import Enum

class AccountStatus(Enum):
    INIT = 'Initialized'
    BTC_ADDRESS_GENERATED_WAITING = 'BTC Address Generated, Waiting for Whitelisting'
    BTC_ADDRESS_GENERATED = 'BTC Address Generated'
    BTC_DEPOSIT_INITIATED = 'BTC Deposit Initiated'
    BTC_CONFIRMATIONS_PENDING = 'Waiting for BTC Confirmations'
    CHECKING_ETH_BALANCE = 'Checking ETH Balance (Mainnet)'
    CHECKING_L2_ETH_BALANCE = 'Checking L2 ETH Balance'
    BRIDGING_FROM_L2 = 'Bridging from L2 network to Ethereum mainnet'
    WITHDRAWING_ETH_FROM_EXCHANGE = 'Withdrawing ETH from exchange'
    WITHDRAWING_ETH_FROM_EXCHANGE_CONFIRMATION = 'Waiting for ETH withdrawal confirmation'
    LBTC_MINT = 'LBTC Mint'
    LBTC_MINT_CONFIRMATION = 'LBTC Mint Confirmed'
    LBTC_RESTAKED = 'LBTC Restaked'
    LBTC_RESTAKED_CONFIRMATION = 'LBTC Restake Confirmed'
    COMPLETED = 'Process Completed'