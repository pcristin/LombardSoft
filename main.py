# main.py

import os
import json
import random
import time
from models import UserSettingsParser
from utils.logger_config import logger
from models.status_enum import AccountStatus
from models.soft_account import SoftAccount
from sdks.lombard_sdk.api import LombardAPI
from sdks.exchanges_sdk.okx_api import OKX_API
from sdks.exchanges_sdk.bitget_api import Bitget_API
from web3 import Web3, HTTPProvider
from sdks.lombard_sdk.lbtc_operations import LBTCOps
from typing import Optional
import requests
from hexbytes import HexBytes
import pandas as pd
from openpyxl import load_workbook

PROVIDER_URL = "" # ETHEREUM_RPC_URL

def get_web3_instance(account: SoftAccount) -> Web3:
    """
    Initializes a Web3 instance, optionally using a proxy.

    Args:
        account (SoftAccount): The account object containing settings.

    Returns:
        Web3: The initialized Web3 instance.
    """
    provider_url = PROVIDER_URL
    proxy = account.settings.get('proxy')
    if proxy:
        logger.info(f"Setting proxy for Web3: {proxy}")
        # Configure HTTPProvider with proxy
        session = requests.Session()
        proxies = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        session.proxies.update(proxies)
        provider = HTTPProvider(provider_url, session=session)
        web3 = Web3(provider)
    else:
        logger.info("No proxy provided for Web3")
        web3 = Web3(Web3.HTTPProvider(provider_url))
    return web3

def generate_btc_address(account: SoftAccount) -> str:
    logger.info("Generating BTC address")
    lombard_api = LombardAPI(
        private_key=account.settings['private_key'],
        chain_id=account.settings.get('chain_id', 1),  # Default to 1 if not specified
        referral_id=account.settings.get('referral_id', 'lombard'),
        base_url=account.settings.get('base_url', 'https://mainnet.prod.lombard.finance'),  # Adjust as needed
        proxy=account.settings.get('proxy')  # Pass the proxy
    )
    btc_address = lombard_api.generate_deposit_btc_address()
    if btc_address:
        # Update the account's BTC address
        account.btc_address = btc_address
        # Update the settings to include the generated BTC address
        account.settings['btc_address'] = btc_address
        logger.info(f"Generated BTC address: {btc_address}")
        return btc_address
    else:
        raise Exception("Failed to generate BTC address")

def deposit_btc(account: SoftAccount):
    logger.info("Initiating BTC deposit")
    exchange_name = account.settings['exchange']
    # Randomly generate BTC amount between min_BTC and max_BTC
    amount = random.uniform(account.settings['min_BTC'], account.settings['max_BTC'])
    amount = round(amount, 8)  # BTC has up to 8 decimal places
    amount_str = format(amount, '.8f')
    btc_address = account.btc_address

    if exchange_name == 'OKX':
        # Initialize OKX API
        exchange_api = OKX_API(
            api_key=account.settings['exchange_api_key'],
            secret_key=account.settings['exchange_secret_key'],
            passphrase=account.settings['exchange_passphrase']
        )
        # Withdraw BTC
        if btc_address:
            withdrawal_id = exchange_api.withdraw(amount=amount_str, address=btc_address)
        else:
            raise ValueError("BTC address cannot be None")
    elif exchange_name == 'Bitget':
        # Initialize Bitget API
        exchange_api = Bitget_API(
            api_key=account.settings['exchange_api_key'],
            secret_key=account.settings['exchange_secret_key'],
            passphrase=account.settings['exchange_passphrase']
        )
        # Withdraw BTC
        if btc_address:
            withdrawal_id = exchange_api.withdraw(amount=amount_str, address=btc_address)
        else:
            raise ValueError("BTC address cannot be None")
    else:
        raise Exception(f"Unsupported exchange: {exchange_name}")

    if withdrawal_id:
        account.withdrawal_id = {"withdrawal_id": withdrawal_id}
        logger.info(f"BTC withdrawal initiated. Withdrawal ID: {withdrawal_id}")
    else:
        raise Exception("Failed to initiate BTC withdrawal")

