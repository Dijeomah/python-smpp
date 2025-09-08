import time
import threading
import logging
import socket
from typing import Optional, Callable
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from SmppConfig import SmppConfig
# from config import SmppConfig


class SessionState(Enum):
    """SMPP Session states"""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    BOUND_TX = "BOUND_TX"
    BOUND_RX = "BOUND_RX"
    BOUND_TRX = "BOUND_TRX"
    UNBOUND = "UNBOUND"


class SMPPSession:
    """Simple SMPP Session implementation - placeholder for actual SMPP library"""

    def __init__(self, host: str, port: int, bind_params: dict):
        self.host = host
        self.port = port
        self.bind_params = bind_params
        self.session_state = SessionState.CLOSED
        self.socket: Optional[socket.socket] = None
        self.message_receiver_listener: Optional[Callable] = None
        self.session_state_listeners = []
        self.enquire_link_timer = 30000  # 30 seconds
        self._running = False

    def connect(self):
        """Connect and bind to SMPP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.session_state = SessionState.BOUND_TRX
            self._running = True
            self._notify_state_change(SessionState.BOUND_TRX, SessionState.CLOSED)
            logging.info(f"Connected to SMPP server {self.host}:{self.port}")

            # Start enquire link timer
            self._start_enquire_link_timer()

        except Exception as e:
            self.session_state = SessionState.CLOSED
            raise Exception(f"Failed to connect to SMPP server: {e}")

    def disconnect(self):
        """Disconnect from SMPP server"""
        self._running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        old_state = self.session_state
        self.session_state = SessionState.CLOSED
        self._notify_state_change(SessionState.CLOSED, old_state)
        logging.info("Disconnected from SMPP server")

    def is_connected(self) -> bool:
        """Check if session is connected and bound"""
        return self.session_state in [SessionState.BOUND_TRX, SessionState.BOUND_TX, SessionState.BOUND_RX]

    def get_session_state(self) -> SessionState:
        """Get current session state"""
        return self.session_state

    def set_enquire_link_timer(self, interval_ms: int):
        """Set enquire link timer interval"""
        self.enquire_link_timer = interval_ms

    def set_message_receiver_listener(self, listener):
        """Set message receiver listener"""
        self.message_receiver_listener = listener

    def add_session_state_listener(self, listener):
        """Add session state listener"""
        self.session_state_listeners.append(listener)

    def submit_short_message(self, service_type, source_ton, source_npi, source_addr,
                             dest_ton, dest_npi, dest_addr, esm_class, protocol_id,
                             priority_flag, schedule_delivery_time, validity_period,
                             registered_delivery, replace_if_present_flag, data_coding,
                             sm_default_msg_id, short_message, optional_parameters=None):
        """Submit short message (placeholder implementation)"""
        if not self.is_connected():
            raise Exception("Session not connected")

        # This would normally send the actual SMPP PDU
        logging.info(f"Submitting message from {source_addr} to {dest_addr}: {short_message}")

        # Simulate message submission
        return "message_id_12345"

    def _start_enquire_link_timer(self):
        """Start enquire link timer"""
        def enquire_link_worker():
            while self._running and self.is_connected():
                time.sleep(self.enquire_link_timer / 1000.0)
                if self._running and self.is_connected():
                    logging.debug("Sending enquire_link")
                    # Would send actual enquire_link PDU here

        thread = threading.Thread(target=enquire_link_worker, daemon=True)
        thread.start()

    def _notify_state_change(self, new_state: SessionState, old_state: SessionState):
        """Notify all session state listeners of state change"""
        for listener in self.session_state_listeners:
            try:
                listener.on_state_change(new_state, old_state, self)
            except Exception as e:
                logging.error(f"Error notifying session state listener: {e}")


class MessageReceiverListenerImpl:
    """Message receiver listener implementation"""

    def __init__(self, smpp_client):
        self.smpp_client = smpp_client
        self.logger = logging.getLogger(__name__)

    def on_accept_deliver_sm(self, deliver_sm):
        """Handle incoming DeliverSm messages"""
        try:
            # Check if it's not a delivery receipt
            if not self._is_delivery_receipt(deliver_sm):
                message = deliver_sm.get('short_message', b'').decode('utf-8')
                dest_address = deliver_sm.get('dest_address', '')

                print(f"RECEIVING{message} CONNECT:::{self.smpp_client.conn}: {dest_address}")

                if self.smpp_client.conn and self.smpp_client.conn.is_connected():
                    # Execute in thread pool
                    from SendSubmitSm import SendSubmitSm
                    task = SendSubmitSm(self.smpp_client.conn, deliver_sm)
                    self.smpp_client.executor_service.submit(task.run)
                else:
                    # Trigger reconnection
                    self.smpp_client._reconnect_after(self.smpp_client.reconnect_interval)
        except Exception as e:
            self.logger.error(f"Error processing DeliverSm: {e}")

    def on_accept_alert_notification(self, alert_notification):
        """Handle alert notifications"""
        self.logger.info("AlertNotification not implemented")

    def on_accept_data_sm(self, data_sm, source):
        """Handle DataSm messages"""
        self.logger.info("DataSm not implemented")
        return None

    def _is_delivery_receipt(self, deliver_sm) -> bool:
        """Check if message is a delivery receipt"""
        # This would check the ESM class for delivery receipt flag
        return False


class SessionStateListenerImpl:
    """Session state listener implementation"""

    def __init__(self, smpp_client):
        self.smpp_client = smpp_client
        self.logger = logging.getLogger(__name__)

    def on_state_change(self, new_state: SessionState, old_state: SessionState, source):
        """Handle session state changes"""
        if new_state == SessionState.CLOSED:
            self.logger.info("Session closed")
            self.smpp_client._reconnect_after(self.smpp_client.reconnect_interval)


class ReconnectionThread(threading.Thread):
    """Thread to handle reconnection logic"""

    def __init__(self, smpp_client, delay_ms: int):
        super().__init__(daemon=True)
        self.smpp_client = smpp_client
        self.delay_ms = delay_ms
        self.logger = logging.getLogger(__name__)

    def run(self):
        """Run reconnection logic"""
        self.logger.info(f"Schedule reconnect after {self.delay_ms} millis")

        try:
            time.sleep(self.delay_ms / 1000.0)
        except InterruptedException:
            return

        attempt = 0
        while (self.smpp_client.conn is None or
               not self.smpp_client.conn.is_connected()):
            try:
                attempt += 1
                self.logger.info(f"Reconnecting attempt #{attempt}...")
                self.smpp_client.conn = self.smpp_client._new_session()
                self.smpp_client.conn.connect()

            except Exception as e:
                self.logger.error(f"Failed opening connection and bind to "
                                  f"{self.smpp_client.server_ip}:{self.smpp_client.server_port}",
                                  exc_info=e)
                try:
                    time.sleep(1.0)
                except InterruptedException:
                    break


class SmppClient(SmppConfig):
    """SMPP Client implementation"""

    def __init__(self, config_instance=None):
        if config_instance:
            # Copy configuration from existing instance
            for attr in dir(config_instance):
                if not attr.startswith('_') and not callable(getattr(config_instance, attr)):
                    setattr(self, attr, getattr(config_instance, attr))
        else:
            super().__init__()

        self.retry = True
        self.bind_retry_counter = 0
        self.smpp_server_running = False
        self.conn: Optional[SMPPSession] = None
        self.reconnect_interval = 5000  # 5 seconds
        self.logger = logging.getLogger(__name__)
        self.executor_service = ThreadPoolExecutor(max_workers=10)

    def connect_gateway(self):
        """Connect to SMPP gateway"""
        self.conn = self._new_session()
        self.conn.connect()

    def disconnect(self):
        """Disconnect from SMPP gateway"""
        if self.conn:
            self.conn.disconnect()
            self.conn = None
        self.executor_service.shutdown()

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.conn is not None and self.conn.is_connected()

    def _new_session(self) -> SMPPSession:
        """Create a new SMPP session"""
        self.logger.info(f"Binding with systemid: {self.account}/{self.password} "
                         f"systemType: {self.system_type} servicetype: {self.service_type}")

        bind_params = {
            'bind_type': 'BIND_TRX',
            'system_id': self.account,
            'password': self.password,
            'system_type': self.system_type,
            'ton': 'UNKNOWN',
            'npi': 'UNKNOWN',
            'address_range': None
        }

        session = SMPPSession(self.server_ip, self.server_port, bind_params)
        session.set_enquire_link_timer(25000)
        session.set_message_receiver_listener(MessageReceiverListenerImpl(self))
        session.add_session_state_listener(SessionStateListenerImpl(self))

        return session

    def _reconnect_after(self, time_in_millis: int):
        """Schedule reconnection after specified time"""
        reconnect_thread = ReconnectionThread(self, time_in_millis)
        reconnect_thread.start()


# Exception for interrupted operations
class InterruptedException(Exception):
    pass