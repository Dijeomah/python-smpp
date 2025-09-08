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

                # Check if this field is in our params
                if hasattr(self, 'params') and field in self.params:
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
                    # Unknown parameter, skip it but don't crash
                    logging.debug(f"Unrecognized optional parameter with tag {field}. Skipping.")

                pos = value_end

            except struct.error as e:
                logging.error(f"Error unpacking optional parameter: {e}. Remaining data: {data[pos:]}")
                break
            except Exception as e:
                logging.error(f"Unexpected error processing optional parameter: {e}")
                break

    # Patch specific command classes that have parse_optional_params
    classes_to_patch = []

    # Look for classes in smpplib.command that might need patching
    for name in dir(smpplib.command):
        attr = getattr(smpplib.command, name)
        if (isinstance(attr, type) and
                hasattr(attr, 'parse_optional_params') and
                callable(getattr(attr, 'parse_optional_params'))):
            classes_to_patch.append(attr)

    # Also check if there are specific classes we know about
    specific_classes = ['DeliverSM', 'SubmitSM', 'DataSM']
    for class_name in specific_classes:
        if hasattr(smpplib.command, class_name):
            cls = getattr(smpplib.command, class_name)
            if (isinstance(cls, type) and
                    hasattr(cls, 'parse_optional_params') and
                    callable(getattr(cls, 'parse_optional_params'))):
                if cls not in classes_to_patch:
                    classes_to_patch.append(cls)

    # Apply the patch to all identified classes
    for cls in classes_to_patch:
        original_method = getattr(cls, 'parse_optional_params')
        setattr(cls, 'parse_optional_params', patched_parse_optional_params)
        logging.info(f"Patched {cls.__name__} to handle unknown optional parameters.")

# Apply the generic patch
try:
    patch_parse_optional_params()
    logging.info("Optional parameter parsing patching completed")
except Exception as e:
    logging.warning(f"Failed to patch optional parameter parsing: {e}")


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

        # Use a safe message handler wrapper
        def safe_handle_message(pdu):
            try:
                self.handle_message(pdu)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")

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
            self.logger.info("SMPP connection established successfully")
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise

    def disconnect(self):
        """Disconnect from SMPP gateway"""
        if self.conn:
            try:
                self.conn.unbind()
                self.conn.disconnect()
                self.logger.info("SMPP connection disconnected successfully")
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

                # Log additional info for debugging
                self.logger.debug(f"Received PDU: {pdu}")
                if hasattr(pdu, 'optional_parameters') and pdu.optional_parameters:
                    self.logger.debug(f"Optional parameters: {pdu.optional_parameters}")

                self.logger.info(f"Received deliver_sm: {short_message}")

                task = SendSubmitSm(self, pdu)
                self.executor_service.submit(task.run)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def submit_short_message(self, **kwargs):
        """Submit a short message."""
        if not self.is_connected():
            raise Exception("Session not connected")
        try:
            return self.conn.send_message(**kwargs)
        except Exception as e:
            self.logger.error(f"Error submitting message: {e}")
            raise