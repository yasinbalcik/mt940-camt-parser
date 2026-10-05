import sys
from pathlib import Path
from . import parse_statement, EntryType


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m mt940_camt_parser <path_to_statement_file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    content = file_path.read_text(encoding="utf-8", errors="replace")
    statements = parse_statement(content)

    print(f"Parsed {len(statements)} statement(s) from {file_path.name}")
    print("-" * 65)

    for idx, stmt in enumerate(statements, 1):
        print(f"Statement #{idx} [{stmt.source_format}]")
        print(f"  Account ID:      {stmt.account_identification}")
        print(f"  Currency:        {stmt.currency}")
        print(f"  Opening Balance: {stmt.opening_balance.amount} {stmt.currency} ({stmt.opening_balance.entry_type.value}) on {stmt.opening_balance.date}")
        print(f"  Closing Balance: {stmt.closing_balance.amount} {stmt.currency} ({stmt.closing_balance.entry_type.value}) on {stmt.closing_balance.date}")
        print(f"  Total Credits:   {stmt.total_credits} {stmt.currency}")
        print(f"  Total Debits:    {stmt.total_debits} {stmt.currency}")
        print(f"  Transactions:    {stmt.entry_count}")
        print("  Recent Entries:")
        for e in stmt.entries[:5]:
            sign = "+" if e.entry_type == EntryType.CREDIT else "-"
            print(f"    [{e.booking_date}] {sign}{e.amount} {e.currency} | {e.description[:40]}")
        if stmt.entry_count > 5:
            print(f"    ... and {stmt.entry_count - 5} more entry(ies)")
        print("-" * 65)


if __name__ == "__main__":
    main()