def wait_for_confirmations(account: SoftAccount):
    logger.info("Waiting for BTC deposit confirmations")
    lombard_api = LombardAPI(
        private_key=account.settings['private_key'],
        proxy=account.settings.get('proxy')  # Pass the proxy
    )
    max_confirmations = 6
    check_interval = 300  # Check every 5 minutes
    max_checks = 72  # Wait up to 6 hours

    for _ in range(max_checks):
        deposits = lombard_api.get_deposits_by_address()
        if deposits:
            for deposit in deposits:
                if deposit['btc_address'] == account.btc_address:
                    confirmations = deposit.get('confirmations', 0)
                    logger.info(f"Deposit confirmations: {confirmations}")
                    if confirmations >= max_confirmations:
                        logger.info("Required confirmations reached")
                        return
        else:
            logger.info("No deposits found yet")

        time.sleep(check_interval)

    raise Exception("Timed out waiting for BTC deposit confirmations")

def mint_lbtc(account: SoftAccount):
    logger.info(f"Minting LBTC for account: {account.address}")
    web3 = get_web3_instance(account)

    lbtc_ops = LBTCOps(web3=web3, account=account)
    tx_hash = lbtc_ops.claim_lbtc()

    if tx_hash:
        account.transaction_hash = {"hash": tx_hash}  # Wrap tx_hash in a dictionary    
        logger.info(f"LBTC mint transaction initiated. Transaction hash: {tx_hash}")
    else:
        raise Exception("Failed to mint LBTC")

def confirm_lbtc_mint(account: SoftAccount):
    logger.info("Confirming LBTC minting transaction")
    web3 = get_web3_instance(account)

    tx_hash = account.transaction_hash
    if not tx_hash:
        raise Exception("No transaction hash found for LBTC minting")

    # Ensure tx_hash is a string or bytes
    if isinstance(tx_hash, dict):
        tx_hash = tx_hash['hash']  # Extract the hash if tx_hash is a dictionary
    tx_hash_bytes = HexBytes(tx_hash)  # Ensure tx_hash is in a compatible format
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=600)
    if receipt["status"] == 1:
        logger.info("LBTC minting transaction confirmed")
    else:
        raise Exception("LBTC minting transaction failed")

# def restake_lbtc(account: SoftAccount):
#     logger.info("Restaking LBTC")
#     selected_vault = account.settings['selected_vault']
#     web3 = get_web3_instance(account)

#     if selected_vault == 'Defi_Vault':
#         tx_hash = restake_to_defi_vault(web3, account)
#     elif selected_vault == 'Etherfi':
#         tx_hash = restake_to_etherfi(web3, account)
#     elif selected_vault == 'Pendle':
#         tx_hash = restake_to_pendle(web3, account)
#     else:
#         raise Exception(f"Unknown vault: {selected_vault}")

#     if tx_hash:
#         account.transaction_hash = {"hash": tx_hash}  # Wrap tx_hash in a dictionary
#         logger.info(f"LBTC restake transaction initiated. Transaction hash: {tx_hash}")
#     else:
#         raise Exception("Failed to restake LBTC")

# def confirm_restake(account: SoftAccount):
#     logger.info("Confirming LBTC restake transaction")
#     web3 = get_web3_instance(account)

#     tx_hash = account.transaction_hash
#     if not tx_hash:
#         raise Exception("No transaction hash found for LBTC restaking")

#     tx_hash_bytes = HexBytes(tx_hash)  # Ensure tx_hash is in a compatible format
#     receipt = web3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=600)
#     if receipt["status"] == 1:
#         logger.info("LBTC restaking transaction confirmed")
#     else:
#         raise Exception("LBTC restaking transaction failed")

