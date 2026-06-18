# 🚀 Production Data Quality Monitoring System

A production-inspired Data Quality Monitoring System built using Python and SQLite that automatically validates database records, detects anomalies, generates reports, maintains audit logs, and provides dashboard-based monitoring.

URL:https://pdqualitychecker.streamlit.app/
---

## 📌 Project Overview

Organizations rely heavily on data for decision-making. Poor-quality data can lead to incorrect reports, operational failures, financial losses, and poor business decisions.

This project automates the process of validating data quality by performing multiple validation checks and generating actionable reports.

The system scans database tables, identifies data quality issues, categorizes them by severity, and generates logs and reports for monitoring and analysis.

---

## 🎯 Key Features

### Data Validation

* Null Value Detection
* Duplicate Record Detection
* Unique Key Validation
* Range Validation
* Referential Integrity Checks
* Format Validation
* Statistical Outlier Detection

### Reporting

* JSON Report Generation
* CSV Report Generation
* Historical Run Tracking

### Monitoring

* Critical Alert Logging
* Warning Alert Logging
* Complete Audit Logging
* Dashboard Visualization

### Database Support

* SQLite (Current)
* MySQL (Extendable)
* PostgreSQL (Extendable)

---

## 🏗️ System Architecture

```text
Database
   │
   ▼
Data Quality Checker Engine
   │
   ├── Null Detection
   ├── Duplicate Detection
   ├── Range Validation
   ├── Referential Integrity
   ├── Format Validation
   └── Statistical Analysis
   │
   ▼
Results Collector
   │
   ├── JSON Report
   ├── CSV Report
   ├── Audit Logs
   └── Dashboard
```

---

## 🛠️ Tech Stack

### Backend

* Python 3.x

### Database

* SQLite

### Frontend Dashboard

* HTML
* CSS
* JavaScript
* Chart.js

### Python Modules

* sqlite3
* logging
* json
* csv
* pathlib
* statistics
* datetime
* re

---

## 📂 Project Structure

```text
data_quality_checker/
│
├── checker.py
├── dashboard.html
├── README.md
│
├── config/
│   └── dq_config.json
│
├── data/
│   └── demo.db
│
├── logs/
│   ├── critical_alerts.log
│   ├── warnings.log
│   └── audit.log
│
└── reports/
    ├── dq_report_*.json
    └── dq_report_*.csv
```

---

## 🔄 Workflow

### Step 1: Database Initialization

The system creates a demo database and populates it with sample records containing intentional data quality issues.

Generated Data:

* 150 Employees
* 500 Orders
* 20 Products
* 1000 Order Items

---

### Step 2: Validation Engine Execution

The Data Quality Engine scans all tables and executes validation checks.

---

### Step 3: Result Processing

Each validation produces a structured result object containing:

* Check ID
* Check Name
* Severity
* Affected Rows
* Failure Percentage
* Timestamp

---

### Step 4: Report Generation

The system automatically generates:

#### JSON Report

Machine-readable validation report.

#### CSV Report

Business-friendly report suitable for Excel and BI tools.

---

### Step 5: Logging

Three separate log channels are maintained:

#### critical_alerts.log

Contains critical failures requiring immediate attention.

#### warnings.log

Contains operational warnings.

#### audit.log

Contains complete execution history.

---

## ✅ Validation Checks

| ID     | Validation                                    |
| ------ | --------------------------------------------- |
| CHK-01 | Critical Null Detection                       |
| CHK-02 | Null Rate Threshold                           |
| CHK-03 | Exact Row Duplicate Detection                 |
| CHK-04 | Unique Key Violation                          |
| CHK-05 | Negative Salary Validation                    |
| CHK-06 | Salary Upper Bound Validation                 |
| CHK-07 | Negative Order Amount Validation              |
| CHK-08 | Future Date Validation                        |
| CHK-09 | Orders → Employees Referential Integrity      |
| CHK-10 | Employees → Departments Referential Integrity |
| CHK-11 | Email Format Validation                       |
| CHK-12 | Date Format Validation                        |
| CHK-13 | Statistical Outlier Detection                 |
| CHK-14 | Order Item Quantity Validation                |

---

## 📊 Dashboard Features

The dashboard provides:

* Quality Score
* Critical Incident Count
* Warning Count
* Validation Summary
* Failure Distribution
* Pipeline Health Monitoring
* Table Health Metrics
* Log Monitoring

---

## 🚨 Example Issues Detected

* Missing Email Addresses
* Duplicate Employee Emails
* Negative Salaries
* Invalid Order Amounts
* Future Order Dates
* Invalid Date Formats
* Zero or Negative Quantities

---

## 📈 Historical Tracking

The system stores every execution in the `dq_runs` table.

Benefits:

* Trend Analysis
* Quality Score Tracking
* Failure Monitoring
* Historical Reporting

---

## ▶️ Running the Project

### Clone Repository

```bash
git clone <repository-url>
cd data_quality_checker
```

### Run Application

```bash
python checker.py
```

### Open Dashboard

```bash
start dashboard.html
```

---

## 💡 Real-World Applications

### Banking

Customer Data Validation

### Healthcare

Patient Record Validation

### HR Systems

Employee Data Quality Monitoring

### E-Commerce

Order and Product Validation

### Finance

Transaction Quality Monitoring

---

## 🚀 Future Enhancements

* MySQL Integration
* PostgreSQL Integration
* Excel Report Generation
* Email Notifications
* REST APIs
* Automated Scheduling
* Real-Time Monitoring
* Dynamic Dashboard Updates

---

## 🎓 Learning Outcomes

This project demonstrates practical knowledge of:

* Python Programming
* SQL Queries
* Database Validation
* Data Engineering Concepts
* Logging Frameworks
* Report Generation
* Dashboard Development
* Data Quality Management
* Software Architecture Design

---

## 👨‍💻 Author

Mithun J

Information Science Engineering Student

Skills:
Python | SQL | MongoDB | React | Node.js | Express.js | Data Engineering | MERN Stack

---

## ⭐ Conclusion

The Production Data Quality Monitoring System automates database validation, anomaly detection, reporting, and monitoring. It provides a scalable foundation for enterprise-grade data quality management and demonstrates practical software engineering, database, and data engineering skills.
