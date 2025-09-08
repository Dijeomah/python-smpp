import urllib.request
import urllib.parse
import urllib.error
import logging
from SmppConfig import SmppConfig
import smpplib.consts

class Response(SmppConfig):
    """USSD Response handler - processes incoming messages and sends responses"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def process_deliver_sm_request(self, smpp_client, pdu):
        """Process incoming DeliverSM request"""
        try:
            msisdn = pdu.source_addr.decode('utf-8')
            payload = pdu.short_message.decode('utf-8', errors='ignore')

            print(f"RECEIVING USSD::::::::::{payload}")

            if payload.strip():
                session_id = "0"  # Default session ID
                if pdu.optional_parameters:
                    for tag, value in pdu.optional_parameters.items():
                        if tag == 'its_session_info':
                            session_id = str(value.decode())

                self.logger.info(f"MSISDN: {msisdn} INPUT: {payload} "
                                 f"NEWREQUEST: {session_id} SESSION: {session_id}")

                encoded_payload = urllib.parse.quote(payload, safe='')
                call_url = (f"{self.process_url}?msisdn={msisdn}&sessionid={session_id}"
                            f"&input={encoded_payload}&sendussd_port={self.send_ussd_port}"
                            f"&network={self.network}")

                menu_response = self.http_request(call_url)

                self.send_submit_sm(smpp_client, menu_response, self.service_code,
                                    msisdn, session_id)

        except Exception as e:
            self.logger.error(f"Error processing DeliverSM request: {e}", exc_info=True)

    def send_submit_sm(self, smpp_client, message: str, source: str, destination: str,
                       session_id: str):
        """Send USSD response message via SMPP"""
        try:
            optional_parameters = []
            if session_id != "0":
                optional_parameters.append(smpplib.consts.TLV(smpplib.consts.Tag.its_session_info, session_id.encode()))

            end_session = message[:3].upper() if len(message) >= 3 else ""

            if end_session == "END":
                optional_parameters.append(smpplib.consts.TLV(smpplib.consts.Tag.ussd_service_op, b'\x11'))
                message = message[3:].strip()
            else:
                optional_parameters.append(smpplib.consts.TLV(smpplib.consts.Tag.ussd_service_op, b'\x02'))

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
                optional_parameters=optional_parameters,
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
