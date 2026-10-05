from datetime import date
from decimal import Decimal
import xml.etree.ElementTree as ET
from typing import List, Optional
from .models import Balance, EntryType, Statement, TransactionEntry


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_camt053(xml_content: str) -> List[Statement]:
    root = ET.fromstring(xml_content)
    statements: List[Statement] = []

    for stmt_elem in root.iter():
        if _strip_ns(stmt_elem.tag) != "Stmt":
            continue

        stmt_id = "UNKNOWN"
        account_id = "UNKNOWN"
        currency = "TRY"
        opening_bal: Optional[Balance] = None
        closing_bal: Optional[Balance] = None
        entries: List[TransactionEntry] = []

        for child in stmt_elem:
            tag_name = _strip_ns(child.tag)

            if tag_name == "Id":
                stmt_id = child.text.strip() if child.text else "UNKNOWN"

            elif tag_name == "Acct":
                # Prioritize IBAN
                found = False
                for elem in child.iter():
                    if _strip_ns(elem.tag) == "IBAN" and elem.text and elem.text.strip():
                        account_id = elem.text.strip()
                        found = True
                        break
                if not found:
                    for elem in child.iter():
                        if _strip_ns(elem.tag) == "Id" and elem.text and elem.text.strip():
                            account_id = elem.text.strip()
                            break

            elif tag_name == "Bal":
                bal_type = None
                bal_amount = Decimal("0.00")
                bal_cur = "TRY"
                bal_date = date.today()
                bal_entry_type = EntryType.CREDIT

                for b_elem in child.iter():
                    b_tag = _strip_ns(b_elem.tag)
                    if b_tag == "Cd":
                        bal_type = b_elem.text
                    elif b_tag == "Amt":
                        bal_amount = Decimal(b_elem.text or "0.00")
                        bal_cur = b_elem.attrib.get("Ccy", "TRY")
                    elif b_tag == "CdtDbtInd":
                        bal_entry_type = EntryType.CREDIT if b_elem.text == "CRDT" else EntryType.DEBIT
                    elif b_tag in ("Dt", "DtTm"):
                        if b_elem.text and b_elem.text.strip():
                            bal_date = date.fromisoformat(b_elem.text.strip()[:10])

                balance_obj = Balance(
                    entry_type=bal_entry_type,
                    amount=bal_amount,
                    currency=bal_cur,
                    date=bal_date
                )

                if bal_type in ("OPBD", "PRCD"):
                    opening_bal = balance_obj
                    currency = bal_cur
                elif bal_type in ("CLBD", "CLAV"):
                    closing_bal = balance_obj

            elif tag_name == "Ntry":
                ntry_amount = Decimal("0.00")
                ntry_cur = currency
                ntry_type = EntryType.CREDIT
                booking_date = date.today()
                value_date = date.today()
                description_parts: List[str] = []
                entry_ref = f"NTRY-{len(entries)+1}"

                for n_elem in child.iter():
                    n_tag = _strip_ns(n_elem.tag)
                    if n_tag == "Amt":
                        ntry_amount = Decimal(n_elem.text or "0.00")
                        ntry_cur = n_elem.attrib.get("Ccy", currency)
                    elif n_tag == "CdtDbtInd":
                        ntry_type = EntryType.CREDIT if n_elem.text == "CRDT" else EntryType.DEBIT
                    elif n_tag == "BookgDt":
                        for d_sub in n_elem.iter():
                            if _strip_ns(d_sub.tag) == "Dt" and d_sub.text and d_sub.text.strip():
                                booking_date = date.fromisoformat(d_sub.text.strip()[:10])
                                break
                    elif n_tag == "ValDt":
                        for d_sub in n_elem.iter():
                            if _strip_ns(d_sub.tag) == "Dt" and d_sub.text and d_sub.text.strip():
                                value_date = date.fromisoformat(d_sub.text.strip()[:10])
                                break
                    elif n_tag == "AcctSvcrRef" and n_elem.text:
                        entry_ref = n_elem.text.strip()
                    elif n_tag in ("Ustrd", "Desc") and n_elem.text and n_elem.text.strip():
                        description_parts.append(n_elem.text.strip())

                entries.append(TransactionEntry(
                    entry_id=entry_ref,
                    booking_date=booking_date,
                    value_date=value_date,
                    entry_type=ntry_type,
                    amount=ntry_amount,
                    currency=ntry_cur,
                    description=" | ".join(description_parts) or "Transaction",
                    account_servicer_ref=entry_ref
                ))

        if opening_bal and closing_bal:
            statements.append(Statement(
                statement_id=stmt_id,
                account_identification=account_id,
                currency=currency,
                opening_balance=opening_bal,
                closing_balance=closing_bal,
                entries=entries,
                source_format="ISO20022-CAMT053"
            ))

    return statements
