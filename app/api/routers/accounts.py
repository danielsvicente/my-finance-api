from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func
from app.models.account import *
from app.db.schema import *
from app.db.database import SessionLocal, get_db
from typing import List
import yfinance 
import decimal

router = APIRouter(prefix="/accounts")

def variation(current, previous):
    if (previous == 0):
        return 0.00
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
                .join(Account, AccountHistory.account_id == Account.id) \
                .order_by(Account.balance.desc())

    # Execute the query
    return query.all()


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
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
    update_total(db)    
    return db_account


@router.get("/history", response_model=List[AccountHistoryRead])
def get_all_account_history(db: SessionLocal = Depends(get_db)):
    account_history = db.query(AccountHistory).all()
    return account_history


@router.get("/total", response_model=TotalHistoryRead)
def get_total(db: SessionLocal = Depends(get_db)):
    update_total(db)
    result = db.query(TotalHistory).order_by(TotalHistory.date.desc()).first()
    return result
    

@router.get("/total/history", response_model=List[TotalHistoryRead])
def get_all_total_history(db: SessionLocal = Depends(get_db)):
    update_total(db)
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
    update_total(db)
    return db_account


@router.delete("/{account_id}")
def delete_account(account_id: int, db: SessionLocal = Depends(get_db)):
    # FIXME: delete children records before deleting account
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


@router.post("/{account_id}/history/note", response_model=None, status_code=status.HTTP_201_CREATED)
def create_note(account_id: int, note: NoteCreate, db: SessionLocal = Depends(get_db)):
    account_history_id = db.query(AccountHistory.id) \
        .filter(AccountHistory.account_id == account_id, 
                AccountHistory.date.between(note.date.strftime('%Y-%m-01'), note.date.strftime('%Y-%m-31')))
    db_note = Note(
        account_history_id=account_history_id,
        note=note.note,
        date=note.date
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def update_total(db):
    today = date.today()
    eurbrl_rate = decimal.Decimal(yfinance.Ticker("EURBRL=X").history(period="1d")['Close'][0])
    eurbrl_rate = eurbrl_rate.quantize(decimal.Decimal('.0001'), rounding=decimal.ROUND_DOWN)
    total = decimal.Decimal(0.00)
    total_invested = decimal.Decimal(0.00)
    total_uninvested = decimal.Decimal(0.00)
    accounts = db.query(Account).all()
    for account in accounts:
        balance = account.balance
        if account.currency == Currency.BRL:
            balance = account.balance / eurbrl_rate
        total = total + balance
        if account.type == AccountType.INVESTMENT:
            total_invested = total_invested + balance
        else:
            total_uninvested = total_uninvested + balance
    total = total.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
    total_invested = total_invested.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
    total_uninvested = total_uninvested.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
    db_total_hist = db.query(TotalHistory).order_by(TotalHistory.date.desc()).limit(2).all()
    if  len(db_total_hist) == 0 or \
        today.year > db_total_hist[0].date.year or \
       (today.year == db_total_hist[0].date.year and today.month > db_total_hist[0].date.month):
        db_total_hist = TotalHistory(
            balance = total,
            invested = total_invested,
            uninvested = total_uninvested,
            variation = 0.00,
            eur_brl_rate = eurbrl_rate,
            date = today
        )
        db.add(db_total_hist)   
    else:
        db_total_hist[0].balance = total
        db_total_hist[0].invested = total_invested
        db_total_hist[0].uninvested = total_uninvested
        db_total_hist[0].eur_brl_rate = eurbrl_rate
        db_total_hist[0].date = today
        if len(db_total_hist) > 1:
            db_total_hist[0].variation = variation(float(db_total_hist[0].balance), float(db_total_hist[1].balance))
    db.commit()



