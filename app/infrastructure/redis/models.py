"""Redis history store models.

Defines the conversation channels whose history is kept in Redis. Each channel
maps to its own key prefix so WhatsApp and online-chat histories never collide,
as required by the technical specification.
"""

from enum import Enum


class HistoryChannel(str, Enum):
    """Channel a conversation history belongs to.

    The value is the Redis key prefix for that channel; the per-user key is
    built by appending the user code, keeping every channel isolated.
    """

    WHATSAPP = "users_histotic_whatsapp"
    ONLINE = "users_histotic_online"
