import logging
from typing import Dict, Any, Optional
from SmppConfig import SmppConfig
from Response import Response

class DeliverSm:
    """Represents an DeliverSm message - placeholder for actual SMPP library"""

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def get_dest_address(self) -> str:
        return self.data.get('dest_address', '')

    def get_source_addr(self) -> str:
        return self.data.get('source_addr', '')

    def get_short_message(self) -> bytes:
        return self.data.get('short_message', b'')

    def get_optional_parameter(self, tag: str) -> Optional[Any]:
        return self.data.get('optional_parameters', {}).get(tag)


class OptionalParameter:
    """SMPP Optional Parameter classes"""

    class ItsSessionInfo:
        def __init__(self, value):
            self.value = value

        def get_value(self):
            return self.value

    class UssdServiceOp:
        def __init__(self, value: int):
            self.value = value

        def get_value(self):
            return self.value


class SendSubmitSm(SmppConfig):
    """Handles USSD message processing and response"""

    def __init__(self, smpp_session, deliver_sm: DeliverSm):
        super().__init__()
        self._conn = smpp_session
        self._deliver_sm = deliver_sm
        self.logger = logging.getLogger(__name__)
        self.response_handler = Response()

    def run(self):
        """Process the incoming USSD message"""
        try:
            self.response_handler.process_deliver_sm_request(self._conn, self._deliver_sm)
        except Exception as e:
            self.logger.error(f"Error Sending submitSM: {e}", exc_info=True)
