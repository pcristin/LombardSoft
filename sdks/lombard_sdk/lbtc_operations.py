# lbtc_operations.py

from web3 import Web3
from utils.logger_config import logger
import os
import json
import time
from sdks.lombard_sdk.api import LombardAPI
from models.soft_account import SoftAccount
from hexbytes import HexBytes 
import asyncio
def load_abi(filename):
    abi_path = os.path.join(os.path.dirname(__file__), 'abi', filename)
    with open(abi_path, 'r') as abi_file:
        abi = json.load(abi_file)
    return abi

class LBTCOps:
    def __init__(self, web3: Web3, account: SoftAccount):
        self.web3 = web3
        self.private_key = account.settings['private_key']
        self.account_address = self.web3.eth.account.from_key(self.private_key).address
        self.lbtc_abi = load_abi('lbtc_token_contract.json')  # Ensure the ABI file is in the 'abi' directory
        self.defi_vault_abi = load_abi('defi_vault_contract.json')
        self.lbtc_contract_address = web3.to_checksum_address('0x8236a87084f8b84306f72007f36f2618a5634494')  # Ensure address is checksummed
        self.lbtc_contract = self.web3.eth.contract(address=self.lbtc_contract_address, abi=self.lbtc_abi)
        self.defi_vault_address = web3.to_checksum_address('0x2eA43384F1A98765257bc6Cb26c7131dEbdEB9B3')  # Replace with actual vault contract address
        self.defi_vault_contract = self.web3.eth.contract(address=self.defi_vault_address, abi=self.defi_vault_abi)
        self.account = account
        logger.info(f"LBTCOps initialized for account: {self.account_address}")
        self.lombard_api = LombardAPI(
            private_key=self.private_key,
            proxy=self.account.settings.get('proxy')  # Pass the proxy if provided
        )

    def claim_lbtc(self) -> str:
        """
        Claims LBTC by calling the mint function of the LBTC token contract.

        Returns:
            str: The transaction hash of the mint transaction.

        Raises:
            Exception: If the minting fails.
        """
        logger.info("Preparing to mint LBTC")

        # Get the latest deposit data
        deposits = self.lombard_api.get_deposits_by_address()
        if not deposits:
            raise Exception("No deposits found for this account")

        # Use the latest deposit
        latest_deposit = deposits[-1]
        data = latest_deposit.get('rawPayload')
        proof_signature = latest_deposit.get('signature')

        if not data or not proof_signature:
            raise Exception("Missing data or signature in deposit information")

        # Convert data and proofSignature to bytes
        data_bytes = bytes.fromhex(data[2:])  # Remove '0x' prefix
        proof_signature_bytes = bytes.fromhex(proof_signature[2:])  # Remove '0x' prefix

        # Wait until the gas price is acceptable
        max_gas_gwei = self.account.settings.get('max_gas_gwei')
        gas_price = self.web3.eth.gas_price
        logger.info(f"Current gas price: {self.web3.from_wei(gas_price, 'gwei')} gwei")

        if max_gas_gwei:
            max_gas_wei = self.web3.to_wei(max_gas_gwei, 'gwei')
            while gas_price > max_gas_wei:
                logger.info(f"Gas price {self.web3.from_wei(gas_price, 'gwei')} gwei is higher than max allowed {max_gas_gwei} gwei. Waiting...")
                time.sleep(60)  # Wait 1 minute before checking again
                gas_price = self.web3.eth.gas_price

        # Build the transaction
        nonce = self.web3.eth.get_transaction_count(self.account_address)
        transaction = self.lbtc_contract.functions.mint(data_bytes, proof_signature_bytes).build_transaction({
            'from': self.account_address,
            'nonce': nonce,
            'gasPrice': gas_price,
            # Estimate gas
            'gas': self.lbtc_contract.functions.mint(data_bytes, proof_signature_bytes).estimate_gas({'from': self.account_address}),
        })

        # Sign the transaction
        signed_tx = self.web3.eth.account.sign_transaction(transaction, private_key=self.private_key)

        # Send the transaction
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logger.info(f"Mint transaction sent. Transaction hash: {tx_hash.hex()}")

        return tx_hash.hex()

    def confirm_mint_transaction(self, tx_hash: str):
        """
        Waits for the mint transaction to be mined and confirms its success.

        Args:
            tx_hash (str): The transaction hash of the mint transaction.

        Raises:
            Exception: If the transaction failed or was reverted.
        """
        logger.info(f"Waiting for mint transaction {tx_hash} to be mined")
        try:
            tx_hash_bytes = HexBytes(tx_hash)  # Convert tx_hash to HexBytes
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=600)  # Wait up to 10 minutes
            if receipt.get("status") == 1:
                logger.info("LBTC minting transaction confirmed successfully")
            else:
                logger.error("LBTC minting transaction failed")
                raise Exception("LBTC minting transaction failed")
        except Exception as e:
            logger.error(f"Error waiting for transaction receipt: {e}")
            raise
    
    async def approve_lbtc(self, restaking_address: str):
        """
        Approves LBTC by calling the approve function of the LBTC token contract.

        Returns:
            str: The transaction hash of the approve transaction.

        Raises:
            Exception: If the approve fails.
        """ 
        logger.info("Preparing to approve LBTC")

        # Get the latest deposit data
        amount = self.lbtc_contract.functions.balanceOf(self.account_address).call()

        if amount == 0:
            raise Exception("No LBTC balance available for restaking")

        while self.web3.eth.gas_price > self.web3.to_wei(self.account.settings.get('max_gas_gwei', 50), 'gwei'):
            logger.info("Gas price is too high. Waiting for 60 seconds")
            await asyncio.sleep(60)

        # Approve LBTC transfer to vault
        nonce = self.web3.eth.get_transaction_count(self.account_address)
        approve_tx = self.lbtc_contract.functions.approve(Web3.to_checksum_address(restaking_address), amount).build_transaction({
            'from': self.account_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': self.web3.to_wei(self.account.settings.get('max_gas_gwei', 50), 'gwei')
        })
        signed_approve_tx = self.web3.eth.account.sign_transaction(approve_tx, private_key=self.private_key)
        approve_tx_hash = self.web3.eth.send_raw_transaction(signed_approve_tx.rawTransaction)
        self.web3.eth.wait_for_transaction_receipt(approve_tx_hash)
        logger.info(f"LBTC approved for restaking. Transaction hash: {approve_tx_hash.hex()}")
        return approve_tx_hash.hex()
    
    async def restake_lbtc_defi_vault(self, restaking_address: str):
        """
        Restakes LBTC by calling the restake function of the LBTC token contract.

        Returns:
            str: The transaction hash of the restake transaction.

        Raises:
            Exception: If the restake fails.
        """
        logger.info("Preparing to restake LBTC")

        amount = self.lbtc_contract.functions.balanceOf(self.account_address).call()

        if amount == 0:
            raise Exception("No LBTC balance available for restaking")

        # Restake LBTC to vault
        nonce = self.web3.eth.get_transaction_count(self.account_address)
        while self.web3.eth.gas_price > self.web3.to_wei(self.account.settings.get('max_gas_gwei', 50), 'gwei'):
            logger.info("Gas price is too high. Waiting for 60 seconds")
            await asyncio.sleep(60)
        restake_tx = self.defi_vault_contract.functions.Deposit(
            self.lbtc_contract_address,
            amount,
            0
        ).build_transaction({
            'from': self.account_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': self.web3.to_wei(self.account.settings.get('max_gas_gwei', 50), 'gwei')
        })
        signed_restake_tx = self.web3.eth.account.sign_transaction(restake_tx, private_key=self.private_key)
        restake_tx_hash = self.web3.eth.send_raw_transaction(signed_restake_tx.rawTransaction)
        self.web3.eth.wait_for_transaction_receipt(restake_tx_hash)
        logger.info(f"LBTC restaked to vault. Transaction hash: {restake_tx_hash.hex()}")
        return restake_tx_hash.hex()
