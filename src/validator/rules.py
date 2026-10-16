"""Row validation rules for branch sales files.

Pure functions with no AWS calls, so they can be unit tested on a laptop.
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = ["date", "branch_code", "sku", "units", "revenue", "cost"]
SKU_PATTERN = re.compile(r"^[A-Z]{3}-\d{3}$")


@dataclass
class Result:
    loaded: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    file_error: str | None = None


def _check_row(row: dict, branches: set[str], today: date) -> list[str]:
    """Return every reason a row is invalid. An empty list means it loads."""
    reasons = []

    try:
        d = date.fromisoformat(row["date"].strip())
        if d > today:
            reasons.append("date is in the future")
    except ValueError:
        reasons.append("date is not YYYY-MM-DD")

    if row["branch_code"].strip() not in branches:
        reasons.append("unknown branch_code")

    if not SKU_PATTERN.match(row["sku"].strip()):
        reasons.append("sku must look like ABC-123")

    try:
        if int(row["units"]) <= 0:
            reasons.append("units must be above zero")
    except ValueError:
        reasons.append("units is not a whole number")

    for col in ("revenue", "cost"):
        try:
            if Decimal(row[col]) < 0:
                reasons.append(f"{col} is negative")
        except InvalidOperation:
            reasons.append(f"{col} is not a number")

    return reasons


def validate(body: str, branches: set[str], today: date) -> Result:
    """Split a CSV file into rows that load and rows that are rejected with reasons."""
    result = Result()
    reader = csv.DictReader(io.StringIO(body))

    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        result.file_error = f"missing columns: {', '.join(missing)}"
        return result

    seen = set()
    for line_no, row in enumerate(reader, start=2):  # line 1 is the header
        reasons = _check_row(row, branches, today)

        key = (row["date"], row["branch_code"], row["sku"])
        if key in seen:
            reasons.append("duplicate of an earlier row (same date, branch, sku)")
        seen.add(key)

        if reasons:
            result.rejected.append({"line": line_no, **row, "reasons": reasons})
        else:
            result.loaded.append({
                "date": row["date"].strip(),
                "branch_code": row["branch_code"].strip(),
                "sku": row["sku"].strip(),
                "units": int(row["units"]),
                "revenue": str(Decimal(row["revenue"])),
                "cost": str(Decimal(row["cost"])),
            })

    return result
