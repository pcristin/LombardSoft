from models.soft_account import SoftAccount
from utils.logger_config import logger, AccountFilter
from utils.constants import RPCS, CHAIN_IDS
import requests
from typing import Dict, Any, Union
from web3.types import Wei, TxParams
from main import get_web3_instance
from web3 import Web3
import asyncio
import random


class RelayAPI:
    def __init__(self, account: SoftAccount, source_chain: str):
        self.account = account
        self.src_chain_name = source_chain
        self.dest_chain_name = 'Ethereum'
        self.src_chain_id = CHAIN_IDS[source_chain]
        self.dest_chain_id = CHAIN_IDS['Ethereum']
        self.src_RPC = RPCS[source_chain]
        self.dest_RPC = RPCS['Ethereum']
        self.proxy = self.account.settings['proxy']
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "*/*",
            "Content-Type": "application/json"
        })
        if self.account.settings['proxy']:
            self.session.proxies.update({
                'http': f'http://{self.proxy}',
                'https': f'http://{self.proxy}'
            })
        else:
            logger.info("No proxy provided for RelayAPI")
    
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
        url = f'https://api.relay.link{endpoint}'
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
        response.close()
        logger.debug(f"Response data: {data}")
        return data

    def get_bridge_config(self,):
        """
        Get the bridge configuration for the given source and destination chains.

        Args:
            src_chain (str): The source chain.
            dest_chain (str): The destination chain.

        Returns:
            Dict[str, Any]: The bridge configuration.
        """
        endpoint = f"/config/v2"
        params = {
            'originChainId': self.src_chain_id,
            'destinationChainId': self.dest_chain_id,
            'user': self.account.address,
            'currency': 'eth',
        }
        return self._make_request("GET", endpoint, params=params)

    def get_bridge_quote(self, amount_wei: Union[Wei, int]):
        """
        Prepare a bridge transaction for the given amount and destination address.

        Args:
            amount (int): The amount of ETH to bridge.
            to_address (str): The address to receive the ETH on the destination chain.

        Returns:
            Dict[str, Any]: The prepared bridge transaction.
        """
        endpoint = f"/quote"
        payload = {
            'user': self.account.address,
            'originChainId': self.src_chain_id,
            'destinationChainId': self.dest_chain_id,
            'originCurrency': '0x0000000000000000000000000000000000000000',
            'destinationCurrency': '0x0000000000000000000000000000000000000000',
            'amount': str(amount_wei),
            'tradeType': 'EXACT_INPUT',
            'useExternalLiquidity': False,
            'referrer': 'relay.link/swap'
        }
        return self._make_request("POST", endpoint, json=payload)
    
    async def bridge_eth(self,):
        """
        Bridge ETH from the source chain to the destination chain.

        Returns:
            TxHash: The transaction hash of the bridge transaction.
        """
        logger.info(f"Preparing to bridge ETH from {self.src_chain_name} to {self.dest_chain_name}")
        src_chain_w3 = get_web3_instance(account=self.account, chain_name=self.src_chain_name)
        
        bridge_config = self.get_bridge_config()
        amount_to_bridge = Web3.to_wei(bridge_config['user']['maxBridgeAmount'], 'wei')
        if not bridge_config:
            logger.error(f"Failed to get bridge config. Bridge config is empty")
            raise
        while True:
            # Check if bridge is enabled
            if not bridge_config['enabled']:
                logger.error(f"For this moment bridge is not enabled from {self.src_chain_name} to {self.dest_chain_name}")
                raise
            # Check if max available user's amount to bridge is greater than minimum amount to bridge
            if not self.check_capacity_per_request(bridge_config, amount_to_bridge):
                logger.error(f"User's max available bridge amount is greater than solver's capacity per request. Trying to reduce the amount")
                await asyncio.sleep(random.randint(5, 20))
                continue
            # Get bridge data
            try:
                bridge_data = self.get_bridge_quote(amount_to_bridge)
            except Exception as e:
                logger.error(f"Failed to get bridge data: {e}")
                raise
            # Check if bridge data is empty
            if not bridge_data:
                logger.error(f"Failed to get bridge data. Bridge data is empty")
                raise
            break
        logger.info(f"Starting to bridge {Web3.from_wei(amount_to_bridge, 'ether')} ETH from {self.src_chain_name} to {self.dest_chain_name}")
        received_flag = False
        estimated_time = int(bridge_data['details']['timeEstimate'])
        # Calculate gas parameters for EIP-1559 tx
        max_gas_gwei = self.account.settings['max_gas_gwei']
        if max_gas_gwei is not None:
            max_gas_gwei = int(max_gas_gwei)
        gas_price = src_chain_w3.eth.gas_price
        logger.info(f"Current gas price: {src_chain_w3.from_wei(gas_price, 'gwei')} gwei")

        if max_gas_gwei:
            max_gas_wei = src_chain_w3.to_wei(max_gas_gwei, 'gwei')
            while gas_price > max_gas_wei:
                logger.info(f"Gas price {src_chain_w3.from_wei(gas_price, 'gwei')} gwei is higher than max allowed {max_gas_gwei} gwei. Waiting...")
                await asyncio.sleep(60)  # Wait 1 minute before checking again
                gas_price = src_chain_w3.eth.gas_price

        # Calculate max fee per gas
        base_fee = src_chain_w3.eth.get_block('latest').get('baseFeePerGas')
        if not base_fee:
            raise Exception("Failed to get base fee")
        max_fee_per_gas = int(base_fee) + int(round(src_chain_w3.eth.max_priority_fee * 1.3))
        
        # Tx params
        tx_params = TxParams({
            'to':  src_chain_w3.to_checksum_address(bridge_data["steps"][0]['items'][0]['data']['to']),
            'data': bridge_data["steps"][0]['items'][0]['data']['data'],
            'nonce': src_chain_w3.eth.get_transaction_count(self.account.address),
            'maxFeePerGas': src_chain_w3.to_wei(max_fee_per_gas, 'wei'),
            'maxPriorityFeePerGas': src_chain_w3.to_wei(int(round(src_chain_w3.eth.max_priority_fee * 1.3)), 'wei'),
            'chainId': self.src_chain_id,
            'type': 2,
            'value': amount_to_bridge
        })

        tx_params['gas'] = src_chain_w3.eth.estimate_gas(tx_params)
        # Sign the transaction
        signed_tx = src_chain_w3.eth.account.sign_transaction(tx_params, private_key=self.account.settings['private_key'])

        # Send the transaction
        tx_hash = src_chain_w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.info(f"Source transaction sent. Transaction hash: 0x{tx_hash.hex()}")

        # Wait for the transaction receipt
        try:
            receipt = src_chain_w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)  # Wait up to 10 minutes
            if receipt.get("status") == 1:
                logger.info(f"Source transaction confirmed successfully. Tx hash: 0x{tx_hash.hex()}")
            else:
                logger.error("Source transaction failed")
                raise
        except Exception as e:
            logger.error(f"Error waiting for transaction receipt: {e}")
        
        # Check if bridge is successful
        endpoint = bridge_data['steps'][0]['items'][0]['check']['endpoint']
        logger.info(f"Waiting for {estimated_time} seconds to confirm bridge on {self.dest_chain_name}")
        await asyncio.sleep(estimated_time)
        for _ in range(3):
            try:
                status = self.check_dest_chain_balance(endpoint)
                if status:
                    if status['status'] == 'success':
                        received_flag = True
                        break
                    elif status['status'] == 'failure':
                        logger.error(f"Bridge failed. Status: {status['details']}")
                        break
                    elif status['status'] == 'refund':
                        logger.error(f"Bridge failed. Status: {status['status']} with details: {status['details']}")
                        break
                    else:
                        logger.info(f"The current status of bridge is {status['status']}. Waiting...")
                        await asyncio.sleep(random.randint(30, 120))
            except Exception as e:
                logger.error(f"Failed to check destination chain balance: {e}")
                raise
        if not received_flag:
            if status:
                logger.error(f"Failed to bridge ETH. Status: {status['details']}")
            else:
                logger.error(f"Failed to bridge ETH. Got no status")
            raise
        else:
            logger.info(f"Successfully bridged {Web3.from_wei(amount_to_bridge, 'ether')} ETH from {self.src_chain_name} to {self.dest_chain_name}. Tx hash: 0x{tx_hash.hex()}")
            return f"0x{tx_hash.hex()}"

    def check_dest_chain_balance(self, endpoint: str):
        """
        Check if user's balance is greater than required balance.

        Args:
            endpoint (str): The endpoint to check.

        Returns:
            bool: True if user's balance is greater than required balance, False otherwise.
        """
        status = self._make_request("GET", endpoint)
        return status
    
    def get_price(self,):
        """
        Get the price of the bridge.

        Returns:
            float: The price of the bridge.
        """
        return self._make_request("GET", "/price")
    
    def check_capacity_per_request(self, bridge_config: Dict[str, Any], amount_to_bridge: Union[Wei, int]):
        """
        Check if user's balance is greater than solver's capacity per request.

        Args:
            bridge_config (Dict[str, Any]): The bridge configuration.

        Returns:
            bool: True if user's balance is greater than solver's capacity per request, False otherwise.
        """
        return Web3.to_wei(bridge_config['solver']['capacityPerRequest'], 'wei') > amount_to_bridge
    