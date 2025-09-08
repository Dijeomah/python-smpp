import logging
import threading
import struct
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import smpplib.client
import smpplib.consts
import smpplib.gsm
import smpplib.command
import smpplib.pdu
from SmppConfig import SmppConfig
from SendSubmitSm import SendSubmitSm

def patch_parse_optional_params():
    """Patch PDU classes to handle unknown optional parameters gracefully."""

    def patched_parse_optional_params(self, data):
        pos = 0
        while pos < len(data):
            try:
                # Need at least 4 bytes for tag and length
                if len(data) - pos < 4:
                    break

                field, length = struct.unpack('!HH', data[pos:pos+4])
                value_start = pos + 4
                value_end = value_start + length

                if value_end > len(data):
                    logging.warning(f"Invalid length for optional parameter with tag {field}. Skipping.")
                    break

                if field in self.params:
                    param = self.params[field]
                    value = data[value_start:value_end]
                    param_name = param.get('name')
                    param_type = param.get('type')

                    if not param_name or not param_type:
                        logging.warning(f"Optional parameter with tag {field} is misconfigured. Ignoring.")
                    else:
                        if param.get('multi'):
                            if not hasattr(self, param_name):
                                setattr(self, param_name, [])
                            getattr(self, param_name).append(param_type(value))
                        else:
                            setattr(self, param_name, param_type(value))
                else:
                    logging.warning(f"Unrecognized optional parameter with tag {field}. Ignoring.")

                pos = value_end

            except struct.error as e:
                logging.error(f"Error unpacking optional parameter: {e}. Remaining data: {data[pos:]}")
                break

    # Patch all PDU classes in smpplib.command
    for name in dir(smpplib.command):
        attr = getattr(smpplib.command, name)
        if isinstance(attr, type) and issubclass(attr, smpplib.command.pdu) and hasattr(attr, 'parse_optional_params'):
            attr.parse_optional_params = patched_parse_optional_params
            logging.info(f"Patched {name} to handle unknown optional parameters.")

# Apply the generic patch
patch_parse_optional_params()

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
                # Check if we have ussd_service_op
                ussd_op = getattr(pdu, 'ussd_service_op', None)
                if ussd_op:
                    self.logger.info(f"Received deliver_sm with USSD op: {ussd_op}, message: {short_message}")
                else:
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