# def restake_to_defi_vault(web3: Web3, account: SoftAccount) -> Optional[str]:
#     logger.info("Restaking LBTC to Defi_Vault")
#     private_key = account.settings['private_key']
#     account_address = web3.eth.account.from_key(private_key).address

#     lbtc_token_address = '0xYourLBTCContractAddress'  # Replace with actual LBTC contract address
#     defi_vault_address = '0xDefiVaultContractAddress'  # Replace with actual vault contract address

#     # Load ABIs
#     lbtc_abi = load_abi('lbtc_token_contract.json')
#     vault_abi = load_abi('defi_vault_contract.json')

#     # Create contract instances
#     lbtc_contract = web3.eth.contract(address=web3.to_checksum_address(lbtc_token_address), abi=lbtc_abi)
#     vault_contract = web3.eth.contract(address=web3.to_checksum_address(defi_vault_address), abi=vault_abi)

#     # Amount to restake (adjust as needed)
#     amount = lbtc_contract.functions.balanceOf(account_address).call()

#     if amount == 0:
#         raise Exception("No LBTC balance available for restaking")

#     # Approve LBTC transfer to vault
#     nonce = web3.eth.get_transaction_count(account_address)
#     approve_tx = lbtc_contract.functions.approve(defi_vault_address, amount).build_transaction({
#         'from': account_address,
#         'nonce': nonce,
#         'gas': 100000,
#         'gasPrice': web3.to_wei(account.settings.get('max_gas_gwei', 50), 'gwei')
#     })
#     signed_approve_tx = web3.eth.account.sign_transaction(approve_tx, private_key=private_key)
#     approve_tx_hash = web3.eth.send_raw_transaction(signed_approve_tx.rawTransaction)
#     web3.eth.wait_for_transaction_receipt(approve_tx_hash)


# def restake_to_etherfi(web3: Web3, account: SoftAccount) -> Optional[str]:
#     logger.info("Restaking LBTC to Etherfi")
#     # Implement Etherfi restaking logic here
#     # Replace with actual implementation
#     raise NotImplementedError("restake_to_etherfi function is not implemented yet")

# def restake_to_pendle(web3: Web3, account: SoftAccount) -> Optional[str]:
#     logger.info("Restaking LBTC to Pendle")
#     # Implement Pendle restaking logic here
#     # Replace with actual implementation
#     raise NotImplementedError("restake_to_pendle function is not implemented yet")

def load_abi(filename: str):
    abi_path = os.path.join(os.path.dirname(__file__), 'abi', filename)
    with open(abi_path, 'r') as abi_file:
        abi = json.load(abi_file)
    return abi

