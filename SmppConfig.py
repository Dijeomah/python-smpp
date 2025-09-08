import os
import base64
import logging
from logging.handlers import TimedRotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from pathlib import Path
from typing import Optional
import threading


class DaemonThreadFactory:
    """Python equivalent of DaemonThreadFactory - creates daemon threads"""

    def new_thread(self, target):
        """Create a new daemon thread"""
        thread = threading.Thread(target=target)
        thread.daemon = True
        return thread


class SmppConfig:
    """Python equivalent of the Java Config class for SMPP USSD configuration"""

    def __init__(self):
        # Initialize configuration attributes
        self.server_ip: Optional[str] = None
        self.server_port: int = 0
        self.account: Optional[str] = None
        self.password: Optional[str] = None
        self.system_type: str = ""
        self.service_code: Optional[str] = None
        self.service_type: Optional[str] = None
        self.process_url: str = ""
        self.send_ussd_port: int = 0
        self.number_of_threads: int = 10
        self.send_ussd_username: Optional[str] = None
        self.send_ussd_password: Optional[str] = None
        self.executor_service: Optional[ThreadPoolExecutor] = None

        try:
            self.load_configuration(os.path.join("conf", "settings.conf"))
        except Exception as e:
            print(f"Error loading default configurations: {e}")
            exit(0)

        # Setup logging similar to log4j configuration
        self._setup_logging()

        # Initialize thread pool executor (equivalent to Java's ExecutorService)
        self.executor_service = ThreadPoolExecutor(
            max_workers=self.number_of_threads,
            thread_name_prefix="ussd-worker"
        )

    def load_configuration(self, file_path: str) -> None:
        """Load configuration from properties file with environment variable override"""
        smpp_config = ConfigParser()

        # Handle the Java properties format by adding a default section
        with open(file_path, 'r') as f:
            config_string = '[DEFAULT]\n' + f.read()

        smpp_config.read_string(config_string)

        # Load configuration with environment variable precedence
        self.server_ip = os.getenv("SMPP_SERVER") or smpp_config.get("DEFAULT", "SMPP_SERVER", fallback=None)

        server_port_env = os.getenv("SMPP_PORT")
        if server_port_env:
            self.server_port = int(server_port_env)
        else:
            self.server_port = smpp_config.getint("DEFAULT", "SMPP_PORT", fallback=0)

        self.account = os.getenv("SMPP_USERNAME") or smpp_config.get("DEFAULT", "SMPP_USERNAME", fallback=None)

        # Note: Original Java code has a typo "SMPP_PASSWPORD" - keeping it for compatibility
        self.password = os.getenv("SMPP_PASSWPORD") or smpp_config.get("DEFAULT", "SMPP_PASSWPORD", fallback=None)

        self.system_type = os.getenv("SYSTEM_TYPE") or smpp_config.get("DEFAULT", "SYSTEM_TYPE", fallback="")

        self.service_type = os.getenv("SERVICE_TYPE") or smpp_config.get("DEFAULT", "SERVICE_TYPE", fallback=None)

        self.process_url = os.getenv("PROCESS_URL") or smpp_config.get("DEFAULT", "PROCESS_URL", fallback="")

        self.service_code = os.getenv("SERVICE_CODE") or smpp_config.get("DEFAULT", "SERVICE_CODE", fallback=None)

        self.send_ussd_username = os.getenv("SEND_USSD_USERNAME") or smpp_config.get("DEFAULT", "SEND_USSD_USERNAME", fallback=None)

        self.send_ussd_password = os.getenv("SEND_USSD_PASSWORD") or smpp_config.get("DEFAULT", "SEND_USSD_PASSWORD", fallback=None)

        # Note: Original Java code has a bug - uses server_Port instead of sendussd_Port
        sendussd_port_env = os.getenv("SEND_USSD_PORT")
        if sendussd_port_env:
            self.send_ussd_port = int(sendussd_port_env)
        else:
            self.send_ussd_port = smpp_config.getint("DEFAULT", "SEND_USSD_PORT", fallback=0)

        thread_number_env = os.getenv("NUMBER_OF_THREADS")
        if thread_number_env:
            self.number_of_threads = int(thread_number_env)
        else:
            self.number_of_threads = smpp_config.getint("DEFAULT", "NUMBER_OF_THREADS", fallback=10)

    def _setup_logging(self) -> None:
        """Setup rotating file logger similar to log4j DailyRollingFileAppender"""
        # Create log directory if it doesn't exist
        log_dir = Path("log")
        log_dir.mkdir(exist_ok=True)

        # Setup log file path
        log_file = log_dir / "ussd-smpp.log"

        # Create formatter similar to log4j pattern
        formatter = logging.Formatter(
            '[%(levelname)s] %(asctime)s %(name)s %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Create rotating file handler (daily rotation)
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

        # Also add console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    def encode_base64(self, text: str) -> str:
        """Encode string to base64"""
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')

    def decode_base64(self, encoded_str: str) -> str:
        """Decode base64 string"""
        return base64.b64decode(encoded_str.encode('utf-8')).decode('utf-8')

    def bytes_to_hex(self, data) -> str:
        """Convert bytes to hexadecimal string"""
        if data is None:
            raise ValueError("The data parameter is None")

        if isinstance(data, int):
            # Handle single byte (int)
            return f"{data:02X}"
        elif isinstance(data, (bytes, bytearray)):
            # Handle byte array
            return ''.join(f"{b:02X}" for b in data)
        else:
            raise TypeError("Data must be bytes, bytearray, or int")

    def hex_to_dec(self, hex_str: str) -> int:
        """Convert hexadecimal string to decimal integer"""
        return int(hex_str, 16)

    def shutdown(self) -> None:
        """Shutdown the thread pool executor"""
        if self.executor_service:
            self.executor_service.shutdown(wait=True)


# Example usage and configuration file format
if __name__ == "__main__":
    # Create a sample configuration file
    sample_config = """
# SMPP Configuration
SMPP_SERVER=127.0.0.1
SMPP_PORT=2775
SMPP_USERNAME=test
SMPP_PASSWPORD=test123
SYSTEM_TYPE=USSD
SERVICE_TYPE=USSD
SERVICE_CODE=*123#

# Processing Configuration
PROCESS_URL=http://localhost:8080/process
SEND_USSD_USERNAME=admin
SEND_USSD_PASSWORD=admin123
SEND_USSD_PORT=8080
NUMBER_OF_THREADS=10
"""

    # Ensure conf directory exists
    os.makedirs("conf", exist_ok=True)

    # Write sample config if it doesn't exist
    config_file = os.path.join("conf", "settings.conf")
    if not os.path.exists(config_file):
        with open(config_file, 'w') as f:
            f.write(sample_config)

    # Test the configuration
    config = Config()
    print(f"Server: {config.server_ip}:{config.server_port}")
    print(f"Account: {config.account}")
    print(f"Service Code: {config.service_code}")

    # Test utility functions
    test_text = "Hello World"
    encoded = config.encode_base64(test_text)
    decoded = config.decode_base64(encoded)
    print(f"Original: {test_text}, Encoded: {encoded}, Decoded: {decoded}")

    # Test hex conversion
    test_bytes = b"\x01\x02\x03"
    hex_str = config.bytes_to_hex(test_bytes)
    print(f"Bytes: {test_bytes}, Hex: {hex_str}")

    # Shutdown
    config.shutdown()