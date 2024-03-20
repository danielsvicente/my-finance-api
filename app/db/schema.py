from sqlalchemy import String, Enum, Numeric, ForeignKey, Date
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column, relationship
from typing import List
from app.models.enums import *

class Base(DeclarativeBase):
    pass

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
    variation: Mapped[float] = mapped_column()
    date: Mapped[str] = mapped_column(Date(), nullable=False)
    notes: Mapped[List["Note"]] = relationship(back_populates="account_history")

class TotalHistory(Base):
    __tablename__ = "total_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    invested: Mapped[float] = mapped_column(Numeric(12, 2))
    uninvested: Mapped[float] = mapped_column(Numeric(12, 2))
    variation: Mapped[float] = mapped_column()
    eur_brl_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    date: Mapped[str] = mapped_column(Date(), nullable=False)

class Note(Base):
    __tablename__ = "note"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_history_id: Mapped[int] = mapped_column(ForeignKey("account_history.id"), nullable=False)
    account_history: Mapped["AccountHistory"] = relationship(back_populates="notes")
    note: Mapped[str] = mapped_column(nullable=False)
    date: Mapped[str] = mapped_column(Date(), nullable=False)
