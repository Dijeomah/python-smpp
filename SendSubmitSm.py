import logging
from SmppConfig import SmppConfig
from Response import Response

class SendSubmitSm(SmppConfig):
    """Handles USSD message processing and response"""

    def __init__(self, smpp_client, pdu):
        super().__init__()
        self.smpp_client = smpp_client
        self.pdu = pdu
        self.logger = logging.getLogger(__name__)
        self.response_handler = Response()

    def run(self):
        """Process the incoming USSD message"""
        try:
            self.response_handler.process_deliver_sm_request(self.smpp_client, self.pdu)
        except Exception as e:
            self.logger.error(f"Error Sending submitSM: {e}", exc_info=True)
