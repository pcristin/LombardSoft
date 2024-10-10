# main.py

import os
import json
import random
from models import UserSettingsParser
from utils.logger_config import logger
from models.status_enum import AccountStatus
from models.soft_account import SoftAccount
from sdks.lombard_sdk.api import LombardAPI
from sdks.exchanges_sdk.okx_api import OKX_API
from sdks.exchanges_sdk.bitget_api import Bitget_API
from web3 import Web3, HTTPProvider
from sdks.lombard_sdk.lbtc_operations import LBTCOps
from typing import Optional, Union
import requests
from hexbytes import HexBytes
import pandas as pd
from openpyxl import load_workbook
import asyncio
from utils.logger_config import AccountFilter
from utils.constants import RPCS
from sdks.relay_sdk.relay_api import RelayAPI

def check_eth_balance(account: SoftAccount) -> bool:
    logger.addFilter(AccountFilter(account.address))
    logger.info("Checking ETH balance")
    web3 = get_web3_instance(account, 'Ethereum')
    balance = web3.eth.get_balance(account.address) / 10**18  # Convert Wei to ETH
    logger.info(f"ETH Balance: {balance} ETH")
    if balance >= 0.0012:
        logger.info("Sufficient ETH balance on Ethereum Mainnet")
        return True
    else:
        return False

def check_l2_eth_balance(account: SoftAccount) -> Union[tuple[str, bool], bool]:
    logger.addFilter(AccountFilter(account.address))
    logger.info("Checking L2 ETH balance")
    for l2_chain in ['Optimism', 'Base', 'Arbitrum']:
        web3 = get_web3_instance(account, l2_chain)
        balance = float(web3.from_wei(web3.eth.get_balance(account.address), 'ether'))
        logger.info(f"L2 ETH Balance: {balance} ETH")
        if balance >= 0.0022:
            logger.info(f"Sufficient L2 ETH balance on {l2_chain}")
            return (l2_chain, True)
    else:
        return False

def withdraw_eth(account: SoftAccount) -> str:
    logger.addFilter(AccountFilter(account.address))
    logger.info("Withdrawing ETH")
    exchange_name = account.settings['exchange']
    amount = format(round(random.uniform(0.0025, 0.0035), 4), '.4f')
    chain = random.choice(['Optimism', 'Base'])
    if exchange_name == 'OKX':
        exchange_api = OKX_API(
            api_key=account.settings['exchange_api_key'],
            secret_key=account.settings['exchange_secret_key'],
            passphrase=account.settings['exchange_passphrase']
        )
    elif exchange_name == 'Bitget':
        exchange_api = Bitget_API(
            api_key=account.settings['exchange_api_key'],
            secret_key=account.settings['exchange_secret_key'],
            passphrase=account.settings['exchange_passphrase']
        )
    else:
        raise Exception(f"Unsupported exchange: {exchange_name}")
    withdraw_id = exchange_api.withdraw(address=account.address, amount=amount, ccy='ETH', chain=chain)

    if withdraw_id and isinstance(withdraw_id, dict):
        account.withdrawal_id_eth = withdraw_id['data']['orderId']
    elif withdraw_id and isinstance(withdraw_id, str):
        account.withdrawal_id_eth = withdraw_id
        logger.info(f"ETH withdrawal initiated. Withdrawal ID: {withdraw_id}")
    else:
        raise Exception("Failed to initiate ETH withdrawal")
    return chain

