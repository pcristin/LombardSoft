# okx_api.py

from typing import Dict, Any, Union
from utils.logger_config import logger
import okx.Funding as Funding
import okx.PublicData as PublicData

class OKX_API:
    """
    A class to interact with the OKX exchange API for managing BTC withdrawals.
    """

    def __init__(self, api_key: str, secret_key: str, passphrase: str, use_server_time: bool = True):
        """
        Initializes the OKX_API class.

        Args:
            api_key (str): Your OKX API key.
            secret_key (str): Your OKX secret key.
            passphrase (str): Your OKX passphrase.
            use_server_time (bool): Whether to synchronize time with the server. Defaults to True.
        """
        logger.info("Initializing OKX_API")
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = '0'
        self.Funding = Funding.FundingAPI(self.api_key, self.secret_key, self.passphrase, False, flag=self.flag)
        self.PublicData = PublicData.PublicAPI(flag='0')
        logger.debug("OKX_API initialized")


    def get_withdrawal_fee(self,) -> Union[str, None]:
        """
        Get the withdrawal fee for a specific currency and chain.

        Args:
            currency (str): The currency code (e.g., 'BTC').
            chain (str): The chain name (e.g., 'BTC-Bitcoin').

        Returns:
            fee_res (str): The withdrawal fee.

        Raises:
            Exception: If the API call fails.
        """

        logger.info("Getting withdrawal fee")
        try:
            fee = self.Funding.get_currencies(ccy="BTC")
            if fee['code'] == '0':
                fee_res = fee['data'][0]['minFee']
            else:
                logger.error(f"Error getting withdrawal fee with code: {fee['code']} and msg: {fee['msg']}")
        except Exception as e:
            logger.error(f"Error getting withdrawal fee: {e}")
            return None
        logger.debug(f"Result for get_withdrawal_fee: {fee_res}")
        return fee_res


    def withdraw(self, amount: str, address: str,) -> Union[str, None]:
        """
        Withdraws funds to the specified address.

        Args:
            amount (str): The amount to withdraw.
            address (str): The withdrawal address.

        Returns:
            withdraw_id (str): The withdrawal ID.

        Raises:
            Exception: If the API call fails.
        """

        logger.info("Withdrawing funds")
        fee = self.get_withdrawal_fee()
        if fee is None:
            logger.info("Error getting withdrawal fee")
            return None
        try:
            withdraw_obj = self.Funding.withdrawal(ccy="BTC", amt=amount, dest='4', toAddr=address, fee=fee, chain='BTC-Bitcoin')
            logger.debug(f"Result for withdraw: {withdraw_obj}")
            if withdraw_obj['code'] == '0':
                withdraw_id = withdraw_obj['data'][0]['wdId']
                logger.info(f"Withdrawal initiated. Withdrawal ID: {withdraw_id}")
                return withdraw_id
            else:
                logger.error(f"Error withdrawing funds with code: {withdraw_obj['code']} and msg: {withdraw_obj['msg']}")
                return None
        except Exception as e:
            logger.error(f"Error withdrawing funds: {e}")
            return None

    def get_withdrawal_status(self, withdraw_id: str) -> Union[str, None]:
        """
        Checks the status of a withdrawal transaction.

        Args:
            withdrawal_id (str): The withdrawal ID returned by the withdraw method.

        Returns:
            dict: The API response data containing withdrawal status.

        Raises:
            Exception: If the API call fails.
        """
        logger.info("Checking withdrawal status")
        try:
            withdrawal_status = self.Funding.get_deposit_withdraw_status(wdId=withdraw_id)
            if withdrawal_status['code'] == '0':
                logger.info(f"Withdrawal status for wid {withdraw_id}: {withdrawal_status['data'][0]['state']}")
                return withdrawal_status['data'][0]
            else:
                logger.error(f"Error getting withdrawal status with code: {withdrawal_status['code']} and msg: {withdrawal_status['msg']}")
                return None
        except Exception as e:
            logger.error(f"Error getting withdrawal status: {e}")
            return None