def process_account(account: SoftAccount, parser: UserSettingsParser, status_file: str):
    logger.info(f"Processing account with public address: {account.address}")
    try:
        if account.status == AccountStatus.INIT:
            if account.settings['generate_btc_address'] == 1:
                if account.btc_address:
                    # BTC address already generated, proceed
                    account.update_status(AccountStatus.BTC_ADDRESS_GENERATED)
                else:
                    generate_btc_address(account)
                    # Write the generated BTC address back to the Excel file
                    update_btc_address_in_excel(account)
                    # Update status to waiting for whitelisting
                    account.update_status(AccountStatus.BTC_ADDRESS_GENERATED_WAITING)
                    # Inform the user
                    logger.info(f"Generated BTC address for account. Please whitelist this address on your exchange and rerun the software.")
                    # Save status
                    parser.save_status(status_file)
                    # Update the status to BTC_ADDRESS_GENERATED (hope that user will whitelist it)
                    account.update_status(AccountStatus.BTC_ADDRESS_GENERATED)
                    # Save status
                    parser.save_status(status_file)
                    # Stop processing this account further
                    return
            else:
                account.btc_address = account.settings['btc_address']
                account.update_status(AccountStatus.BTC_ADDRESS_GENERATED)

        if account.status == AccountStatus.BTC_ADDRESS_GENERATED_WAITING:
            # Waiting for the user to whitelist the BTC address
            logger.info(f"Please whitelist the generated BTC address on your exchange and rerun the software.")
            return

        if account.status == AccountStatus.BTC_ADDRESS_GENERATED:
            deposit_btc(account)
            account.update_status(AccountStatus.BTC_DEPOSIT_INITIATED)

        if account.status == AccountStatus.BTC_DEPOSIT_INITIATED:
            wait_for_confirmations(account)
            account.update_status(AccountStatus.BTC_CONFIRMATIONS_PENDING)

        if account.status == AccountStatus.BTC_CONFIRMATIONS_PENDING:
            mint_lbtc(account)
            account.update_status(AccountStatus.LBTC_MINTED)

        if account.status == AccountStatus.LBTC_MINTED:
            confirm_lbtc_mint(account)
            account.update_status(AccountStatus.LBTC_MINT_CONFIRMATION)

        # if account.status == AccountStatus.LBTC_MINT_CONFIRMATION:
        #     if account.settings['restaking_LBTC'] == 1:
        #         restake_lbtc(account)
        #         account.update_status(AccountStatus.LBTC_RESTAKED)
        #     else:
        #         account.update_status(AccountStatus.COMPLETED)

        # if account.status == AccountStatus.LBTC_RESTAKED:
        #     confirm_restake(account)
        #     account.update_status(AccountStatus.LBTC_RESTAKED_CONFIRMATION)
        #     account.update_status(AccountStatus.COMPLETED)

        # Remember to save the status after processing
        parser.save_status(status_file)

    except Exception as e:
        logger.error(f"Error processing account: {e}")
        parser.save_status(status_file)
        raise

def update_btc_address_in_excel(account: SoftAccount):
    """
    Updates the BTC address in the 'Soft_settings.xlsx' file for the given account.
    """
    logger.info("Updating BTC address in Soft_settings.xlsx")
    settings_file = './Soft_settings.xlsx'
    try:
        # Load the Excel file
        with pd.ExcelFile(settings_file) as xls:
            # Read both sheets
            main_df = pd.read_excel(xls, sheet_name='Main')
            lombard_df = pd.read_excel(xls, sheet_name='Lombard')
        
        # Find the row corresponding to the account
        # Assuming that private_key is unique and can be used to identify the account
        private_key = account.settings['private_key']
        # Find the index of the row with this private_key
        index = main_df.index[main_df['private_key'] == private_key].tolist()
        if not index:
            logger.error("Account not found in Soft_settings.xlsx")
            return
        index = index[0]  # Get the first matching index

        # Update the 'btc_address' column in the 'Lombard' sheet
        lombard_df.at[index, 'btc_address'] = str(account.btc_address)

        # Write back to the Excel file
        with pd.ExcelWriter(settings_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            # Remove existing sheets to prevent duplication
            writer.book.remove(writer.book['Main'])
            writer.book.remove(writer.book['Lombard'])
            # Write the updated DataFrames back
            main_df.to_excel(writer, sheet_name='Main', index=False)
            lombard_df.to_excel(writer, sheet_name='Lombard', index=False)
        
        logger.info("BTC address updated in Soft_settings.xlsx")
    except Exception as e:
        logger.error(f"Error updating BTC address in Soft_settings.xlsx: {e}")
        raise

def main():
    settings_file = './Soft_settings.xlsx'
    status_file = './status.json'

    try:
        parser = UserSettingsParser(settings_file)
        parser.load_status(status_file)
        accounts = parser.get_accounts()
    except Exception as e:
        logger.error(f"Error initializing accounts: {e}")
        return

    for account in accounts:
        try:
            process_account(account, parser, status_file)
            # Status is saved within process_account
        except Exception as e:
            logger.error(f"Error processing account: {e}")
            parser.save_status(status_file)
            continue  # Proceed to the next account

if __name__ == '__main__':
    main()