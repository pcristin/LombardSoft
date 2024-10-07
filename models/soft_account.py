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
            self.btc_withdrawal_id: Union[str, None] = None  # For tracking BTC withdrawals
            self.transaction_hash_mint: Union[str, None] = None  # For tracking mint LBTC transactions
            self.transaction_hash_approve_lbtc: Union[str, None] = None # For tracking approval LBTC transactions
            self.transaction_hash_restake: Union[str, None] = None # For tracking restake LBTC transactions
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
            'btc_withdrawal_id': self.btc_withdrawal_id,
            'transaction_hash_mint': self.transaction_hash_mint,
            'transaction_hash_approve_lbtc': self.transaction_hash_approve_lbtc,
            'transaction_hash_restake': self.transaction_hash_restake
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
        account.btc_withdrawal_id = data.get('btc_withdrawal_id')
        account.transaction_hash_mint = data.get('transaction_hash_mint')
        account.transaction_hash_approve_lbtc = data.get('transaction_hash_approve_lbtc')
        account.transaction_hash_restake = data.get('transaction_hash_restake')
        return account
