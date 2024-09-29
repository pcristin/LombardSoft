# models/status_enum.py

from enum import Enum

class AccountStatus(Enum):
    INIT = 'Initialized'
    BTC_ADDRESS_GENERATED_WAITING = 'BTC Address Generated, Waiting for Whitelisting'
    BTC_ADDRESS_GENERATED = 'BTC Address Generated'
    BTC_DEPOSIT_INITIATED = 'BTC Deposit Initiated'
    BTC_CONFIRMATIONS_PENDING = 'Waiting for BTC Confirmations'
    LBTC_MINTED = 'LBTC Minted'
    LBTC_MINT_CONFIRMATION = 'LBTC Mint Confirmed'
    LBTC_RESTAKED = 'LBTC Restaked'
    LBTC_RESTAKED_CONFIRMATION = 'LBTC Restake Confirmed'
    COMPLETED = 'Process Completed'