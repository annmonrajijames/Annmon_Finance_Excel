"""
Finance_Analysis.py
Clean a Federal Bank CSV – robust to variable header position & names
---------------------------------------------------------------------
• Keeps only: Sl. No., Tran Date, Particulars, amount
• Extracts word between 3rd & 4th slash in Particulars
• Combines Withdrawal / Deposit into signed 'amount'
"""

import csv
import re
import sys
from pathlib import Path

import pandas as pd

# ------------------------------------------------------------------
# 1  Paths – change only if your folders move
# ------------------------------------------------------------------
IN_PATH  = Path(r"C:\Git_projects\Annmon_Finance_Excel\Federal_Bank_Transaction_log.csv")
OUT_PATH = Path(r"C:\Git_projects\Annmon_Finance_Excel\Cleaned_Federal_Bank_Transaction_log.csv")

# ------------------------------------------------------------------
# 2  Read CSV and locate the header row
# ------------------------------------------------------------------
with IN_PATH.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.reader(f))

header_row_idx = None
for idx, row in enumerate(rows):
    lowered = [c.strip().lower() for c in row]
    joined  = " ".join(lowered)
    if ("date" in joined) and any(k in joined for k in ("particular", "narration", "description")):
        header_row_idx = idx
        break

if header_row_idx is None:
    sys.exit("❌ Couldn’t find a header row with both 'date' and 'particulars' keywords.")

header = [c.encode("utf-8").decode("utf-8-sig").strip().lower() for c in rows[header_row_idx]]
data   = rows[header_row_idx + 1 :]

df = pd.DataFrame(data, columns=header).dropna(how="all")

# ------------------------------------------------------------------
# 3  Helper to find a column by keyword list
# ------------------------------------------------------------------
def find(keywords, mandatory=True):
    pat = re.compile("|".join(keywords))
    matches = [c for c in df.columns if pat.search(c)]
    if matches:
        return matches[0]
    if mandatory:
        print(f"❌ Couldn’t find a column containing any of {keywords}")
        print("Detected headers:", header, sep="\n  • ")
        sys.exit(1)
    return None

# ------------------------------------------------------------------
# 4  Identify columns
# ------------------------------------------------------------------
slno_col     = find([r"\bsl\b", r"\bs[._ ]?no\b", r"\bserial\b", r"\bsr\b", r"\bindex\b", r"^unnamed"], mandatory=False)
date_col     = find([r"date"])
particol     = find([r"particular", r"narration", r"description"])
withdraw_col = find([r"withdraw", r"debit"])
deposit_col  = find([r"deposit", r"credit"])

fabricate_slno = slno_col is None

print("Matched columns:")
print(f"  Sl. No.     → {repr(slno_col) if slno_col else 'fabricate'}")
print(f"  Tran Date   → {repr(date_col)}")
print(f"  Particulars → {repr(particol)}")
print(f"  Withdrawal  → {repr(withdraw_col)}")
print(f"  Deposit     → {repr(deposit_col)}\n")

# ------------------------------------------------------------------
# 5  Clean 'Particulars'
# ------------------------------------------------------------------
def between_third_and_fourth_slash(x):
    parts = str(x).split("/")
    return parts[3] if len(parts) > 3 else x

df[particol] = df[particol].apply(between_third_and_fourth_slash)

# ------------------------------------------------------------------
# 6  Helper to turn messy money strings into floats
# ------------------------------------------------------------------
def clean_number(series: pd.Series) -> pd.Series:
    """
    • Removes anything that is not 0-9, dot or minus
    • Converts to float
    • NaNs → 0
    """
    cleaned = (
        series.astype(str)
              .str.replace(r"[^\d\.-]", "", regex=True)   # drop ₹, commas, spaces
              .replace("", "0")                           # empty → 0
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)

# ------------------------------------------------------------------
# 7  Build signed 'amount'
# ------------------------------------------------------------------
df[withdraw_col] = clean_number(df[withdraw_col])
df[deposit_col]  = clean_number(df[deposit_col])
df["amount"]     = df[deposit_col] - df[withdraw_col]

# ------------------------------------------------------------------
# 8  Assemble cleaned DataFrame
# ------------------------------------------------------------------
if fabricate_slno:
    cleaned = df[[date_col, particol, "amount"]].copy()
    cleaned.insert(0, "Sl. No.", range(1, len(cleaned) + 1))
else:
    cleaned = df[[slno_col, date_col, particol, "amount"]].copy()
    cleaned.rename(columns={slno_col: "Sl. No."}, inplace=True)

cleaned.rename(columns={date_col: "Tran Date", particol: "Particulars"}, inplace=True)
cleaned["Sl. No."] = pd.to_numeric(cleaned["Sl. No."], errors="coerce").fillna(method="ffill")
cleaned.sort_values("Sl. No.", inplace=True, ignore_index=True)

# ------------------------------------------------------------------
# 9  Save
# ------------------------------------------------------------------
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
cleaned.to_csv(OUT_PATH, index=False)
print(f"✅ Cleaned file written to:\n   {OUT_PATH}")
