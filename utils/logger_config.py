import logging
import colorlog
import os
from datetime import datetime

# Ensure the logs directory exists
log_dir = './utils/logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Generate a unique log file name based on the current time and date
log_filename = datetime.now().strftime("%H_%M %d_%m_%y") + '.log'
log_filepath = os.path.join(log_dir, log_filename)

# Custom filter to add account address to log records
class AccountFilter(logging.Filter):
    def __init__(self, account_address):
        super().__init__()
        self.account_address = account_address

    def filter(self, record):
        # Format the account address as first 5 and last 4 characters
        record.account_address = f"{self.account_address[:5]}...{self.account_address[-4:]}"
        return True

# Set up logging
logger = logging.getLogger('lombard_logger')
logger.setLevel(logging.DEBUG)

# Create a file handler
file_handler = logging.FileHandler(log_filepath)
file_handler.setLevel(logging.DEBUG)

# Create a console handler with colorlog
console_handler = colorlog.StreamHandler()
console_handler.setLevel(logging.INFO)  # Set to INFO level

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - (%(account_address)s): %(message)s')
color_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - (%(account_address)s): %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)

file_handler.setFormatter(formatter)
console_handler.setFormatter(color_formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Example usage: Add the filter with the account address
# account_address = "0x1234567890abcdef1234567890abcdef12345678"
# logger.addFilter(AccountFilter(account_address))