async def wait_for_withdrawal_confirmation_eth(account: SoftAccount) -> Union[bool, None]:
    logger.addFilter(AccountFilter(account.address))
    logger.info("Waiting for ETH withdrawal confirmation")
    exchange_name = account.settings['exchange']
    confirmed = False
    if exchange_name == 'OKX':
        exchange_api = OKX_API(
            api_key=account.settings['exchange_api_key'],
            secret_key=account.settings['exchange_secret_key'],
            passphrase=account.settings['exchange_passphrase']
        )
        if account.withdrawal_id_eth:
            for _ in range(6):
                withdrawal_status = exchange_api.get_withdrawal_status(account.withdrawal_id_eth)
                if withdrawal_status is not None:
                    logger.info(f"Withdrawal state for wid {account.withdrawal_id_eth}]: {withdrawal_status['state']}")
                    if 'Withdrawal complete' in withdrawal_status['state']:
                        confirmed = True
                        logger.info(f"ETH withdrawal confirmed")
                        return confirmed
                    else:
                        logger.info(f"ETH withdrawal not confirmed yet, waiting ...")
                        await asyncio.sleep(random.randint(60, 300))
            if not confirmed:
                logger.error(f"Couldn't confirm ETH withdrawal in 10 minutes with wdId: {account.withdrawal_id_eth} ")
                return False
        else:
            logger.error('There was no withdrawal id found')
            return False
        
    elif exchange_name == 'Bitget':
        exchange_api = Bitget_API(
            api_key=account.settings['exchange_api_key'],
            secret_key=account.settings['exchange_secret_key'],
            passphrase=account.settings['exchange_passphrase']
        )
        if account.withdrawal_id_eth:
            for _ in range(6):
                withdrawal_status = exchange_api.get_withdrawal_status(account.withdrawal_id_eth)
                if withdrawal_status is not None:
                    logger.info(f"Withdrawal state for wid {account.withdrawal_id_eth}]: {withdrawal_status['data'][0]['status']}")
                    if withdrawal_status['msg'] == 'success':
                        confirmed = True
                        logger.info(f"ETH withdrawal confirmed")
                        return confirmed
                    else:
                        logger.info(f"ETH withdrawal not confirmed yet, waiting...")
                        await asyncio.sleep(random.randint(60, 300))
            if not confirmed:
                logger.error(f"Couldn't confirm ETH withdrawal in 10 minutes with wdId: {account.withdrawal_id_eth} ")
                return False
        else:
            logger.error('There was no withdrawal id found')
            return False
    else:
        raise Exception(f"Unsupported exchange: {exchange_name}")
    
async def bridge_from_l2(account: SoftAccount, source_l2_chain: str) -> Union[str, None]:
    relay_api = RelayAPI(account, source_l2_chain)
    try:
        bridge_tx_hash = await relay_api.bridge_eth()
        return bridge_tx_hash
    except Exception as e:
        return None

def get_web3_instance(account: SoftAccount, chain_name: str) -> Web3:
    """
    Initializes a Web3 instance, optionally using a proxy.

    Args:
        account (SoftAccount): The account object containing settings.

    Returns:
        Web3: The initialized Web3 instance.
    """
    logger.addFilter(AccountFilter(account.address))
    provider_url = RPCS[chain_name]
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
    logger.addFilter(AccountFilter(account.address))
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

def withdraw_btc(account: SoftAccount):
    logger.addFilter(AccountFilter(account.address))
    logger.info("Initiating BTC withdrawal")
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
            withdrawal_id = exchange_api.withdraw(amount=amount_str, address=btc_address, ccy='BTC', chain='BTC')
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
            withdrawal_id = exchange_api.withdraw(amount=amount_str, address=btc_address, ccy='BTC', chain='BTC')['data']['orderId']
        else:
            raise ValueError("BTC address cannot be None")
    else:
        raise Exception(f"Unsupported exchange: {exchange_name}")

    if withdrawal_id:
        account.withdrawal_id_btc = withdrawal_id
        logger.info(f"BTC withdrawal initiated. Withdrawal ID: {withdrawal_id}")
    else:
        raise Exception("Failed to initiate BTC withdrawal")

