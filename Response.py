# Response.py
import urllib.request
import urllib.parse
import urllib.error
import logging
import uuid
from SmppConfig import SmppConfig
import smpplib.consts

class Response(SmppConfig):
    """USSD Response handler - processes incoming messages and sends responses"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def _generate_session_id(self) -> str:
        """Generates a unique session ID."""
        return uuid.uuid4().hex

    def process_deliver_sm_request(self, smpp_client, pdu):
        """Process incoming DeliverSM request"""
        try:
            msisdn = pdu.source_addr.decode('utf-8')
            payload = pdu.short_message.decode('utf-8', errors='ignore')

            print(f"RECEIVING USSD::::::::::{payload}")

            if payload.strip():
                session_id = None
                if hasattr(pdu, 'optional_parameters') and pdu.optional_parameters:
                    for tag, value in pdu.optional_parameters.items():
                        # Check for session info in different possible tag formats
                        if (tag == 'its_session_info' or
                                (hasattr(smpplib.consts, 'TAG_ITS_SESSION_INFO') and tag == smpplib.consts.TAG_ITS_SESSION_INFO) or
                                (hasattr(smpplib.consts, 'Tag') and hasattr(smpplib.consts.Tag, 'its_session_info') and tag == smpplib.consts.Tag.its_session_info)):
                            session_id = str(value.decode())

                if session_id is None:
                    session_id = self._generate_session_id()

                self.logger.info(f"MSISDN: {msisdn} INPUT: {payload} "
                                 f"NEWREQUEST: {session_id} SESSION: {session_id}")

                encoded_payload = urllib.parse.quote(payload, safe='')
                call_url = f"{self.process_url}?msisdn={msisdn}&input={encoded_payload}&sessionid={session_id}"
                # if session_id:
                #     call_url += f"&sessionid={session_id}"

                menu_response = self.http_request(call_url)

                # Only try to send if we're still connected
                if smpp_client.is_connected():
                    self.send_submit_sm(smpp_client, menu_response, self.service_code,
                                        msisdn, session_id)
                else:
                    self.logger.warning("Cannot send response - SMPP client is not connected")

        except Exception as e:
            self.logger.error(f"Error processing DeliverSM request: {e}", exc_info=True)

    def send_submit_sm(self, smpp_client, message: str, source: str, destination: str,
                       session_id: str or None):
        """Send USSD response message via SMPP"""
        try:
            optional_parameters = {}

            # Handle session info - check for different constant names
            if session_id and session_id != "0":
                session_tag = None
                # Check various possible tag names
                if hasattr(smpplib.consts, 'TAG_ITS_SESSION_INFO'):
                    session_tag = smpplib.consts.TAG_ITS_SESSION_INFO
                elif hasattr(smpplib.consts, 'Tag') and hasattr(smpplib.consts.Tag, 'its_session_info'):
                    session_tag = smpplib.consts.Tag.its_session_info
                elif hasattr(smpplib.consts, 'its_session_info'):
                    session_tag = smpplib.consts.its_session_info

                if session_tag:
                    optional_parameters[session_tag] = session_id.encode()

            end_session = message[:3].upper() if len(message) >= 3 else ""

            # Handle USSD service op - check for different constant names
            ussd_op_value = b'\x11' if end_session == "END" else b'\x02'

            ussd_tag = None
            # Check various possible tag names for USSD service op
            if hasattr(smpplib.consts, 'TAG_USSD_SERVICE_OP'):
                ussd_tag = smpplib.consts.TAG_USSD_SERVICE_OP
            elif hasattr(smpplib.consts, 'Tag') and hasattr(smpplib.consts.Tag, 'ussd_service_op'):
                ussd_tag = smpplib.consts.Tag.ussd_service_op
            elif hasattr(smpplib.consts, 'ussd_service_op'):
                ussd_tag = smpplib.consts.ussd_service_op

            if ussd_tag:
                optional_parameters[ussd_tag] = ussd_op_value

            if end_session == "END":
                message = message[3:].strip()

            # Convert optional_parameters dict to list of TLV tuples if needed
            optional_params_list = []
            for tag, value in optional_parameters.items():
                optional_params_list.append((tag, value))

            smpp_client.submit_short_message(
                source_addr=source,
                destination_addr=destination,
                short_message=message.encode('ascii', errors='ignore'),
                service_type=self.service_type,
                source_addr_ton=smpplib.consts.SMPP_TON_INTL,
                source_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                data_coding=smpplib.consts.SMPP_ENCODING_DEFAULT,
                optional_parameters=optional_params_list or None,
            )

            self.logger.info("Message submitted successfully")

        except Exception as e:
            self.logger.error(f"Error sending SubmitSM: {e}")

    def http_request(self, url: str) -> str:
        """Make HTTP request to process USSD"""
        print(f"====================Sending request to local server:: {{ {url} }}")

        default_response = "System Error. Please try again later. Thanks"

        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                response_data = response.read().decode('utf-8')
                print(f"url call response::{response_data}")
                return response_data.strip() if response_data else default_response

        except urllib.error.URLError as e:
            self.logger.error(f"HTTP request failed: {e}")
            return default_response
        except Exception as e:
            self.logger.error(f"Unexpected error in HTTP request: {e}")
            return default_response
