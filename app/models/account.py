from pydantic import BaseModel
from app.models.enums import AccountType, Currency
from datetime import date


class AccountCreate(BaseModel):
    name: str
    type: AccountType
    currency: Currency
    balance: float


class AccountUpdate(BaseModel):
    name: str
    type: AccountType
    currency: Currency
    balance: float


class AccountRead(BaseModel):
    id: int
    name: str
    type: AccountType
    currency: Currency
    balance: float

    class Config:
        from_attributes = True


class AccountWithVariation(BaseModel):
    id: int
    name: str
    type: AccountType
    currency: Currency
    balance: float
    variation: float

    class Config:
        from_attributes = True


class AccountHistoryRead(BaseModel):
    id: int
    balance: float
    variation: float
    date: date
    account_id: int

    class Config:
        from_attributes = True


class TotalHistoryRead(BaseModel):
    id: int
    balance: float
    variation: float
    eur_brl_rate: float
    date: date

    class Config:
        from_attributes = True
