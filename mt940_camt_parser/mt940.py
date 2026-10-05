from datetime import date
from decimal import Decimal
import re
from typing import List, Optional
from .models import Balance, EntryType, Statement, TransactionEntry


def _parse_swift_date(date_str: str) -> date:
    year = 2000 + int(date_str[0:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])
    return date(year, month, day)


def _parse_swift_amount(amount_str: str) -> Decimal:
    return Decimal(amount_str.replace(",", "."))


def _parse_balance_tag(content: str) -> Balance:
    indicator_char = content[0]
    entry_type = EntryType.CREDIT if indicator_char == "C" else EntryType.DEBIT
    date_val = _parse_swift_date(content[1:7])
    currency = content[7:10]
    amount = _parse_swift_amount(content[10:])
    return Balance(
        entry_type=entry_type,
        amount=amount,
        currency=currency,
        date=date_val
    )


def parse_mt940(raw_content: str) -> List[Statement]:
    lines = raw_content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    tags: List[tuple[str, str]] = []
    
    current_tag: Optional[str] = None
    current_val: List[str] = []

    tag_regex = re.compile(r"^:([0-9]{2}[A-Z]?):(.*)$")

    for line in lines:
        match = tag_regex.match(line)
        if match:
            if current_tag is not None:
                tags.append((current_tag, "\n".join(current_val).strip()))
            current_tag = match.group(1)
            current_val = [match.group(2)]
        elif current_tag is not None:
            current_val.append(line)

    if current_tag is not None:
        tags.append((current_tag, "\n".join(current_val).strip()))

    statements: List[Statement] = []
    
    stmt_ref = "UNKNOWN"
    account = "UNKNOWN"
    seq = None
    opening_bal: Optional[Balance] = None
    closing_bal: Optional[Balance] = None
    entries: List[TransactionEntry] = []
    pending_line_entry: Optional[dict] = None

    def commit_pending_entry(descr: str = ""):
        nonlocal pending_line_entry
        if pending_line_entry is not None:
            entries.append(TransactionEntry(
                entry_id=pending_line_entry["ref"] or f"TX-{len(entries)+1}",
                booking_date=pending_line_entry["booking_date"],
                value_date=pending_line_entry["value_date"],
                entry_type=pending_line_entry["type"],
                amount=pending_line_entry["amount"],
                currency=opening_bal.currency if opening_bal else "TRY",
                description=descr.strip(),
                account_servicer_ref=pending_line_entry["ref"]
            ))
            pending_line_entry = None

    for tag, val in tags:
        if tag == "20":
            stmt_ref = val
        elif tag == "25":
            account = val.replace("/", "").strip()
        elif tag in ("28C", "28"):
            seq = val
        elif tag in ("60F", "60M"):
            opening_bal = _parse_balance_tag(val)
        elif tag == "61":
            commit_pending_entry()
            # Tag 61: 6 chars date + optional 4 chars entry date + C/D/RC/RD + optional 1 letter + amount with comma + rest
            # Example: 2610021002CR12500,00NTRFNONREF//REF987654
            val_date = _parse_swift_date(val[:6])
            idx = 6
            entry_date = val_date
            if len(val) > 10 and val[6:10].isdigit():
                entry_date = date(val_date.year, int(val[6:8]), int(val[8:10]))
                idx = 10

            # Match indicator C, D, RC, RD
            if val[idx:idx+2] in ("RC", "RD"):
                type_indicator = val[idx:idx+2]
                idx += 2
            else:
                type_indicator = val[idx:idx+1]
                idx += 1

            entry_type = EntryType.CREDIT if "C" in type_indicator else EntryType.DEBIT

            # Optional 1 letter currency indicator
            if idx < len(val) and val[idx].isalpha() and not val[idx:idx+1].isdigit():
                idx += 1

            # Match amount
            amt_match = re.match(r"^([0-9,]+)(.*)$", val[idx:], re.DOTALL)
            if amt_match:
                amount = _parse_swift_amount(amt_match.group(1))
                rest = amt_match.group(2)
                
                # Bank reference often follows '//'
                ref = ""
                if "//" in rest:
                    ref = rest.split("//", 1)[1].split("\n", 1)[0].strip()
                elif rest:
                    ref = rest.strip()[:16]

                pending_line_entry = {
                    "value_date": val_date,
                    "booking_date": entry_date,
                    "type": entry_type,
                    "amount": amount,
                    "ref": ref
                }
        elif tag == "86":
            commit_pending_entry(val)
        elif tag in ("62F", "62M"):
            commit_pending_entry()
            closing_bal = _parse_balance_tag(val)
            if opening_bal and closing_bal:
                statements.append(Statement(
                    statement_id=stmt_ref,
                    account_identification=account,
                    currency=opening_bal.currency,
                    opening_balance=opening_bal,
                    closing_balance=closing_bal,
                    entries=list(entries),
                    sequence_number=seq,
                    source_format="SWIFT-MT940"
                ))
            entries = []
            opening_bal = None
            closing_bal = None

    return statements
