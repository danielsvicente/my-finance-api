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

class AccountHistoryCreate(BaseModel):
    balance: float
    date: date
    account_id: int

class AccountHistoryUpdate(BaseModel):
    balance: float
    date: date
    account_id: int

class AccountHistoryRead(BaseModel):
    id: int
    balance: float
    date: date
    account_id: int

    class Config:
        from_attributes = True

class TotalHistoryCreate(BaseModel):
    balance: float
    eur_brl_rate: float
    date: date

class TotalHistoryUpdate(BaseModel):
    balance: float
    eur_brl_rate: float
    date: date

class TotalHistoryRead(BaseModel):
    id: int
    balance: float
    eur_brl_rate: float
    date: date

    class Config:
        from_attributes = True
