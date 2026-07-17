from abc import ABC, abstractmethod
from typing import Optional


class InboundMessage:
    def __init__(self, channel_id: str, from_number: str, body: str,
                 message_id: str, timestamp: int):
        self.channel_id = channel_id
        self.from_number = from_number
        self.body = body
        self.message_id = message_id
        self.timestamp = timestamp


class WhatsAppProvider(ABC):
    @abstractmethod
    def send_text(self, channel_id: str, to: str, body: str) -> None:
        ...

    @abstractmethod
    def send_document(self, channel_id: str, to: str, file_url: str,
                      caption: Optional[str] = None) -> None:
        ...

    @abstractmethod
    def parse_inbound(self, payload: dict) -> InboundMessage:
        ...
