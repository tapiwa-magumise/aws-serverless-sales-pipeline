import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "validator"))

from rules import validate  # noqa: E402

BRANCHES = {"LON01", "MAN01"}
TODAY = date(2026, 10, 16)
HEADER = "date,branch_code,sku,units,revenue,cost\n"


def test_clean_row_loads():
    r = validate(HEADER + "2026-10-15,LON01,ABC-123,3,30.00,18.50\n", BRANCHES, TODAY)
    assert len(r.loaded) == 1 and not r.rejected
    assert r.loaded[0]["units"] == 3


def test_each_rule_rejects_with_a_reason():
    rows = [
        "2026-13-01,LON01,ABC-123,1,1,1",   # bad date
        "2026-10-20,LON01,ABC-123,1,1,1",   # future date
        "2026-10-15,XXX99,ABC-123,1,1,1",   # unknown branch
        "2026-10-15,LON01,abc123,1,1,1",    # bad sku
        "2026-10-15,LON01,ABC-124,0,1,1",   # zero units
        "2026-10-15,LON01,ABC-125,1,-5,1",  # negative revenue
        "2026-10-15,LON01,ABC-126,1,1,x",   # cost not a number
    ]
    r = validate(HEADER + "\n".join(rows) + "\n", BRANCHES, TODAY)
    assert not r.loaded
    assert len(r.rejected) == 7
    assert all(row["reasons"] for row in r.rejected)
    assert r.rejected[0]["line"] == 2


def test_duplicate_row_rejected():
    row = "2026-10-15,MAN01,XYZ-001,2,20,10\n"
    r = validate(HEADER + row + row, BRANCHES, TODAY)
    assert len(r.loaded) == 1
    assert "duplicate" in r.rejected[0]["reasons"][0]


def test_missing_column_fails_whole_file():
    r = validate("date,branch_code,sku,units,revenue\n2026-10-15,LON01,ABC-123,1,1\n", BRANCHES, TODAY)
    assert r.file_error == "missing columns: cost"
    assert not r.loaded and not r.rejected