async def wait_for_confirmations(account: SoftAccount):
    logger.addFilter(AccountFilter(account.address))
    logger.info("Waiting for BTC withdrawal confirmations")
    lombard_api = LombardAPI(
        private_key=account.settings['private_key'],
        proxy=account.settings.get('proxy')  # Pass the proxy
    )
    check_interval = 1800  # Check every 30 minutes
    max_checks = 8  # Wait up to 3 hours

    for _ in range(max_checks):
        withdrawals = lombard_api.get_deposits_by_address()
        if len(withdrawals) > 0:
            for withdrawal in withdrawals:
                if withdrawal['address'] == account.btc_address and 'notarization_wait_dur' in withdrawal:
                    logger.info("Required confirmations not reached yet")
                elif withdrawal['address'] == account.btc_address and 'raw_payload' in withdrawal and 'signature' in withdrawal:
                    logger.info("Required confirmations reached")
                    return
        else:
            logger.info("No deposits found yet. Going to sleep for 30 minutes....")

        await asyncio.sleep(check_interval)

    raise Exception("Timed out waiting for BTC deposit confirmations")

async def mint_lbtc(account: SoftAccount):
    logger.addFilter(AccountFilter(account.address))
    logger.info(f"Minting LBTC for account: {account.address}")
    web3 = get_web3_instance(account, 'Ethereum')

    lbtc_ops = LBTCOps(web3=web3, account=account)
    tx_hash = await lbtc_ops.claim_lbtc()

    if tx_hash:
        account.transaction_hash_mint_lbtc = tx_hash  
        logger.debug(f"LBTC mint transaction initiated. Transaction hash: {tx_hash}")
    else:
        raise Exception("Failed to mint LBTC")

def confirm_lbtc_mint(account: SoftAccount):
    logger.info("Confirming LBTC minting transaction")
    web3 = get_web3_instance(account, 'Ethereum')

    tx_hash = account.transaction_hash_mint_lbtc
    if not tx_hash:
        raise Exception("No transaction hash found for LBTC minting")

    tx_hash_bytes = HexBytes(tx_hash)  # Ensure tx_hash is in a compatible format
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=600)
    if receipt["status"] == 1:
        logger.info("LBTC minting transaction confirmed")
    else:
        raise Exception("LBTC minting transaction failed")

async def restake_lbtc(account: SoftAccount):
    logger.addFilter(AccountFilter(account.address))
    logger.info("Restaking LBTC")
    selected_vault = account.settings['selected_vault']
    web3 = get_web3_instance(account, 'Ethereum')

    if selected_vault == 'Defi_Vault':
        tx_hash = await restake_to_defi_vault(web3, account)
    # elif selected_vault == 'Etherfi':
    #     tx_hash = restake_to_etherfi(web3, account)
    # elif selected_vault == 'Pendle':
    #     tx_hash = restake_to_pendle(web3, account)
    else:
        raise Exception(f"Unknown vault: {selected_vault}")

    if tx_hash:
        account.transaction_hash_restake_lbtc = tx_hash
        logger.info(f"LBTC restake transaction initiated. Transaction hash: {tx_hash}")
    else:
        raise Exception("Failed to restake LBTC")

def confirm_restake(account: SoftAccount):
    logger.addFilter(AccountFilter(account.address))
    logger.info("Confirming LBTC restake transaction")
    web3 = get_web3_instance(account, 'Ethereum')

    tx_hash = account.transaction_hash_restake_lbtc
    if not tx_hash:
        raise Exception("No transaction hash found for LBTC restaking")

    tx_hash_bytes = HexBytes(tx_hash)  # Ensure tx_hash is in a compatible format
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=600)
    if receipt["status"] == 1:
        logger.info("LBTC restaking transaction confirmed")
    else:
        raise Exception("LBTC restaking transaction failed")

async def restake_to_defi_vault(web3: Web3, account: SoftAccount) -> Optional[str]:
    logger.addFilter(AccountFilter(account.address))
    logger.info("Restaking LBTC to Defi_Vault")
    lbtc_ops = LBTCOps(web3=web3, account=account)
    approve_tx_hash = await lbtc_ops.approve_lbtc(web3.to_checksum_address("0x5401b8620E5FB570064CA9114fd1e135fd77D57c"))
    account.transaction_hash_approve_lbtc = approve_tx_hash
    logger.debug(f"LBTC approved for restaking. Transaction hash: {approve_tx_hash}")
    restake_tx_hash = await lbtc_ops.restake_lbtc_defi_vault()
    account.transaction_hash_restake_lbtc = restake_tx_hash
    logger.debug(f"LBTC restaked to vault. Transaction hash: {restake_tx_hash}")
    return restake_tx_hash


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

