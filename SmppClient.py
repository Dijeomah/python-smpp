import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import smpplib.client
import smpplib.consts
import smpplib.gsm
from SmppConfig import SmppConfig
from SendSubmitSm import SendSubmitSm


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
        self.conn.set_message_received_handler(self.handle_message)

        self.logger.info(f"Binding with systemid: {self.account}/{self.password} "
                         f"systemType: {self.system_type} servicetype: {self.service_type}")
        self.conn.connect()
        self.conn.bind_transceiver(
            system_id=self.account,
            password=self.password,
            system_type=self.system_type,
        )
        self._listen_thread = threading.Thread(target=self.conn.listen)
        self._listen_thread.start()

    def disconnect(self):
        """Disconnect from SMPP gateway"""
        if self.conn:
            try:
                self.conn.unbind()
                self.conn.disconnect()
            except smpplib.exceptions.PDUError as e:
                self.logger.error(f"Error while disconnecting: {e}")
            self.conn = None
        self.executor_service.shutdown()

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.conn is not None and self.conn.state == 'BOUND_TRX'

    def handle_message(self, pdu):
        """Handle incoming messages"""
        if pdu.command == 'deliver_sm':
            self.logger.info(f"Received deliver_sm: {pdu.short_message}")
            task = SendSubmitSm(self, pdu)
            self.executor_service.submit(task.run)

    def submit_short_message(self, **kwargs):
        """Submit a short message."""
        if not self.is_connected():
            raise Exception("Session not connected")
        return self.conn.send_message(**kwargs)
