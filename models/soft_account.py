# models/soft_account.py

from typing import Dict, Any, Optional, Union
from models.status_enum import AccountStatus
from utils.logger_config import logger
from typing import Optional
from eth_account import Account

class SoftAccount:
    def __init__(self, settings: Dict[str, Any], status: Optional[AccountStatus] = None):
        """
        Initializes the SoftAccount.

        Args:
            settings (Dict[str, Any]): The account settings parsed from the Excel file.
            status (AccountStatus, optional): The current status of the account. Defaults to AccountStatus.INIT.
        """
        try:
            self.settings = settings
            self.status = status or AccountStatus.INIT
            self.btc_address = settings.get('btc_address')  # This will be updated later if generated
            self.withdrawal_id_btc: Union[str, None] = None  # For tracking BTC withdrawals
            self.transaction_hash_mint_lbtc: Union[str, None] = None  # For tracking minting blockchain transactions
            self.transaction_hash_approve_lbtc: Union[str, None] = None  # For tracking approve LBTc transactions
            self.transaction_hash_restake_lbtc: Union[str, None] = None  # For tracking restaking blockchain transactions
            self.withdrawal_id_eth: Union[str, None] = None  # For tracking ETH withdrawals
            self.transaction_hash_bridge_eth: Union[str, None] = None  # For tracking ETH blockchain transactions
            logger.debug(f"SoftAccount initialized with status {self.status}")
            self.address = Account.from_key(settings['private_key']).address
        except ValueError as e:
            logger.error(f"Error initializing accounts: {e}")
            raise  # Re-raise the exception without logging it again

    def update_status(self, new_status: AccountStatus):
        """
        Updates the account status.

        Args:
            new_status (AccountStatus): The new status to set.
        """
        logger.info(f"Updating status from {self.status} to {new_status}")
        self.status = new_status

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the account data to a dictionary for JSON serialization.

        Returns:
            Dict[str, Any]: The account data as a dictionary.
        """
        return {
            'settings': self.settings,
            'status': self.status.value,
            'btc_address': self.btc_address,
            'withdrawal_id_btc': self.withdrawal_id_btc,
            'transaction_hash_mint_lbtc': self.transaction_hash_mint_lbtc,
            'transaction_hash_approve_lbtc': self.transaction_hash_approve_lbtc,
            'transaction_hash_restake_lbtc': self.transaction_hash_restake_lbtc,
            'withdrawal_id_eth': self.withdrawal_id_eth,
            'transaction_hash_bridge_eth': self.transaction_hash_bridge_eth,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Creates a SoftAccount instance from a dictionary.

        Args:
            data (Dict[str, Any]): The account data.

        Returns:
            SoftAccount: The instantiated SoftAccount object.
        """
        settings = data['settings']
        status = AccountStatus(data['status'])
        account = cls(settings, status)
        account.btc_address = data.get('btc_address')
        account.withdrawal_id_btc = data.get('withdrawal_id_btc')
        account.transaction_hash_mint_lbtc = data.get('transaction_hash_mint_lbtc')
        account.transaction_hash_approve_lbtc = data.get('transaction_hash_approve_lbtc')
        account.transaction_hash_restake_lbtc = data.get('transaction_hash_restake_lbtc')
        account.withdrawal_id_eth = data.get('withdrawal_id_eth')
        account.transaction_hash_bridge_eth = data.get('transaction_hash_bridge_eth')
        return account