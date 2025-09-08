import time
import logging
import signal
import sys
from typing import Optional

# Import the Config class we created earlier
# from config import Config
from SmppConfig import SmppConfig

# Import the SmppClient class
from SmppClient import SmppClient


class MtnUssd(SmppConfig):
    """Main USSD application class that extends Config functionality"""

    def __init__(self):
        # Initialize the parent Config class
        super().__init__()

        # Initialize class attributes
        self.retry: bool = True
        self.client_instance: Optional[SmppClient] = None

        # Setup logger
        self._logger = logging.getLogger(__name__)

        # Create SMPP client instance - pass self as config
        self.client_instance = SmppClient(self)

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def start_client(self) -> None:
        """Start the SMPP client and connect to gateway"""
        try:
            if self.client_instance:
                self._logger.info("Starting SMPP client...")
                self.client_instance.connect_gateway()
                self._logger.info("SMPP client started successfully")
            else:
                raise RuntimeError("SMPP client instance is not initialized")
        except Exception as e:
            self._logger.error(f"Failed to start SMPP client: {e}")
            raise

    def stop_client(self) -> None:
        """Stop the SMPP client and cleanup resources"""
        try:
            if self.client_instance:
                self._logger.info("Stopping SMPP client...")
                self.client_instance.disconnect()
                self._logger.info("SMPP client stopped")

            # Shutdown thread pool
            self.shutdown()

        except Exception as e:
            self._logger.error(f"Error stopping SMPP client: {e}")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self._logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.retry = False
            self.stop_client()
            sys.exit(0)

        # Handle SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self) -> None:
        """Main application loop"""
        try:
            self.start_client()
            self._logger.info("MTN USSD service is running. Press Ctrl+C to stop.")
            print("MTN USSD service is running. Press Ctrl+C to stop.")

            while self.retry:
                if not (self.client_instance and self.client_instance.is_connected()):
                    self._logger.warning("SMPP client disconnected. Attempting to reconnect in 5 seconds...")
                    self.stop_client()
                    time.sleep(5)

                    if not self.retry:
                        break

                    self._logger.info("Re-initializing client for reconnection.")
                    self.client_instance = SmppClient(self)
                    self.start_client()
                
                time.sleep(1)

        except Exception as e:
            self._logger.error(f"Fatal error in main application: {e}", exc_info=True)
        finally:
            self.stop_client()
            print("MTN USSD service stopped.")


def main():
    """Entry point of the application"""
    try:
        # Create and run the MTN USSD service
        ussd_service = MtnUssd()
        ussd_service.run()

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Failed to start MTN USSD service: {e}", exc_info=True)
        print(f"Failed to start service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
