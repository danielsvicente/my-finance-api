from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, String, Enum, Numeric, ForeignKey, Date
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from typing import List
import enum
from datetime import date, datetime
import decimal
import yfinance as yf

app = FastAPI()

class Base(DeclarativeBase):
    pass

class AccountType(enum.Enum):
    CURRENT = "CURRENT"
    INVESTMENT = "INVESTMENT"

class Currency(enum.Enum):
    EUR = "EUR"
    BRL = "BRL"

class AccountStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(Enum(AccountType), nullable=False)
    currency: Mapped[str] = mapped_column(Enum(Currency), nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # status: Mapped[str] = mapped_column(Enum(AccountStatus), nullable=False)
    history: Mapped[List["AccountHistory"]] = relationship(back_populates="account")

class AccountHistory(Base):
    __tablename__ = 'account_history'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id : Mapped[int]= mapped_column(ForeignKey("account.id"), nullable=False)
    account: Mapped["Account"] = relationship(back_populates="history")
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # variation: Mapped[float] = mapped_column()
    date: Mapped[str] = mapped_column(Date(), nullable=False)
    # note: Mapped[str] = mapped_column()

class TotalHistory(Base):
    __tablename__ = "total_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # variation: Mapped[float] = mapped_column()
    eur_brl_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    date: Mapped[str] = mapped_column(Date(), nullable=False)
    # note: Mapped[str] = mapped_column()
    

DATABASE_URL = "sqlite:///./dashboard.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('pragma foreign_keys=ON')

from sqlalchemy import event
event.listen(engine, 'connect', _fk_pragma_on_connect)

Base.metadata.create_all(bind=engine)

### Account
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
        orm_mode = True

### Account History
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
        orm_mode = True

### Total History
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
        orm_mode = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CORS middleware to allow requests from different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You should specify the actual origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/accounts/", response_model=List[AccountRead])
def get_accounts(db: SessionLocal = Depends(get_db)):
    accounts = db.query(Account).all()
    return accounts

@app.get("/accounts/total/")
def get_total(db: SessionLocal = Depends(get_db)):
    today = date.today()
    eurbrl_rate = decimal.Decimal(yf.Ticker("EURBRL=X").history(period="1d")['Close'][0])
    eurbrl_rate = eurbrl_rate.quantize(decimal.Decimal('.0001'), rounding=decimal.ROUND_DOWN)
    total = decimal.Decimal(0.00)
    result = db.query(Account.balance, Account.currency).all()
    for row in result:
        if row.currency == Currency.BRL:
            total = total + (row.balance / eurbrl_rate)
        else:
            total = total + row.balance
    
    total = total.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)

    db_total_hist = db.query(TotalHistory).order_by(TotalHistory.date.desc()).first()
    if  db_total_hist is None or \
        today.year > db_total_hist.date.year or \
       (today.year == db_total_hist.date.year and today.month > db_total_hist.date.month):
        
        db_total_hist = TotalHistory(
            balance = total,
            eur_brl_rate = eurbrl_rate,
            date = today
        )
        db.add(db_total_hist)   
    else:
        db_total_hist.balance = total
        db_total_hist.eur_brl_rate = eurbrl_rate
        db_total_hist.date = today
    db.commit()
    return total

@app.get("/accounts/{account_id}", response_model=AccountCreate)
def get_account(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return db_account

@app.post("/accounts/", response_model=AccountCreate)
def create_account(account: AccountCreate, db: SessionLocal = Depends(get_db)):

    # insert account
    db_account = Account(
        name=account.name,
        type=account.type,
        currency=account.currency,
        balance=account.balance
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)

    # insert account history
    db_account_history = AccountHistory(
        account_id = db_account.id,
        balance = db_account.balance,
        date = date.today()
    )
    db.add(db_account_history)
    db.commit()

    get_total(db)    

    return db_account

@app.put("/accounts/{account_id}", response_model=AccountUpdate)
def update_account(account_id: int, account: AccountUpdate, db: SessionLocal = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db_account.name = account.name
    db_account.type = account.type
    db_account.currency = account.currency
    db_account.balance = account.balance
    db.commit()
    db.refresh(db_account)

    db_acc_hist = db.query(AccountHistory).filter(AccountHistory.account_id == account_id).order_by(AccountHistory.date.desc()).first()
    if db_acc_hist is None:
        raise HTTPException(status_code=404, detail="Account history not found")
    
    today = date.today()

    if today.year > db_acc_hist.date.year or (today.year == db_acc_hist.date.year and today.month > db_acc_hist.date.month):
        db_account_history = AccountHistory(
            account_id = db_account.id,
            balance = db_account.balance,
            date = today
        )
        db.add(db_account_history)
    else:
        db_acc_hist.balance = account.balance
        db_acc_hist.date = today

    db.commit()
    get_total(db)
    return db_account

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(db_account)
    db.commit()
    return {"message": "Account deleted successfully"}

@app.get("/account-history/", response_model=List[AccountHistoryRead])
def get_all_account_history(db: SessionLocal = Depends(get_db)):
    account_history = db.query(AccountHistory).all()
    return account_history

@app.get("/account-history/{account_id}", response_model=List[AccountHistoryRead])
def get_account_history(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account_history = db.query(AccountHistory).filter(Account.id == account_id)
    if db_account_history is None:
        raise HTTPException(status_code=404, detail="No data found for this account")
    return db_account_history

@app.get("/total-history/", response_model=List[TotalHistoryRead])
def get_all_total_history(db: SessionLocal = Depends(get_db)):
    get_total(db)
    result = db.query(TotalHistory).all()
    return result

@app.get("/")
def read_root():
    return {"message": "Welcome to your dashboard!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)