import urllib.request
import urllib.parse
import urllib.error
import logging
import threading
from typing import Dict, Any
from SmppConfig import SmppConfig
from SendSubmitSm import DeliverSm



class ResponseProcessDeliverSMInThread:
    """Thread worker for processing DeliverSM messages"""

    def __init__(self, response_handler, conn, deliver_sm: DeliverSm):
        self.response_handler = response_handler
        self._conn = conn
        self._pack = deliver_sm
        self.logger = logging.getLogger(__name__)

    def run(self):
        """Process DeliverSM in thread"""
        try:
            self.response_handler.process_deliver_sm_request(self._conn, self._pack)
        except Exception as e:
            self.logger.error(f"Error Processing Deliver SM: {e}", exc_info=True)


class Response(SmppConfig):
    """USSD Response handler - processes incoming messages and sends responses"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def process_deliver_sm_request(self, conn, deliver_sm: DeliverSm):
        """Process incoming DeliverSM request"""
        try:
            msgs_dest = deliver_sm.get_dest_address()
            msisdn = deliver_sm.get_source_addr()
            payload = deliver_sm.get_short_message().decode('utf-8', errors='ignore')

            print(f"RECEIVING USSD::::::::::{payload}")

            if payload.strip():
                # Extract session info from optional parameters
                its_session_info = deliver_sm.get_optional_parameter('ITS_SESSION_INFO')
                if its_session_info:
                    session_id = str(its_session_info.get_value())
                else:
                    session_id = "0"  # Default session ID

                self.logger.info(f"MSISDN: {msisdn} INPUT: {payload} "
                                 f"NEWREQUEST: {session_id} SESSION: {session_id}")

                # Build request URL
                encoded_payload = urllib.parse.quote(payload, safe='')
                call_url = (f"{self.process_url}?msisdn={msisdn}&sessionid={session_id}"
                            f"&input={encoded_payload}&sendussd_port={self.send_ussd_port}"
                            f"&network={self.network}")

                # Make HTTP request to process the USSD
                menu_response = self.http_request(call_url)

                # Send response back via SMPP
                self.send_submit_sm(conn, menu_response, self.service_code,
                                    msisdn, session_id)

        except Exception as e:
            self.logger.error(f"Error processing DeliverSM request: {e}", exc_info=True)

    def send_submit_sm(self, conn, message: str, source: str, destination: str,
                       session_id: str):
        """Send USSD response message via SMPP"""
        try:
            # Create optional parameters for USSD
            session_info_param = {
                'tag': 'ITS_SESSION_INFO',
                'value': int(session_id)
            }

            # Check if this is an end session message
            end_session = message[:3].upper() if len(message) >= 3 else ""

            if end_session == "END":
                # End session operation
                service_op_param = {
                    'tag': 'USSD_SERVICE_OP',
                    'value': 17  # End session
                }
                # Remove "END" from the beginning of message
                message = message[3:].strip()
            else:
                # Continue session operation
                service_op_param = {
                    'tag': 'USSD_SERVICE_OP',
                    'value': 2  # Continue session
                }

            optional_parameters = [session_info_param, service_op_param]

            # Submit the message
            conn.submit_short_message(
                service_type=self.service_type,
                source_ton='INTERNATIONAL',  # TypeOfNumber.INTERNATIONAL
                source_npi='ISDN',          # NumberingPlanIndicator.ISDN
                source_addr=source,
                dest_ton='INTERNATIONAL',
                dest_npi='ISDN',
                dest_addr=destination,
                esm_class={},               # ESMClass()
                protocol_id=0,
                priority_flag=0,
                schedule_delivery_time=None,
                validity_period=None,
                registered_delivery={'default': True},  # RegisteredDelivery(SMSCDeliveryReceipt.DEFAULT)
                replace_if_present_flag=0,
                data_coding={'alphabet': 'ALPHA_8_BIT'},  # GeneralDataCoding(Alphabet.ALPHA_8_BIT)
                sm_default_msg_id=0,
                short_message=message.encode('ascii', errors='ignore'),
                optional_parameters=optional_parameters
            )

            self.logger.info("Message submitted successfully")

        except Exception as e:
            self.logger.error(f"Error sending SubmitSM: {e}")

    def http_request(self, url: str) -> str:
        """Make HTTP request to process USSD"""
        print(f"====================Sending request to local server:: {{ {url} }}")

        default_response = "System Error. Please try again later. Thanks"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                print(f"url call response::{response_data}")
                return response_data.strip() if response_data else default_response

        except urllib.error.URLError as e:
            self.logger.error(f"HTTP request failed: {e}")
            return default_response
        except Exception as e:
            self.logger.error(f"Unexpected error in HTTP request: {e}")
            return default_response

    def process_deliver_sm_in_thread(self, conn, deliver_sm: DeliverSm):
        """Process DeliverSM in a separate thread"""
        processor = ResponseProcessDeliverSMInThread(self, conn, deliver_sm)

        # Run in executor service thread pool
        if hasattr(self, 'executor_service') and self.executor_service:
            self.executor_service.submit(processor.run)
        else:
            # Fallback to creating a new thread
            thread = threading.Thread(target=processor.run, daemon=True)
            thread.start()