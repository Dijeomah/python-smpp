# MtnUssd.py
import time
import logging
import signal
import sys
import socket
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

    def _can_connect_to_server(self) -> bool:
        """Checks if a TCP connection can be established to the SMPP server."""
        try:
            with socket.create_connection((self.server_ip, self.server_port), timeout=5) as sock:
                self._logger.debug(f"Successfully connected to {self.server_ip}:{self.server_port}")
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            self._logger.warning(f"Connectivity check to {self.server_ip}:{self.server_port} failed: {e}")
            return False

    def start_client(self) -> None:
        """Start the SMPP client and connect to gateway"""
        try:
            if self.client_instance:
                self._logger.info("Starting SMPP client...")
                success = self.client_instance.connect_gateway()
                if success:
                    self._logger.info("SMPP client started successfully")
                else:
                    self._logger.warning("SMPP client connection failed, but reconnection will be attempted automatically")
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
            # Make sure the client knows to stop as well
            if self.client_instance:
                self.client_instance._should_run = False
            self.stop_client()
            sys.exit(0)

        # Handle SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self) -> None:
        """Main application loop"""
        try:
            # Start the SMPP client
            self.start_client()

            self._logger.info("MTN USSD service is running. Press Ctrl+C to stop.")
            print("MTN USSD service is running. Press Ctrl+C to stop.")

            # Main loop - let the client handle its own reconnections
            # We just need to keep the main thread alive and check periodically
            check_interval = 30  # Check every 30 seconds
            last_status_log = time.time()
            status_log_interval = 300  # Log status every 5 minutes

            while self.retry:
                try:
                    # Check if we should still be running
                    if not self.retry:
                        break

                    current_time = time.time()

                    # Log status periodically
                    if current_time - last_status_log >= status_log_interval:
                        if self.client_instance:
                            status = "Connected" if self.client_instance.is_connected() else "Disconnected"
                            session_state = self.client_instance.get_session_state().value if hasattr(self.client_instance.get_session_state(), 'value') else str(self.client_instance.get_session_state())
                            self._logger.info(f"Service status: {status}, Session state: {session_state}")
                        last_status_log = current_time

                    # Sleep for the check interval
                    time.sleep(check_interval)

                except KeyboardInterrupt:
                    self._logger.info("Keyboard interrupt received, shutting down...")
                    self.retry = False
                    break
                except Exception as e:
                    self._logger.error(f"Error in main loop: {e}")
                    if not self.retry:
                        break
                    # Continue the loop on error
                    time.sleep(5.0)  # Wait a bit before retrying

        except Exception as e:
            self._logger.error(f"Fatal error in main application: {e}", exc_info=True)
            raise
        finally:
            # Ensure cleanup
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