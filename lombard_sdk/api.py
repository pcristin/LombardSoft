# api.py

import requests
import logging
from eth_account import Account
from eth_account.messages import encode_defunct
from typing import List, Dict, Any, Optional
from .constants import TESTNET_BASE_URL, CHAIN_ID, REFERRAL_ID, MAINNET_BASE_URL

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler
file_handler = logging.FileHandler('lombard_api.log')
file_handler.setLevel(logging.DEBUG)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class LombardAPI:
    """
    A class to handle API-based operations for Lombard Finance.
    """

    def __init__(self, private_key: str, chain_id: int = CHAIN_ID, referral_id: str = REFERRAL_ID, base_url: str = TESTNET_BASE_URL):
        """
        Initializes the LombardAPI class.

        Args:
            private_key (str): Private key of the user's Ethereum account.
            chain_id (int, optional): The chain ID (1 for Ethereum Mainnet). Defaults to CHAIN_ID.
            referral_id (str, optional): Referral ID. Defaults to REFERRAL_ID.
            base_url (str, optional): Base URL for the Lombard API. Defaults to TESTNET_BASE_URL/MAINNET_BASE_URL.
        """
        logger.info("Initializing LombardAPI")
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.chain_id = chain_id
        self.referral_id = referral_id
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
            })
        logger.debug(f"LombardAPI initialized with address: {self.address}, chain_id: {self.chain_id}")
        self.base_url = base_url

    def _generate_signature(self) -> str:
        """
        Generates a signature for the given message using the user's private key.

        Args:
            message (str): The message to sign.

        Returns:
            str: The signature as a hexadecimal string.
        """
        message = f"destination chain id is {self.chain_id}"
        logger.debug(f"Generating signature for message: {message}")
        message_encoded = encode_defunct(text=message)
        logger.debug(f"Message encoded: {message_encoded.body.hex()}")
        signed_message = self.account.sign_message(message_encoded)
        signature = signed_message.signature.to_0x_hex()
        logger.debug(f"Generated signature: {signature}")
        return signature

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an API request and handle common error cases.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            endpoint (str): The API endpoint to call.
            **kwargs: Additional keyword arguments to pass to the request.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        url = f'{self.base_url}{endpoint}'
        logger.debug(f"Making {method} request to {url}")
        logger.debug(f"Request kwargs: {kwargs}")
        response = self.session.request(method, url, **kwargs)
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        if response.status_code != 200:
            logger.error(f"Request failed with status code {response.status_code}")
            logger.error(f"Response text: {response.text}")
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response data: {data}")
        return data

    def generate_deposit_btc_address(self) -> str:
        """
        Generates a new BTC deposit address for the user's Ethereum address.

        Returns:
            str: The newly generated BTC deposit address.

        Raises:
            Exception: If the API call fails.
        """
        logger.info("Generating new BTC deposit address")
        self.session.headers.update({
        })
        signature = self._generate_signature()

        payload = {
            "captcha_token": "0",
            "nonce": "0",
            "referral_id": self.referral_id,
            "to_address": self.address,
            "to_address_signature": signature,
            "to_chain": "DESTINATION_BLOCKCHAIN_ETHEREUM"
        }
        logger.debug(f"Payload for generate_deposit_btc_address: {payload}")
        try: 
            data = self._make_request('POST', '/api/v1/address/generate', json=payload)
            btc_address = data['address']
            logger.info(f"Generated BTC deposit address: {btc_address}")
            return btc_address
        except Exception as e:
            logger.error(f"Error generating BTC deposit address: {e}")
            return None

    def get_deposit_btc_address(self) -> Optional[str]:
        """
        Retrieves the BTC deposit address associated with the user's Ethereum address.

        Returns:
            Optional[str]: The BTC deposit address if exists, else None.

        Raises:
            Exception: If the API call fails.
        """
        logger.info("Retrieving BTC deposit address")
        params = {
                "to_address": self.address,
                "to_blockchain": "DESTINATION_BLOCKCHAIN_ETHEREUM",
                "limit": "1",
                "offset": "0",
                "asc": "false",
                "referral_id": self.referral_id
        }
        logger.debug(f"Params for get_deposit_btc_address: {params}")
        try:
            data = self._make_request('GET', '/api/v1/address', params=params)
            if not data:
                logger.warning("No BTC deposit address found")
                return None
            btc_address = data['addresses'][0]['btc_address']
            logger.info(f"Retrieved BTC deposit address: {btc_address}")
            return btc_address
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("No BTC deposit address found")
                return None
            logger.error(f"HTTP error occurred: {e}")
            raise

    def get_deposit_btc_addresses(self) -> List[str]:
        """
        Retrieves all BTC deposit addresses associated with the user's Ethereum address.

        Returns:
            List[str]: A list of BTC deposit addresses.

        Raises:
            Exception: If the API call fails.
        """
        logger.info("Retrieving all BTC deposit addresses")
        params = {
                "to_address": self.address,
                "to_blockchain": "DESTINATION_BLOCKCHAIN_ETHEREUM",
                "limit": "1",
                "offset": "0",
                "asc": "false",
                "referral_id": self.referral_id
        }
        logger.debug(f"Params for get_deposit_btc_addresses: {params}")
        data = self._make_request('GET', '/api/v1/addresses', params=params)
        addresses = data['addresses'][0]['btc_address']
        logger.info(f"Retrieved {len(data['addresses'])} BTC deposit address")
        logger.debug(f"BTC deposit addresses: {addresses}")
        return addresses

    def get_deposits_by_address(self) -> List[Dict[str, Any]]:
        """
        Retrieves BTC deposits associated with the user's Ethereum address.

        Returns:
            List[Dict[str, Any]]: A list of deposit records.

        Raises:
            Exception: If the API call fails.
        """
        logger.info("Retrieving BTC deposits")
        data = self._make_request('GET', f'/api/v1/deposits/{self.address}/{self.chain_id}')
        deposits = data.get('deposits', [])
        logger.info(f"Retrieved {len(deposits)} BTC deposits")
        logger.debug(f"BTC deposits: {deposits}")
        return deposits

    def get_lbtc_exchange_rate(self) -> float:
        """
        Retrieves the current LBTC exchange rate.

        Returns:
            float: The LBTC exchange rate.

        Raises:
            Exception: If the API call fails.
        """
        logger.info("Retrieving LBTC exchange rate")
        params = {
            "amount": "1"
        }
        data = self._make_request('GET', '/api/v1/exchange/rate/DESTINATION_BLOCKCHAIN_ETHEREUM', params=params)
        exchange_rate = float(data['amount_out'])
        logger.info(f"Retrieved LBTC exchange rate: {float(params['amount'])} = {exchange_rate} LBTC")
        return exchange_rate

    def set_proxy(self, proxies: Dict[str, str]):
        """
        Sets proxy configuration for the session.

        Args:
            proxies (Dict[str, str]): A dictionary of proxy settings.
        """
        logger.info("Setting proxy configuration")
        logger.debug(f"Proxy settings: {proxies}")
        self.session.proxies.update(proxies)
        logger.info("Proxy configuration updated")
