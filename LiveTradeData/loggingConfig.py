# logging_config.py
import logging
import config

def setup_logging():
    logging.basicConfig(level=logging.INFO,  # Set the minimum log level to capture
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename=config.LOG_FILE_PATH,      # Specify the file to save logs (optional)
                    filemode='a')
    logging.getLogger("pika").setLevel(logging.ERROR)
    
def get_logger(name):
    return logging.getLogger(name)
