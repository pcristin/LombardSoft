import requests
import time
import datetime
import hmac
import base64
from typing import Dict, Any, Optional
from utils.logger_config import logger
import json

class Bitget_API:
    """
    A class to interact with the Bitget exchange API for managing BTC withdrawals.
    """

    BASE_URL = 'https://api.bitget.com'

    def __init__(self, api_key: str, secret_key: str, passphrase: str, use_server_time: bool = True):
        """
        Initializes the BitgetAPI class.

        Args:
            api_key (str): Your Bitget API key.
            secret_key (str): Your Bitget secret key.
            passphrase (str): Your Bitget passphrase.
            use_server_time (bool): Whether to synchronize time with the server. Defaults to True.
        """
        logger.info("Initializing BitgetAPI")
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.session = requests.Session()
        self.use_server_time = use_server_time
        if self.use_server_time:
            self.server_time = self._get_server_time()
        else:
            self.server_time = datetime.datetime.now(datetime.timezone.utc).isoformat() + 'Z'

        self.session.headers.update({
            'Content-Type': 'application/json',
            'ACCESS-KEY': self.api_key,
            'ACCESS-PASSPHRASE': self.passphrase
        })
        logger.debug("BitgetAPI initialized")

    def _get_server_time(self) -> str:
        """
        Retrieves the server time from Bitget.

        Returns:
            str: The server time in ISO 8601 format.
        """
        url = f"{self.BASE_URL}/api/v2/public/time"
        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            server_time = int(data['data']['serverTime'])
            logger.debug(f"Server time retrieved: {server_time}")
            return str(server_time)
        else:
            logger.error(f"Failed to get server time: {response.text}")
            raise Exception(f"Failed to get server time: {response.text}")

    def _get_timestamp(self) -> str:
        """
        Gets the current timestamp for request signing.

        Returns:
            str: The timestamp in ISO 8601 format.
        """
        if self.use_server_time:
            return self.server_time
        else:
            return str(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))

    def _sign(self, method: str, request_path: str, body: Optional[str] = '') -> str:
        """
        Creates a signature for the request.

        Args:
            method (str): HTTP method (GET, POST, etc.).
            request_path (str): The API endpoint path.
            body (str): The request body as a JSON string.

        Returns:
            str: The base64-encoded signature.
        """
        timestamp = self._get_timestamp()
        if not body:
            message = timestamp + method.upper() + request_path
        else:
            message = timestamp + method.upper() + request_path + body
        mac = hmac.new(self.secret_key.encode('utf-8'), msg=message.encode('utf-8'), digestmod='sha256')
        d = mac.digest()
        signature = base64.b64encode(d).decode()
        logger.debug(f"Generated signature: {signature}")
        return signature

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends a signed request to the Bitget API.

        Args:
            method (str): HTTP method (GET, POST).
            path (str): API endpoint path.
            params (dict): Request parameters or payload.

        Returns:
            dict: The API response data.

        Raises:
            Exception: If the API call fails.
        """
        url = self.BASE_URL + path
        timestamp = self._get_timestamp()
        body = ''
        if params:
            body = json.dumps(params)
        else:
            body = ''

        sign = self._sign(method, path, body)
        headers = dict(self.session.headers)
        headers.update({
            'ACCESS-SIGN': sign,
            'ACCESS-TIMESTAMP': timestamp,
        })

        logger.debug(f"Making {method} request to {url} with params: {params}")
        if method.upper() == 'GET':
            response = self.session.get(url, headers=headers, params=params)
        else:
            response = self.session.post(url, headers=headers, data=body)

        logger.debug(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            response.close()
            if data.get('code') == '00000':
                logger.debug(f"Response data: {data}")
                return data
            else:
                logger.error(f"API error: {data.get('msg')}")
                raise Exception(f"API error: {data.get('msg')}")
        else:
            logger.error(f"HTTP error: {response.status_code} {response.text}")
            response.close()
            raise Exception(f"HTTP error: {response.status_code} {response.text}")


    def withdraw(self, amount: str, address: str, ccy: str, chain: str) -> Dict[str, Any]:
        """
        Withdraws funds to the specified address.

        Args:
            address (str): The withdrawal address.
            amount (str): The amount to withdraw.

        Returns:
            dict: The API response data.

        Raises:
            Exception: If the API call fails.
        """
        logger.info(f"Withdrawing {ccy}")
        match chain:
            case 'BTC':
                chain_dest = 'BITCOIN'
            case 'Optimism':
                chain_dest = 'OPTIMISM'
            case 'Base':
                chain_dest = 'BASE'
            case _:
                logger.error(f"Unsupported chain: {chain}")
        path = '/api/v2/spot/wallet/withdrawal'
        params = {
            'coin': ccy,
            'transferType': "on_chain",
            'address': address,
            'chain': chain_dest,
            'amount': amount,
        }
        logger.debug(f"Params for withdraw: {params}")
        return self._request('POST', path, params)

    def get_withdrawal_status(self, order_id: str) -> Dict[str, Any]:
        """
        Checks the status of a withdrawal transaction.

        Args:
            order_id (str): The order ID returned by the withdraw method.

        Returns:
            dict: The API response data containing withdrawal status.

        Raises:
            Exception: If the API call fails.
        """
        logger.info("Checking withdrawal status")
        path = '/api/v2/spot/wallet/withdrawal-records'
        params = {
            'orderId': order_id
        }
        logger.debug(f"Params for get_withdrawal_status: {params}")
        return self._request('GET', path, params)
