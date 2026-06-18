"""
Production Data Quality Checker
================================
14 automated validation checks across:
  - Null detection
  - Duplicate identification
  - Range validation
  - Referential integrity
  - Schema validation
  - Statistical outliers
  - Format/pattern validation

Multi-level logging: CRITICAL → critical_alerts.log | WARNING → warnings.log | INFO → audit.log
"""

import sqlite3
import json
import csv
import logging
import logging.handlers
import os
import re
import hashlib
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_DIR = BASE_DIR / "config"

for d in (LOG_DIR, DATA_DIR, REPORTS_DIR, CONFIG_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ─── Enums & constants ────────────────────────────────────────────────────────
class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING  = "WARNING"
    INFO     = "INFO"
    PASS     = "PASS"


class CheckCategory(str, Enum):
    NULL_DETECTION      = "Null Detection"
    DUPLICATE_ID        = "Duplicate Identification"
    RANGE_VALIDATION    = "Range Validation"
    REFERENTIAL         = "Referential Integrity"
    SCHEMA              = "Schema Validation"
    STATISTICAL         = "Statistical Outlier"
    FORMAT_PATTERN      = "Format / Pattern"
    DATA_FRESHNESS      = "Data Freshness"


# ─── Result dataclass ─────────────────────────────────────────────────────────
@dataclass
class CheckResult:
    check_id:    str
    check_name:  str
    category:    CheckCategory
    severity:    Severity
    table:       str
    column:      Optional[str]
    passed:      bool
    affected_rows: int
    total_rows:  int
    message:     str
    details:     dict = field(default_factory=dict)
    timestamp:   str  = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def failure_rate(self) -> float:
        return (self.affected_rows / self.total_rows * 100) if self.total_rows else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["failure_rate"] = round(self.failure_rate, 2)
        d["category"]     = self.category.value
        d["severity"]     = self.severity.value
        return d


# ─── Multi-level logging setup ────────────────────────────────────────────────
def _setup_logging() -> logging.Logger:
    """
    Production-style multi-channel logging:
      - CRITICAL  → logs/critical_alerts.log  (modelled after P0/P1 incident runbooks)
      - WARNING   → logs/warnings.log          (operational alerts)
      - INFO+     → logs/audit.log             (full audit trail)
      - console   → stdout                     (live operator view)
    """
    fmt_full  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    fmt_short = "%(asctime)s | %(levelname)-8s | %(message)s"

    logger = logging.getLogger("dq_checker")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # 1. CRITICAL-only handler — mirrors P0 alert channel
    crit_handler = logging.FileHandler(LOG_DIR / "critical_alerts.log", encoding="utf-8")
    crit_handler.setLevel(logging.CRITICAL)
    crit_handler.setFormatter(logging.Formatter(fmt_full))

    # 2. WARNING-only handler — operational runbook feed
    class WarningFilter(logging.Filter):
        def filter(self, record):
            return record.levelno == logging.WARNING

    warn_handler = logging.FileHandler(LOG_DIR / "warnings.log", encoding="utf-8")
    warn_handler.setLevel(logging.WARNING)
    warn_handler.addFilter(WarningFilter())
    warn_handler.setFormatter(logging.Formatter(fmt_full))

    # 3. Full rotating audit log
    audit_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "audit.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    audit_handler.setLevel(logging.DEBUG)
    audit_handler.setFormatter(logging.Formatter(fmt_full))

    # 4. Console (operator live view)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(fmt_short))

    for h in (crit_handler, warn_handler, audit_handler, console_handler):
        logger.addHandler(h)

    return logger


log = _setup_logging()


# ─── Database bootstrap ───────────────────────────────────────────────────────
def bootstrap_demo_db(db_path: Path) -> sqlite3.Connection:
    """Creates a realistic demo SQLite database for validation."""
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS departments (
        dept_id   INTEGER PRIMARY KEY,
        dept_name TEXT NOT NULL UNIQUE,
        budget    REAL
    );

    CREATE TABLE IF NOT EXISTS employees (
        emp_id      INTEGER PRIMARY KEY,
        first_name  TEXT,
        last_name   TEXT,
        email       TEXT,
        dept_id     INTEGER REFERENCES departments(dept_id),
        salary      REAL,
        hire_date   TEXT,
        is_active   INTEGER
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id     INTEGER PRIMARY KEY,
        emp_id       INTEGER REFERENCES employees(emp_id),
        amount       REAL,
        order_date   TEXT,
        status       TEXT,
        region       TEXT
    );

    CREATE TABLE IF NOT EXISTS products (
        product_id   INTEGER PRIMARY KEY,
        name         TEXT UNIQUE,
        price        REAL,
        stock_qty    INTEGER
    );

    CREATE TABLE IF NOT EXISTS order_items (
        item_id     INTEGER PRIMARY KEY,
        order_id    INTEGER REFERENCES orders(order_id),
        product_id  INTEGER REFERENCES products(product_id),
        quantity    INTEGER,
        unit_price  REAL
    );
    """)

    # Departments
    cur.executemany(
        "INSERT OR IGNORE INTO departments VALUES (?,?,?)",
        [(1,"Engineering",850000),(2,"Sales",400000),(3,"Finance",300000),(4,"HR",200000)]
    )

    import random, string
    random.seed(42)

    # Employees — inject deliberate quality issues
    employees = []
    emails_used = set()
    for i in range(1, 151):
        fn = random.choice(["Alice","Bob","Carol","Dave","Eve","Frank","Grace","Hank","Iris","Jake"])
        ln = random.choice(["Smith","Jones","Lee","Brown","Taylor","Wilson","Davis","Clark","Hall","Young"])
        # Inject nulls (~5%)
        email = None if random.random() < 0.05 else f"{fn.lower()}.{ln.lower()}{i}@company.com"
        # Inject duplicates (~3%)
        if random.random() < 0.03 and emails_used:
            email = random.choice(list(emails_used))
        if email:
            emails_used.add(email)
        dept = random.choice([1,2,3,4, None])   # ~20% orphan
        salary = random.choice([-500, 25000, 55000, 80000, 120000, 210000, 999999])
        hire_date = f"20{random.randint(10,23):02d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        # Inject bad dates
        if random.random() < 0.04:
            hire_date = "not-a-date"
        is_active = random.choice([0,1,1,1])
        employees.append((i, fn, ln, email, dept, salary, hire_date, is_active))

    cur.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?,?)", employees)

    # Products
    for i in range(1, 21):
        cur.execute("INSERT OR IGNORE INTO products VALUES (?,?,?,?)",
                    (i, f"Product_{i}", round(random.uniform(5,500),2), random.randint(0,500)))

    # Orders
    statuses = ["completed","pending","cancelled","refunded"]
    regions  = ["North","South","East","West",None]
    for i in range(1, 501):
        emp = random.randint(1,150)
        amt = round(random.uniform(-50, 5000), 2)   # negatives = bad data
        odate = (datetime.today() - timedelta(days=random.randint(0,730))).strftime("%Y-%m-%d")
        if random.random() < 0.03:
            odate = "2099-12-31"    # future date
        status = random.choice(statuses)
        region = random.choice(regions)
        cur.execute("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?)",
                    (i, emp, amt, odate, status, region))

    # Order items
    for i in range(1, 1001):
        oid = random.randint(1,500)
        pid = random.randint(1,20)
        qty = random.choice([-1, 0, 1, 2, 5, 10, 100])
        up  = round(random.uniform(5,600),2)
        cur.execute("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?)", (i,oid,pid,qty,up))

    conn.commit()
    return conn


# ─── The 14 Validation Checks ─────────────────────────────────────────────────
class DataQualityChecker:

    def __init__(self, conn: sqlite3.Connection):
        self.conn    = conn
        self.cur     = conn.cursor()
        self.results: list[CheckResult] = []

    # ── helpers ───────────────────────────────────────────────────────────────
    def _total(self, table: str) -> int:
        return self.cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def _record(self, result: CheckResult):
        self.results.append(result)
        lvl = result.severity
        msg = f"[{result.check_id}] {result.check_name} | {result.table}"
        if result.column:
            msg += f".{result.column}"
        msg += f" | {result.message}"
        if lvl == Severity.CRITICAL:
            log.critical(msg)
        elif lvl == Severity.WARNING:
            log.warning(msg)
        elif lvl == Severity.PASS:
            log.info(f"PASS  {msg}")
        else:
            log.info(msg)

    # ── CHECK 01 — Critical null detection (PK / FK / email) ─────────────────
    def check_01_critical_nulls(self):
        configs = [
            ("employees", "first_name",  Severity.WARNING),
            ("employees", "email",       Severity.WARNING),
            ("employees", "dept_id",     Severity.WARNING),
            ("orders",    "emp_id",      Severity.CRITICAL),
            ("orders",    "amount",      Severity.CRITICAL),
        ]
        for table, col, sev in configs:
            total   = self._total(table)
            nulls   = self.cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL").fetchone()[0]
            passed  = nulls == 0
            self._record(CheckResult(
                check_id="CHK-01", check_name="Critical Null Detection",
                category=CheckCategory.NULL_DETECTION, severity=Severity.PASS if passed else sev,
                table=table, column=col, passed=passed,
                affected_rows=nulls, total_rows=total,
                message=f"{nulls} NULL values found" if not passed else "No NULLs"
            ))

    # ── CHECK 02 — Null rate threshold (>10% = warning) ───────────────────────
    def check_02_null_rate_threshold(self):
        cols = [("orders","region"), ("employees","last_name")]
        for table, col in cols:
            total  = self._total(table)
            nulls  = self.cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL").fetchone()[0]
            rate   = nulls / total * 100 if total else 0
            passed = rate <= 10
            self._record(CheckResult(
                check_id="CHK-02", check_name="Null Rate Threshold (>10%)",
                category=CheckCategory.NULL_DETECTION,
                severity=Severity.PASS if passed else Severity.WARNING,
                table=table, column=col, passed=passed,
                affected_rows=nulls, total_rows=total,
                message=f"{rate:.1f}% null rate" + (" — exceeds 10% threshold" if not passed else ""),
                details={"null_rate_pct": round(rate,2)}
            ))

    # ── CHECK 03 — Exact row duplicates ───────────────────────────────────────
    def check_03_exact_duplicates(self):
        for table in ("employees", "orders"):
            total = self._total(table)
            cols  = [r[1] for r in self.cur.execute(f"PRAGMA table_info({table})").fetchall()
                     if r[1] not in ("emp_id","order_id","rowid")]
            if not cols:
                continue
            group_expr = ", ".join(cols)
            dups = self.cur.execute(
                f"SELECT COUNT(*) FROM (SELECT {group_expr}, COUNT(*) c FROM {table} GROUP BY {group_expr} HAVING c>1)"
            ).fetchone()[0]
            passed = dups == 0
            self._record(CheckResult(
                check_id="CHK-03", check_name="Exact Row Duplicates",
                category=CheckCategory.DUPLICATE_ID,
                severity=Severity.PASS if passed else Severity.WARNING,
                table=table, column=None, passed=passed,
                affected_rows=dups, total_rows=total,
                message=f"{dups} duplicate row groups" if not passed else "No exact duplicates"
            ))

    # ── CHECK 04 — Unique key duplicates (email) ───────────────────────────────
    def check_04_unique_key_duplicates(self):
        total = self._total("employees")
        dups  = self.cur.execute(
            "SELECT COUNT(*) FROM (SELECT email, COUNT(*) c FROM employees WHERE email IS NOT NULL GROUP BY email HAVING c>1)"
        ).fetchone()[0]
        passed = dups == 0
        self._record(CheckResult(
            check_id="CHK-04", check_name="Unique Key Violation (email)",
            category=CheckCategory.DUPLICATE_ID,
            severity=Severity.PASS if passed else Severity.CRITICAL,
            table="employees", column="email", passed=passed,
            affected_rows=dups, total_rows=total,
            message=f"{dups} duplicate emails — violates UNIQUE constraint" if not passed else "All emails unique"
        ))

    # ── CHECK 05 — Negative salary range ─────────────────────────────────────
    def check_05_negative_salary(self):
        total = self._total("employees")
        bad   = self.cur.execute("SELECT COUNT(*) FROM employees WHERE salary < 0").fetchone()[0]
        passed = bad == 0
        self._record(CheckResult(
            check_id="CHK-05", check_name="Negative Salary",
            category=CheckCategory.RANGE_VALIDATION,
            severity=Severity.PASS if passed else Severity.CRITICAL,
            table="employees", column="salary", passed=passed,
            affected_rows=bad, total_rows=total,
            message=f"{bad} negative salary values" if not passed else "All salaries non-negative"
        ))

    # ── CHECK 06 — Salary upper-bound outlier (>500k) ─────────────────────────
    def check_06_salary_upper_bound(self):
        total = self._total("employees")
        bad   = self.cur.execute("SELECT COUNT(*) FROM employees WHERE salary > 500000").fetchone()[0]
        passed = bad == 0
        self._record(CheckResult(
            check_id="CHK-06", check_name="Salary Upper Bound (>500k)",
            category=CheckCategory.RANGE_VALIDATION,
            severity=Severity.PASS if passed else Severity.WARNING,
            table="employees", column="salary", passed=passed,
            affected_rows=bad, total_rows=total,
            message=f"{bad} salaries exceed $500k threshold" if not passed else "Salaries within bounds"
        ))

    # ── CHECK 07 — Negative order amounts ────────────────────────────────────
    def check_07_negative_order_amount(self):
        total = self._total("orders")
        bad   = self.cur.execute("SELECT COUNT(*) FROM orders WHERE amount < 0").fetchone()[0]
        passed = bad == 0
        self._record(CheckResult(
            check_id="CHK-07", check_name="Negative Order Amount",
            category=CheckCategory.RANGE_VALIDATION,
            severity=Severity.PASS if passed else Severity.CRITICAL,
            table="orders", column="amount", passed=passed,
            affected_rows=bad, total_rows=total,
            message=f"{bad} negative order amounts" if not passed else "All amounts non-negative"
        ))

    # ── CHECK 08 — Future order dates ─────────────────────────────────────────
    def check_08_future_dates(self):
        today = datetime.today().strftime("%Y-%m-%d")
        total = self._total("orders")
        bad   = self.cur.execute(
            f"SELECT COUNT(*) FROM orders WHERE order_date > '{today}' AND order_date NOT LIKE '%not%'"
        ).fetchone()[0]
        passed = bad == 0
        self._record(CheckResult(
            check_id="CHK-08", check_name="Future Order Dates",
            category=CheckCategory.RANGE_VALIDATION,
            severity=Severity.PASS if passed else Severity.WARNING,
            table="orders", column="order_date", passed=passed,
            affected_rows=bad, total_rows=total,
            message=f"{bad} orders with future dates" if not passed else "All dates valid"
        ))

    # ── CHECK 09 — Referential integrity: orders → employees ─────────────────
    def check_09_ref_integrity_orders_employees(self):
        total = self._total("orders")
        bad   = self.cur.execute(
            "SELECT COUNT(*) FROM orders o LEFT JOIN employees e ON o.emp_id=e.emp_id WHERE e.emp_id IS NULL"
        ).fetchone()[0]
        passed = bad == 0
        self._record(CheckResult(
            check_id="CHK-09", check_name="Referential Integrity: orders→employees",
            category=CheckCategory.REFERENTIAL,
            severity=Severity.PASS if passed else Severity.CRITICAL,
            table="orders", column="emp_id", passed=passed,
            affected_rows=bad, total_rows=total,
            message=f"{bad} orders reference non-existent employees" if not passed else "All FK references valid"
        ))

    # ── CHECK 10 — Referential integrity: employees → departments ─────────────
    def check_10_ref_integrity_employees_depts(self):
        total = self._total("employees")
        bad   = self.cur.execute(
            "SELECT COUNT(*) FROM employees e LEFT JOIN departments d ON e.dept_id=d.dept_id WHERE d.dept_id IS NULL AND e.dept_id IS NOT NULL"
        ).fetchone()[0]
        passed = bad == 0
        self._record(CheckResult(
            check_id="CHK-10", check_name="Referential Integrity: employees→departments",
            category=CheckCategory.REFERENTIAL,
            severity=Severity.PASS if passed else Severity.CRITICAL,
            table="employees", column="dept_id", passed=passed,
            affected_rows=bad, total_rows=total,
            message=f"{bad} employees reference non-existent departments" if not passed else "All FK references valid"
        ))

    # ── CHECK 11 — Email format validation (regex) ────────────────────────────
    def check_11_email_format(self):
        pattern = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
        rows    = self.cur.execute("SELECT emp_id, email FROM employees WHERE email IS NOT NULL").fetchall()
        total   = self._total("employees")
        bad_ids = [r[0] for r in rows if not pattern.match(r[1])]
        passed  = len(bad_ids) == 0
        self._record(CheckResult(
            check_id="CHK-11", check_name="Email Format Validation",
            category=CheckCategory.FORMAT_PATTERN,
            severity=Severity.PASS if passed else Severity.WARNING,
            table="employees", column="email", passed=passed,
            affected_rows=len(bad_ids), total_rows=total,
            message=f"{len(bad_ids)} malformed email addresses" if not passed else "All emails well-formed",
            details={"sample_bad_ids": bad_ids[:10]}
        ))

    # ── CHECK 12 — Date format validation (hire_date) ─────────────────────────
    def check_12_date_format(self):
        rows  = self.cur.execute("SELECT emp_id, hire_date FROM employees WHERE hire_date IS NOT NULL").fetchall()
        total = self._total("employees")
        pat   = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        bad   = [r[0] for r in rows if not pat.match(str(r[1]))]
        passed = len(bad) == 0
        self._record(CheckResult(
            check_id="CHK-12", check_name="Date Format Validation (YYYY-MM-DD)",
            category=CheckCategory.FORMAT_PATTERN,
            severity=Severity.PASS if passed else Severity.WARNING,
            table="employees", column="hire_date", passed=passed,
            affected_rows=len(bad), total_rows=total,
            message=f"{len(bad)} malformed hire_date values" if not passed else "All dates correctly formatted",
            details={"sample_bad_ids": bad[:10]}
        ))

    # ── CHECK 13 — Statistical outlier (IQR method on order amounts) ──────────
    def check_13_statistical_outlier(self):
        amounts = [r[0] for r in self.cur.execute("SELECT amount FROM orders WHERE amount IS NOT NULL AND amount >= 0").fetchall()]
        total   = self._total("orders")
        if len(amounts) < 4:
            return
        amounts.sort()
        n  = len(amounts)
        q1 = amounts[n//4]
        q3 = amounts[3*n//4]
        iqr = q3 - q1
        lo, hi = q1 - 3*iqr, q3 + 3*iqr
        outliers = [a for a in amounts if a < lo or a > hi]
        passed = len(outliers) == 0
        self._record(CheckResult(
            check_id="CHK-13", check_name="Statistical Outlier Detection (IQR×3)",
            category=CheckCategory.STATISTICAL,
            severity=Severity.PASS if passed else Severity.WARNING,
            table="orders", column="amount", passed=passed,
            affected_rows=len(outliers), total_rows=total,
            message=f"{len(outliers)} statistical outliers (IQR×3 fence)" if not passed else "No statistical outliers",
            details={"q1": round(q1,2), "q3": round(q3,2), "iqr": round(iqr,2),
                     "fence_low": round(lo,2), "fence_high": round(hi,2)}
        ))

    # ── CHECK 14 — Order item quantity range (≥1) ─────────────────────────────
    def check_14_order_item_qty(self):
        total = self._total("order_items")
        bad   = self.cur.execute("SELECT COUNT(*) FROM order_items WHERE quantity < 1").fetchone()[0]
        passed = bad == 0
        self._record(CheckResult(
            check_id="CHK-14", check_name="Order Item Quantity ≥ 1",
            category=CheckCategory.RANGE_VALIDATION,
            severity=Severity.PASS if passed else Severity.CRITICAL,
            table="order_items", column="quantity", passed=passed,
            affected_rows=bad, total_rows=total,
            message=f"{bad} items with zero/negative quantity" if not passed else "All quantities valid"
        ))

    # ── Runner ────────────────────────────────────────────────────────────────
    def run_all(self) -> list[CheckResult]:
        log.info("=" * 70)
        log.info("DATA QUALITY CHECK RUN STARTED")
        log.info("=" * 70)
        checks = [
            self.check_01_critical_nulls,
            self.check_02_null_rate_threshold,
            self.check_03_exact_duplicates,
            self.check_04_unique_key_duplicates,
            self.check_05_negative_salary,
            self.check_06_salary_upper_bound,
            self.check_07_negative_order_amount,
            self.check_08_future_dates,
            self.check_09_ref_integrity_orders_employees,
            self.check_10_ref_integrity_employees_depts,
            self.check_11_email_format,
            self.check_12_date_format,
            self.check_13_statistical_outlier,
            self.check_14_order_item_qty,
        ]
        for fn in checks:
            try:
                fn()
            except Exception as exc:
                log.critical(f"Check {fn.__name__} raised unhandled exception: {exc}", exc_info=True)

        self._summarise()
        return self.results

    def _summarise(self):
        total     = len(self.results)
        passed    = sum(1 for r in self.results if r.passed)
        criticals = sum(1 for r in self.results if r.severity == Severity.CRITICAL and not r.passed)
        warnings  = sum(1 for r in self.results if r.severity == Severity.WARNING  and not r.passed)
        log.info("=" * 70)
        log.info(f"SUMMARY  total={total}  passed={passed}  critical={criticals}  warning={warnings}")
        log.info("=" * 70)
        if criticals:
            log.critical(f"RUN COMPLETE — {criticals} CRITICAL failure(s) require immediate action")
        elif warnings:
            log.warning(f"RUN COMPLETE — {warnings} warning(s) require review")
        else:
            log.info("RUN COMPLETE — all checks passed")


# ─── Report writer ────────────────────────────────────────────────────────────
class ReportWriter:

    def __init__(self, results: list[CheckResult]):
        self.results   = results
        self.timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def to_json(self) -> Path:
        out = REPORTS_DIR / f"dq_report_{self.timestamp}.json"
        payload = {
            "generated_at":  datetime.utcnow().isoformat(),
            "total_checks":  len(self.results),
            "passed":        sum(1 for r in self.results if r.passed),
            "failed":        sum(1 for r in self.results if not r.passed),
            "criticals":     sum(1 for r in self.results if r.severity == Severity.CRITICAL and not r.passed),
            "warnings":      sum(1 for r in self.results if r.severity == Severity.WARNING  and not r.passed),
            "checks":        [r.to_dict() for r in self.results],
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log.info(f"JSON report written → {out}")
        return out

    def to_csv(self) -> Path:
        out = REPORTS_DIR / f"dq_report_{self.timestamp}.csv"
        fieldnames = ["check_id","check_name","category","severity","table","column",
                      "passed","affected_rows","total_rows","failure_rate","message","timestamp"]
        with out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                d = r.to_dict()
                writer.writerow({k: d.get(k,"") for k in fieldnames})
        log.info(f"CSV report written → {out}")
        return out

    def to_sqlite_history(self, conn: sqlite3.Connection):
        """Persist results into a dq_runs table for trend analysis."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dq_runs (
                run_id TEXT, check_id TEXT, check_name TEXT, category TEXT,
                severity TEXT, table_name TEXT, column_name TEXT,
                passed INTEGER, affected_rows INTEGER, total_rows INTEGER,
                failure_rate REAL, message TEXT, timestamp TEXT
            )
        """)
        run_id = hashlib.md5(self.timestamp.encode()).hexdigest()[:8]
        rows = [
            (run_id, r.check_id, r.check_name, r.category.value, r.severity.value,
             r.table, r.column, int(r.passed), r.affected_rows, r.total_rows,
             round(r.failure_rate,2), r.message, r.timestamp)
            for r in self.results
        ]
        conn.executemany(
            "INSERT INTO dq_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
        )
        conn.commit()
        log.info(f"Run {run_id} persisted to dq_runs history table")


# ─── Entry point ─────────────────────────────────────────────────────────────
def main():
    db_path = DATA_DIR / "demo.db"
    log.info(f"Bootstrapping demo database at {db_path}")
    conn    = bootstrap_demo_db(db_path)

    checker = DataQualityChecker(conn)
    results = checker.run_all()

    writer  = ReportWriter(results)
    json_path = writer.to_json()
    csv_path  = writer.to_csv()
    writer.to_sqlite_history(conn)

    conn.close()
    return json_path


if __name__ == "__main__":
    main()
