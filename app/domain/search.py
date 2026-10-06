"""Search request payloads for the two supported channels.

WhatsApp messages arrive from the integration gateway (Evolution API) while the
online chat payload comes from the website widget. Both are validated at the
API boundary before any search is performed.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress


class WhatsAppSearchPayload(BaseModel):
    """Message received from the WhatsApp integration gateway."""

    model_config = ConfigDict(populate_by_name=True)

    number: str = Field(min_length=1)
    text: str = Field(min_length=1)
    delay: int | None = None
    link_preview: Annotated[bool, Field(alias="linkPreview")] = False


class OnlineChatSearchPayload(BaseModel):
    """Message received from the online chat widget."""

    message: str = Field(min_length=1)
    user_code: str = Field(min_length=1)
    user_ip: IPvAnyAddress
