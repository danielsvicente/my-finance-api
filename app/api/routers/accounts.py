from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from app.models.account import *
from app.db.schema import *
from app.db.database import SessionLocal, get_db
from typing import List
import yfinance 
import decimal

router = APIRouter(prefix="/accounts")

def variation(current, previous):
    return (current * 100.0 / previous) - 100.0


@router.get("/", response_model=List[AccountWithVariation])
def get_accounts(db: SessionLocal = Depends(get_db)):

    # Subquery to find the latest date for each account_id
    subquery = db.query(AccountHistory.account_id, func.max(AccountHistory.date).label('latest')) \
                    .group_by(AccountHistory.account_id) \
                    .subquery()

    # Joining AccountHistory with the subquery and Account
    query = db.query(Account.id, Account.name, Account.type, Account.currency, Account.balance, AccountHistory.variation) \
                .join(subquery, AccountHistory.account_id == subquery.c.account_id) \
                .filter(AccountHistory.date == subquery.c.latest) \
                .join(Account, AccountHistory.account_id == Account.id)

    # Execute the query
    return query.all()


@router.post("/", response_model=AccountCreate)
def create_account(account: AccountCreate, db: SessionLocal = Depends(get_db)):
    db_account = Account(
        name=account.name,
        type=account.type,
        currency=account.currency,
        balance=account.balance
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    db_account_history = AccountHistory(
        account_id = db_account.id,
        balance = db_account.balance,
        variation = 0.00,
        date = date.today()
    )
    db.add(db_account_history)
    db.commit()
    get_total(db)    
    return db_account


@router.get("/history", response_model=List[AccountHistoryRead])
def get_all_account_history(db: SessionLocal = Depends(get_db)):
    account_history = db.query(AccountHistory).all()
    return account_history


@router.get("/total")
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
    db_total_hist = db.query(TotalHistory).order_by(TotalHistory.date.desc()).limit(2).all()
    if  len(db_total_hist) == 0 or \
        today.year > db_total_hist[0].date.year or \
       (today.year == db_total_hist[0].date.year and today.month > db_total_hist[0].date.month):
        db_total_hist = TotalHistory(
            balance = total,
            variation = 0.00,
            eur_brl_rate = eurbrl_rate,
            date = today
        )
        db.add(db_total_hist)   
    else:
        db_total_hist[0].balance = total
        db_total_hist[0].eur_brl_rate = eurbrl_rate
        db_total_hist[0].date = today
        if len(db_total_hist) > 1:
            db_total_hist[0].variation = variation(float(db_total_hist[0].balance), float(db_total_hist[1].balance))
    db.commit()
    return total
    

@router.get("/total/history", response_model=List[TotalHistoryRead])
def get_all_total_history(db: SessionLocal = Depends(get_db)):
    get_total(db)
    result = db.query(TotalHistory).order_by(TotalHistory.date.asc()).all()
    return result


@router.get("/{account_id}", response_model=AccountWithVariation)
def get_account(account_id: int, db: SessionLocal = Depends(get_db)):

    # Subquery to find the latest record
    subquery = db.query(AccountHistory.account_id, func.max(AccountHistory.date).label('latest')) \
                    .filter(AccountHistory.account_id == account_id) \
                    .group_by(AccountHistory.account_id) \
                    .subquery()

    # Joining AccountHistory with the subquery and Account
    query = db.query(Account.id, Account.name, Account.type, Account.currency, Account.balance, AccountHistory.variation) \
                .join(subquery, AccountHistory.account_id == subquery.c.account_id) \
                .filter(AccountHistory.date == subquery.c.latest) \
                .join(Account, AccountHistory.account_id == Account.id)
    
    print(query)

    # Execute the query
    return query.one()


@router.put("/{account_id}", response_model=AccountUpdate)
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
    db_acc_hist = db.query(AccountHistory) \
                    .filter(AccountHistory.account_id == account_id) \
                    .order_by(AccountHistory.date.desc()) \
                    .limit(2) \
                    .all()
    if len(db_acc_hist) == 0:
        raise HTTPException(status_code=404, detail="Account history not found")
    today = date.today()

    # if it's a new month, create a new entry
    if today.year > db_acc_hist[0].date.year or \
      (today.year == db_acc_hist[0].date.year and today.month > db_acc_hist[0].date.month):
        db_account_history = AccountHistory(
            account_id = db_account.id,
            balance = db_account.balance,
            variation = variation(float(db_account.balance), float(db_acc_hist[0].balance)),
            date = today
        )
        db.add(db_account_history)
    else:
        db_acc_hist[0].balance = account.balance
        db_acc_hist[0].date = today
        if len(db_acc_hist) > 1:
            db_acc_hist[0].variation = variation(float(db_acc_hist[0].balance), float(db_acc_hist[1].balance))
    db.commit()
    get_total(db)
    return db_account


@router.delete("/{account_id}")
def delete_account(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(db_account)
    db.commit()
    return {"message": "Account deleted successfully"}


@router.get("/{account_id}/history", response_model=List[AccountHistoryRead])
def get_account_history(account_id: int, db: SessionLocal = Depends(get_db)):
    db_account_history = db.query(AccountHistory) \
        .filter(AccountHistory.account_id == account_id) \
        .order_by(AccountHistory.date.desc())
    if db_account_history is None:
        raise HTTPException(status_code=404, detail="No data found for this account")
    return db_account_history




