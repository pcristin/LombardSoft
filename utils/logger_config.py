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
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
color_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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