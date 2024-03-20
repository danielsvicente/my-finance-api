from pydantic import BaseModel
from app.models.enums import AccountType, Currency
from datetime import date
from typing import List


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
    notes: List["Note"]

    class Config:
        from_attributes = True


class TotalHistoryRead(BaseModel):
    id: int
    balance: float
    invested: float
    uninvested: float
    variation: float
    eur_brl_rate: float
    date: date

    class Config:
        from_attributes = True


class Note(BaseModel):
    id: int
    account_history_id: int
    note: str
    date: date
    

class NoteCreate(BaseModel):
    note: str
    date: date