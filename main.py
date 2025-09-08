#!/usr/bin/env python3
"""
MTN USSD SMPP Gateway - Python Implementation
Converted from Java SMPP implementation

This application connects to an SMPP server and handles USSD messages,
processing them through HTTP requests and sending responses back.
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from MtnUssd import MtnUssd


def setup_directories():
    """Create necessary directories if they don't exist"""
    directories = ['conf', 'log']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)


def create_sample_config():
    """Create a sample configuration file if it doesn't exist"""
    config_file = Path("conf/settings.conf")

    if not config_file.exists():
        sample_config = """# MTN USSD SMPP Configuration
# SMPP Server Settings
SMPP_SERVER=127.0.0.1
SMPP_PORT=2775
SMPP_USERNAME=test
SMPP_PASSWPORD=test123
SYSTEM_TYPE=USSD
SERVICE_TYPE=USSD
SERVICE_CODE=*123#

# Processing Configuration
PROCESS_URL=http://localhost:8080/ussd/process
SEND_USSD_USERNAME=admin
SEND_USSD_PASSWORD=admin123
SEND_USSD_PORT=8080
NUMBER_OF_THREADS=10

# You can override any of these settings using environment variables
# For example: export SMPP_SERVER=192.168.1.100
"""

        with open(config_file, 'w') as f:
            f.write(sample_config)

        print(f"Created sample configuration file: {config_file}")
        print("Please update the configuration with your SMPP server details.")


def main():
    """Main entry point of the application"""
    try:
        print("=" * 60)
        print("MTN USSD SMPP Gateway - Python Implementation")
        print("=" * 60)

        # Setup directories
        setup_directories()

        # Create sample config if needed
        create_sample_config()

        # Create and start the USSD service
        print("Initializing MTN USSD service...")
        ussd_service = MtnUssd()

        print(f"Configuration loaded:")
        print(f"  SMPP Server: {ussd_service.server_ip}:{ussd_service.server_port}")
        print(f"  Account: {ussd_service.account}")
        print(f"  Service Code: {ussd_service.service_code}")
        print(f"  Process URL: {ussd_service.process_url}")
        print(f"  Threads: {ussd_service.number_of_threads}")
        print()

        # Start the service
        ussd_service.run()

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"Configuration file not found: {e}")
        print("Please ensure the configuration file exists in conf/settings.conf")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to start MTN USSD service: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()