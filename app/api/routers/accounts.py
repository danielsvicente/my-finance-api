from fastapi import APIRouter, HTTPException, Depends
from app.models.account import *
from app.db.schema import *
from app.db.database import SessionLocal, get_db
from typing import List
import yfinance 
import decimal

router = APIRouter()

@router.get("/accounts/", response_model=List[AccountRead])
def get_accounts(db: SessionLocal = Depends(get_db)):
    accounts = db.query(Account).all()
    return accounts

@router.get("/accounts/total/")
def get_total(db: SessionLocal = Depends(get_db)):
    today = date.today()
    eurbrl_rate = decimal.Decimal(yfinance.Ticker("EURBRL=X").history(period="1d")['Close'][0])
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

@router.get("/accounts/{account_id}", response_model=AccountCreate)
def get_account(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return db_account

@router.post("/accounts/", response_model=AccountCreate)
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

@router.put("/accounts/{account_id}", response_model=AccountUpdate)
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

@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(db_account)
    db.commit()
    return {"message": "Account deleted successfully"}

@router.get("/account-history/", response_model=List[AccountHistoryRead])
def get_all_account_history(db: SessionLocal = Depends(get_db)):
    account_history = db.query(AccountHistory).all()
    return account_history

@router.get("/account-history/{account_id}", response_model=List[AccountHistoryRead])
def get_account_history(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account_history = db.query(AccountHistory).filter(Account.id == account_id)
    if db_account_history is None:
        raise HTTPException(status_code=404, detail="No data found for this account")
    return db_account_history

@router.get("/total-history/", response_model=List[TotalHistoryRead])
def get_all_total_history(db: SessionLocal = Depends(get_db)):
    get_total(db)
    result = db.query(TotalHistory).all()
    return result

