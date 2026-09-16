# 📱 MOBIX — Mobile Shop Management System (POS & ERP)

> A modern, production-ready, full-stack Mobile Retail POS, Repair Lifecycle Management, and Smart EMI Management System built with Python Flask, SQLAlchemy, Scikit-Learn AI, and modern Glassmorphism UI.

---

## 🌟 Key Features & Modules

### 1. 📊 Executive Dashboard & Analytics
- **Live Business KPIs**: Total revenue, today's sales count, active/overdue EMIs, total inventory units, active repairs, and supplier liabilities.
- **Chart.js Visualizations**: 7-Day interactive sales revenue area chart and product category distribution doughnut chart.
- **Actionable Alerts**: Immediate warning panels for overdue EMI installments (with late fines) and low-stock handsets/accessories.

### 2. 🔐 Multi-Role Authentication & Access Control (RBAC)
- **👑 Admin**: Unrestricted access to inventory, pricing, supplier purchases, reports, and settings.
- **💰 Cashier**: POS Billing terminal, product lookup, customer registration, and printable invoices.
- **🔧 Technician**: Dedicated repair workbench, status progression, parts consumed, and diagnostic notes.

### 3. 📱 Mobile Inventory & IMEI Tracking
- Track Brand, Model, primary & secondary **IMEI numbers**, RAM/Storage variants, and color.
- Cost price, retail selling price, stock quantities, and manufacturer warranty tracking.
- Stock-in, stock-out, and automated low-stock warnings when inventory drops below safety threshold.

### 4. 🎧 Accessories & Peripherals Catalog
- Dedicated tracking for Chargers, Earphones, Power banks, Cases & Covers, Screen protectors, Cables, and Smart watches.
- One-click inline stock adjusters (`+` / `-`).

### 5. 🛒 Point of Sale (POS) Billing & Invoicing
- **Unified Cart**: Combine smartphones (with unique IMEI verification) and multiple accessories in a single bill.
- **Automated Pricing**: Real-time computation of Subtotal, GST/tax rate, instant discount, and old phone trade-in deduction.
- **Multi-Payment Modes**: Cash, UPI (GPay/PhonePe/Paytm QR), Credit/Debit Card, and Smart Store EMI.
- **Invoice Delivery**:
  - Thermal / A4 Printable receipt with print-optimized CSS.
  - Native PDF generation using **ReportLab**.
  - **WhatsApp Notification** generator with pre-filled billing details.
  - **Email Notification** (SMTP HTML template with PDF invoice attached).

### 6. 💳 Smart EMI Management with Automated Fines
- Configurable down payment and flexible tenures (3, 6, 9, 12, 18, 24 months).
- Automatically marks missed monthly payments as **Overdue** and applies configured late penalty fines (e.g., ₹200).
- Detailed customer repayment schedules and installment collection modal.

### 7. 🔧 Mobile Repair Lifecycle Management
- 5-Stage status progression pipeline: `Received` ➔ `Diagnosing` ➔ `Repairing` ➔ `Ready` ➔ `Delivered`.
- Record technician diagnostic notes, consumed spare parts, and repair warranties.
- One-click WhatsApp status update link sent directly to customer's phone.

### 8. 🤖 AI-Assisted Phone Exchange / Trade-In Predictor
- Uses **Scikit-Learn Machine Learning** (Random Forest Regression) trained on depreciation parameters.
- Evaluates fair market resale price based on: Brand retention factor, model, age in months, storage, battery health percentage, screen/body condition, and hardware functional checks.
- Direct integration into POS billing to apply instant exchange discounts.

### 9. 👥 Customer 360° Management
- Customer profiles with purchase history, active EMI contracts, repair tickets, and outstanding balances.

### 10. 🚚 Supplier & Vendor Ledger
- Vendor registration, inbound stock purchase invoices, payments, and outstanding liability tracking.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, Flask 3.1 |
| **Database** | SQLite (Default plug-and-play) / MySQL (PyMySQL ready) |
| **ORM** | Flask-SQLAlchemy / SQLAlchemy 2.0 |
| **AI / Machine Learning**| Scikit-Learn, NumPy |
| **PDF Generation** | ReportLab 5.0 |
| **Frontend UI** | Modern HTML5, Vanilla CSS3 (Glassmorphism, Dark/Light Theme) |
| **Charts** | Chart.js |
| **Icons & Fonts** | FontAwesome 6, Plus Jakarta Sans |

---

## 🚀 Quick Start Guide

### 1. Requirements
Ensure Python 3.10+ is installed on your system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

> **Note**: On first run, `seed_data.py` will automatically seed demo smartphones (iPhone 15, Galaxy S24, OnePlus 12), accessories, mock customers, active repairs, and overdue EMI schedules for immediate exploration!

---

## 🔑 Demo Login Credentials

You can click any of the quick-fill pills on the login screen or enter manually:

| Role | Username | Password |
|---|---|---|
| 👑 **Administrator** | `admin` | `admin123` |
| 💰 **Cashier** | `cashier` | `cashier123` |
| 🔧 **Technician** | `tech` | `tech123` |

---

## 🗄️ Database Configuration (SQLite vs MySQL)

### SQLite (Default)
By default, the application runs on a local SQLite database (`mobix.db`) with zero setup.

### MySQL (Optional Production)
To switch to MySQL:
1. Create a MySQL database:
   ```sql
   CREATE DATABASE mobix_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. In `.env` or system environment, set:
   ```env
   DATABASE_URL=mysql+pymysql://root:password@localhost:3306/mobix_db
   ```
3. Restart `python app.py`. SQLAlchemy will automatically create the tables and seed initial data.
