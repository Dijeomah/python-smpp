import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import smpplib.client
import smpplib.consts
import smpplib.gsm
import smpplib.command
from SmppConfig import SmppConfig
from SendSubmitSm import SendSubmitSm

# NO MONKEY PATCHING - this might be the simplest solution
# If USSD functionality is not required, don't patch

class SmppClient(SmppConfig):
    """SMPP Client implementation using smpplib"""

    def __init__(self, config_instance=None):
        if config_instance:
            for attr in dir(config_instance):
                if not attr.startswith('_') and not callable(getattr(config_instance, attr)):
                    setattr(self, attr, getattr(config_instance, attr))
        else:
            super().__init__()

        self.conn: Optional[smpplib.client.Client] = None
        self.logger = logging.getLogger(__name__)
        self.executor_service = ThreadPoolExecutor(max_workers=self.number_of_threads)
        self._listen_thread = None

    def connect_gateway(self):
        """Connect to SMPP gateway"""
        self.conn = smpplib.client.Client(self.server_ip, self.server_port)

        # Use a wrapper to handle parsing errors
        def safe_handle_message(pdu):
            try:
                self.handle_message(pdu)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
                # Continue listening despite errors

        self.conn.set_message_received_handler(safe_handle_message)

        self.logger.info(f"Binding with systemid: {self.account}/{self.password} "
                         f"systemType: {self.system_type} servicetype: {self.service_type}")

        try:
            self.conn.connect()
            self.conn.bind_transceiver(
                system_id=self.account,
                password=self.password,
                system_type=self.system_type,
            )
            self._listen_thread = threading.Thread(target=self.conn.listen)
            self._listen_thread.daemon = True
            self._listen_thread.start()
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise

    def disconnect(self):
        """Disconnect from SMPP gateway"""
        if self.conn:
            try:
                self.conn.unbind()
                self.conn.disconnect()
            except Exception as e:
                self.logger.error(f"Error while disconnecting: {e}")
            finally:
                self.conn = None
        if self.executor_service:
            self.executor_service.shutdown(wait=False)

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return (self.conn is not None and
                hasattr(self.conn, 'state') and
                self.conn.state == 'BOUND_TRX')

    def handle_message(self, pdu):
        """Handle incoming messages"""
        try:
            if hasattr(pdu, 'command') and pdu.command == 'deliver_sm':
                short_message = getattr(pdu, 'short_message', 'No message')
                self.logger.info(f"Received deliver_sm: {short_message}")
                task = SendSubmitSm(self, pdu)
                self.executor_service.submit(task.run)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def submit_short_message(self, **kwargs):
        """Submit a short message."""
        if not self.is_connected():
            raise Exception("Session not connected")
        return self.conn.send_message(**kwargs)