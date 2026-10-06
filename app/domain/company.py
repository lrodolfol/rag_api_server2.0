"""Company registration domain models.

Model the payload a client sends to register (or update) its company. Field
names follow the public JSON contract defined in the tech spec; mixed
Portuguese/English names (``descricao``, ``detalhes``) are kept because they are
part of that external contract.
"""

from pydantic import BaseModel, EmailStr, Field


class CompanyData(BaseModel):
    """Business details provided by the client for a single company."""

    name: str = Field(min_length=1)
    descricao: str = Field(min_length=1)
    email: EmailStr
    address: str = Field(min_length=1)
    telephone: str = Field(min_length=1)
    detalhes: str = Field(min_length=1)


class CompanyRegistrationRequest(BaseModel):
    """Top-level registration request: the client code plus its company data."""

    user_code: str = Field(min_length=1)
    request: CompanyData
