import unittest
from datetime import date
from decimal import Decimal
from mt940_camt_parser import parse_mt940, parse_camt053, parse_statement, EntryType


SAMPLE_MT940 = """
:20:STMT20261005
:25:TR330006100519786457841326
:28C:00123/001
:60F:C261001TRY50000,00
:61:2610021002CR12500,00NTRFNONREF//REF987654
:86:FATURA TAHSILATI
ABC YAZILIM A.S.
GIB2026000000042
:61:2610031003DR4500,50NTRFNONREF//REF112233
:86:OFIS KIRASI EKIM
:62F:C261005TRY57999,50
""".strip()


SAMPLE_CAMT053 = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
  <BkToCstmrStmt>
    <Stmt>
      <Id>CAMT-STMT-2026-001</Id>
      <Acct>
        <Id>
          <IBAN>TR560006200000012990000001</IBAN>
        </Id>
      </Acct>
      <Bal>
        <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="TRY">10000.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-10-01</Dt></Dt>
      </Bal>
      <Ntry>
        <Amt Ccy="TRY">3500.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <BookgDt><Dt>2026-10-02</Dt></BookgDt>
        <ValDt><Dt>2026-10-02</Dt></ValDt>
        <AcctSvcrRef>EFT-998877</AcctSvcrRef>
        <NtryDtls>
          <TxDtls>
            <RmtInf>
              <Ustrd>EFT GELEN HAVALE / MUSTERI ODEMESI</Ustrd>
            </RmtInf>
          </TxDtls>
        </NtryDtls>
      </Ntry>
      <Ntry>
        <Amt Ccy="TRY">1200.75</Amt>
        <CdtDbtInd>DBIT</CdtDbtInd>
        <BookgDt><Dt>2026-10-03</Dt></BookgDt>
        <ValDt><Dt>2026-10-03</Dt></ValDt>
        <AcctSvcrRef>VIR-443322</AcctSvcrRef>
        <NtryDtls>
          <TxDtls>
            <RmtInf>
              <Ustrd>BULUT SUNUCU HIZMET BEDELI</Ustrd>
            </RmtInf>
          </TxDtls>
        </NtryDtls>
      </Ntry>
      <Bal>
        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="TRY">12299.25</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-10-05</Dt></Dt>
      </Bal>
    </Stmt>
  </BkToCstmrStmt>
</Document>
""".strip()


class TestMT940Parser(unittest.TestCase):
    def test_parse_sample_mt940(self):
        stmts = parse_mt940(SAMPLE_MT940)
        self.assertEqual(len(stmts), 1)
        s = stmts[0]

        self.assertEqual(s.statement_id, "STMT20261005")
        self.assertEqual(s.account_identification, "TR330006100519786457841326")
        self.assertEqual(s.currency, "TRY")
        self.assertEqual(s.opening_balance.amount, Decimal("50000.00"))
        self.assertEqual(s.opening_balance.entry_type, EntryType.CREDIT)
        self.assertEqual(s.opening_balance.date, date(2026, 10, 1))

        self.assertEqual(len(s.entries), 2)
        # Entry 1 (Credit)
        e1 = s.entries[0]
        self.assertEqual(e1.entry_type, EntryType.CREDIT)
        self.assertEqual(e1.amount, Decimal("12500.00"))
        self.assertEqual(e1.account_servicer_ref, "REF987654")
        self.assertIn("GIB2026000000042", e1.description)

        # Entry 2 (Debit)
        e2 = s.entries[1]
        self.assertEqual(e2.entry_type, EntryType.DEBIT)
        self.assertEqual(e2.amount, Decimal("4500.50"))
        self.assertIn("OFIS KIRASI", e2.description)

        # Totals and Closing
        self.assertEqual(s.total_credits, Decimal("12500.00"))
        self.assertEqual(s.total_debits, Decimal("4500.50"))
        self.assertEqual(s.closing_balance.amount, Decimal("57999.50"))
        # Opening (50000) + Credits (12500) - Debits (4500.50) == Closing (57999.50)
        calculated_closing = s.opening_balance.amount + s.total_credits - s.total_debits
        self.assertEqual(calculated_closing, s.closing_balance.amount)


class TestCAMT053Parser(unittest.TestCase):
    def test_parse_sample_camt053(self):
        stmts = parse_camt053(SAMPLE_CAMT053)
        self.assertEqual(len(stmts), 1)
        s = stmts[0]

        self.assertEqual(s.statement_id, "CAMT-STMT-2026-001")
        self.assertEqual(s.account_identification, "TR560006200000012990000001")
        self.assertEqual(s.currency, "TRY")
        self.assertEqual(s.opening_balance.amount, Decimal("10000.00"))

        self.assertEqual(len(s.entries), 2)
        self.assertEqual(s.entries[0].amount, Decimal("3500.00"))
        self.assertEqual(s.entries[0].entry_type, EntryType.CREDIT)
        self.assertEqual(s.entries[1].amount, Decimal("1200.75"))
        self.assertEqual(s.entries[1].entry_type, EntryType.DEBIT)

        self.assertEqual(s.total_credits, Decimal("3500.00"))
        self.assertEqual(s.total_debits, Decimal("1200.75"))
        self.assertEqual(s.closing_balance.amount, Decimal("12299.25"))


class TestAutoDetection(unittest.TestCase):
    def test_auto_detect_mt940_and_camt(self):
        stmt_mt940 = parse_statement(SAMPLE_MT940)
        self.assertEqual(stmt_mt940[0].source_format, "SWIFT-MT940")

        stmt_camt = parse_statement(SAMPLE_CAMT053)
        self.assertEqual(stmt_camt[0].source_format, "ISO20022-CAMT053")


if __name__ == "__main__":
    unittest.main()