async def process_account(account: SoftAccount, parser: UserSettingsParser, status_file: str):
    
    logger.addFilter(AccountFilter(account.address))
    logger.debug(f"Account status: {account.status.value}")
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
            withdraw_btc(account)
            account.update_status(AccountStatus.BTC_DEPOSIT_INITIATED)

        if account.status == AccountStatus.BTC_DEPOSIT_INITIATED:
            await wait_for_confirmations(account)
            account.update_status(AccountStatus.CHECKING_ETH_BALANCE)
        
        if account.status == AccountStatus.CHECKING_ETH_BALANCE:
            check_eth_result = check_eth_balance(account)
            if check_eth_result:
                account.update_status(AccountStatus.BTC_CONFIRMATIONS_PENDING)
            else:
                account.update_status(AccountStatus.CHECKING_L2_ETH_BALANCE)

        if account.status == AccountStatus.CHECKING_L2_ETH_BALANCE:
            check_l2_eth_result = check_l2_eth_balance(account)
            if isinstance(check_l2_eth_result, tuple):
                source_l2_chain = check_l2_eth_result[0]
                account.update_status(AccountStatus.BRIDGING_FROM_L2)
            else:
                account.update_status(AccountStatus.WITHDRAWING_ETH_FROM_EXCHANGE)

        if account.status == AccountStatus.WITHDRAWING_ETH_FROM_EXCHANGE:
            source_l2_chain = withdraw_eth(account)
            account.update_status(AccountStatus.WITHDRAWING_ETH_FROM_EXCHANGE_CONFIRMATION)

        if account.status == AccountStatus.WITHDRAWING_ETH_FROM_EXCHANGE_CONFIRMATION:
            eth_withdrawal_status = await wait_for_withdrawal_confirmation_eth(account)
            if not eth_withdrawal_status:
                raise KeyError(f"Couldn't confirm ETH withdrawal from {account.settings.get('exchange')}")
            account.update_status(AccountStatus.BRIDGING_FROM_L2)
        
        if account.status == AccountStatus.BRIDGING_FROM_L2:
            tx_hash_bridge = await bridge_from_l2(account, source_l2_chain)
            if not tx_hash_bridge:
                logger.error(f"Failed to bridge ETH from {source_l2_chain}")
                raise
            account.update_status(AccountStatus.BTC_CONFIRMATIONS_PENDING)

        if account.status == AccountStatus.BTC_CONFIRMATIONS_PENDING:
            await mint_lbtc(account)
            account.update_status(AccountStatus.LBTC_MINT)

        if account.status == AccountStatus.LBTC_MINT:
            confirm_lbtc_mint(account)
            account.update_status(AccountStatus.LBTC_MINT_CONFIRMATION)

        if account.status == AccountStatus.LBTC_MINT_CONFIRMATION:
            if account.settings['restaking_LBTC'] == 1:
                await restake_lbtc(account)
                account.update_status(AccountStatus.LBTC_RESTAKED)
            else:
                account.update_status(AccountStatus.COMPLETED)

        if account.status == AccountStatus.LBTC_RESTAKED:
            confirm_restake(account)
            account.update_status(AccountStatus.LBTC_RESTAKED_CONFIRMATION)
            account.update_status(AccountStatus.COMPLETED)

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
    logger.addFilter(AccountFilter(account.address))
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

async def main():
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
            await process_account(account, parser, status_file)
            # Status is saved within process_account
        except Exception as e:
            logger.error(f"Error processing account: {e}")
            parser.save_status(status_file)
            continue  # Proceed to the next account

if __name__ == '__main__':
    asyncio.run(main())