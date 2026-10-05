"""
mt940-camt-parser: Zero-dependency SWIFT MT940 and ISO 20022 CAMT.053 parser in Python.
"""

from .models import Balance, EntryType, Statement, TransactionEntry
from .mt940 import parse_mt940
from .camt053 import parse_camt053
from typing import List


def parse_statement(content: str) -> List[Statement]:
    """
    Auto-detects format (XML CAMT.053 vs SWIFT MT940) and returns normalized statements.
    """
    stripped = content.strip()
    if stripped.startswith("<?xml") or "<Document" in stripped or "<BkToCstmrStmt" in stripped:
        return parse_camt053(stripped)
    return parse_mt940(stripped)


__all__ = [
    "Balance",
    "EntryType",
    "Statement",
    "TransactionEntry",
    "parse_mt940",
    "parse_camt053",
    "parse_statement",
]

__version__ = "0.1.0"
