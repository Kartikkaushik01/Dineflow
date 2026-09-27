# 🍽️ Restaurant Management System — Final Year Project

A full-stack restaurant management system built with **Python Flask + SQLite + HTML/CSS/JavaScript**.

## Features

### Customer
- Registration and secure password hashing
- Login/logout
- Menu browsing by category
- Cart and checkout
- Dine-in / takeaway order placement
- Cash / online payment status simulation
- Order history and status tracking
- Table booking
- Booking history

### Admin
- Admin authentication
- KPI dashboard
- Total revenue and today's revenue
- Order count and booking count
- Customer count
- Expense tracking and profit calculation
- Sales trend chart
- Order management and payment status
- Booking management and table assignment
- Menu CRUD / availability toggle
- Inventory management and low-stock alerts
- Customer analytics

## Demo credentials

Admin:
- Email: `admin@restaurant.com`
- Password: `admin123`

Customer:
- Email: `customer@example.com`
- Password: `customer123`

## Run on Windows

1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Create a virtual environment:

```bash
python -m venv venv
```

4. Activate it:

```bash
venv\Scripts\activate
```

5. Install packages:

```bash
pip install -r requirements.txt
```

6. Start:

```bash
python app.py
```

7. Open:
`http://127.0.0.1:5000`

The SQLite database is created automatically on first run.

## Suggested final-year presentation modules

1. Authentication & Role Management
2. Customer Ordering
3. Order Tracking
4. Table Booking
5. Menu Management
6. Inventory & Low Stock
7. Finance & Expense Tracking
8. Sales Analytics
9. Customer Analytics
10. Admin Dashboard

## Important academic note

This is a working college-project foundation. For production deployment, change the Flask secret key, disable debug mode, use environment variables, add CSRF protection, use a production database, and connect a real payment gateway rather than the included payment-status simulation.
