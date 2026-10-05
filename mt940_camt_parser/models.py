from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class EntryType(str, Enum):
    CREDIT = "CRDT"  # Inflow / Tahsilat
    DEBIT = "DBIT"   # Outflow / Tediye


@dataclass(frozen=True)
class Balance:
    entry_type: EntryType
    amount: Decimal
    currency: str
    date: date


@dataclass(frozen=True)
class TransactionEntry:
    entry_id: str
    booking_date: date
    value_date: date
    entry_type: EntryType
    amount: Decimal
    currency: str
    description: str
    transaction_code: Optional[str] = None
    account_servicer_ref: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_iban: Optional[str] = None


@dataclass(frozen=True)
class Statement:
    statement_id: str
    account_identification: str  # IBAN or bank internal account number
    currency: str
    opening_balance: Balance
    closing_balance: Balance
    entries: List[TransactionEntry] = field(default_factory=list)
    sequence_number: Optional[str] = None
    source_format: str = "UNKNOWN"

    @property
    def total_credits(self) -> Decimal:
        return sum(
            (e.amount for e in self.entries if e.entry_type == EntryType.CREDIT),
            Decimal("0.00")
        )

    @property
    def total_debits(self) -> Decimal:
        return sum(
            (e.amount for e in self.entries if e.entry_type == EntryType.DEBIT),
            Decimal("0.00")
        )

    @property
    def entry_count(self) -> int:
        return len(self.entries)
