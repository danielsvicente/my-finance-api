import enum

class AccountType(enum.Enum):
    CURRENT = "CURRENT"
    INVESTMENT = "INVESTMENT"

class Currency(enum.Enum):
    EUR = "EUR"
    BRL = "BRL"

class AccountStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"