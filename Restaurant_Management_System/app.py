from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"
DB = Path(__file__).with_name("restaurant.db")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS menu_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image TEXT,
        available INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        order_type TEXT NOT NULL DEFAULT 'Dine-In',
        table_no TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        payment_method TEXT NOT NULL DEFAULT 'Cash',
        payment_status TEXT NOT NULL DEFAULT 'Pending',
        total REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        menu_item_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY(menu_item_id) REFERENCES menu_items(id)
    );
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        booking_date TEXT NOT NULL,
        booking_time TEXT NOT NULL,
        guests INTEGER NOT NULL,
        table_no TEXT,
        status TEXT NOT NULL DEFAULT 'Booked',
        created_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT,
        expense_date TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        unit TEXT NOT NULL,
        quantity REAL NOT NULL DEFAULT 0,
        reorder_level REAL NOT NULL DEFAULT 5,
        cost_per_unit REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    );
    """)

    admin = conn.execute("SELECT id FROM users WHERE email=?", ("admin@restaurant.com",)).fetchone()
    if not admin:
        conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                     ("Restaurant Admin","admin@restaurant.com",generate_password_hash("admin123"),"admin",datetime.now().isoformat()))
    customer = conn.execute("SELECT id FROM users WHERE email=?", ("customer@example.com",)).fetchone()
    if not customer:
        conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                     ("Demo Customer","customer@example.com",generate_password_hash("customer123"),"customer",datetime.now().isoformat()))

    if conn.execute("SELECT COUNT(*) c FROM menu_items").fetchone()["c"] == 0:
        items = [
            ("Paneer Tikka","Starters","Smoky cottage cheese with spices",220),
            ("Veg Biryani","Main Course","Aromatic basmati rice and vegetables",260),
            ("Butter Chicken","Main Course","Creamy tomato chicken curry",340),
            ("Masala Dosa","South Indian","Crispy dosa with potato masala",160),
            ("Veg Burger","Fast Food","Grilled vegetable patty burger",190),
            ("Margherita Pizza","Pizza","Classic cheese and tomato pizza",299),
            ("French Fries","Sides","Crispy salted fries",120),
            ("Chocolate Brownie","Desserts","Warm brownie with chocolate sauce",150),
            ("Cold Coffee","Beverages","Chilled creamy coffee",130),
            ("Fresh Lime Soda","Beverages","Refreshing lime and soda",90),
        ]
        conn.executemany("INSERT INTO menu_items(name,category,description,price) VALUES(?,?,?,?)", items)

    if conn.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"] == 0:
        inv = [
            ("Rice","kg",35,10,70),("Paneer","kg",8,3,280),("Chicken","kg",12,4,240),
            ("Cooking Oil","L",18,5,140),("Flour","kg",25,8,45),("Coffee","kg",4,1,650),
            ("Cheese","kg",6,2,420),("Vegetables","kg",30,10,65)
        ]
        conn.executemany("INSERT INTO inventory(item_name,unit,quantity,reorder_level,cost_per_unit,updated_at) VALUES(?,?,?,?,?,?)",
                         [(a,b,c,d,e,datetime.now().isoformat()) for a,b,c,d,e in inv])
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_user():
    return {"current_user": session}

@app.route("/")
def index():
    conn = db()
    menu = conn.execute("SELECT * FROM menu_items WHERE available=1 ORDER BY category,name").fetchall()
    conn.close()
    return render_template("index.html", menu=menu)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name,email,password = request.form["name"].strip(),request.form["email"].strip().lower(),request.form["password"]
        try:
            conn=db()
            conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                         (name,email,generate_password_hash(password),"customer",datetime.now().isoformat()))
            conn.commit(); conn.close()
            flash("Account created. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email is already registered.", "error")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email,password=request.form["email"].strip().lower(),request.form["password"]
        conn=db(); user=conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone(); conn.close()
        if user and check_password_hash(user["password"],password):
            session.clear(); session["user_id"]=user["id"]; session["name"]=user["name"]; session["role"]=user["role"]
            return redirect(url_for("admin_dashboard") if user["role"]=="admin" else url_for("menu"))
        flash("Invalid email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/menu")
def menu():
    conn=db(); items=conn.execute("SELECT * FROM menu_items WHERE available=1 ORDER BY category,name").fetchall(); conn.close()
    return render_template("menu.html", menu=items)

@app.route("/cart")
@login_required
def cart():
    return render_template("cart.html")

@app.route("/api/order", methods=["POST"])
@login_required
def create_order():
    data=request.get_json()
    items=data.get("items",[])
    if not items: return jsonify(error="Cart is empty"),400
    conn=db()
    total=0; verified=[]
    for item in items:
        row=conn.execute("SELECT * FROM menu_items WHERE id=? AND available=1",(item["id"],)).fetchone()
        if not row: continue
        qty=max(1,int(item.get("qty",1)))
        sub=row["price"]*qty; total+=sub
        verified.append((row,qty,sub))
    if not verified: conn.close(); return jsonify(error="No valid items"),400
    cur=conn.execute("""INSERT INTO orders(customer_id,customer_name,order_type,table_no,status,payment_method,payment_status,total,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                     (session["user_id"],session["name"],data.get("order_type","Takeaway"),data.get("table_no",""),
                      "Pending",data.get("payment_method","Cash"),"Paid" if data.get("payment_method")=="Online" else "Pending",
                      total,datetime.now().isoformat()))
    oid=cur.lastrowid
    conn.executemany("""INSERT INTO order_items(order_id,menu_item_id,item_name,qty,price,subtotal) VALUES(?,?,?,?,?,?)""",
                     [(oid,r["id"],r["name"],q,r["price"],s) for r,q,s in verified])
    conn.commit(); conn.close()
    return jsonify(order_id=oid,total=total)

@app.route("/orders")
@login_required
def orders():
    conn=db()
    rows=conn.execute("SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC",(session["user_id"],)).fetchall()
    conn.close(); return render_template("orders.html", orders=rows)

@app.route("/api/booking", methods=["POST"])
@login_required
def create_booking():
    data=request.get_json()
    if not all(data.get(k) for k in ["phone","booking_date","booking_time","guests"]):
        return jsonify(error="Please fill all booking fields"),400
    conn=db()
    conn.execute("""INSERT INTO bookings(customer_id,customer_name,phone,booking_date,booking_time,guests,table_no,status,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                 (session["user_id"],session["name"],data["phone"],data["booking_date"],data["booking_time"],
                  int(data["guests"]),None,"Booked",datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify(success=True)

@app.route("/bookings")
@login_required
def bookings():
    conn=db(); rows=conn.execute("SELECT * FROM bookings WHERE customer_id=? ORDER BY booking_date,booking_time",(session["user_id"],)).fetchall(); conn.close()
    return render_template("bookings.html", bookings=rows)

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    today = date.today().isoformat()

    metrics = {
        "revenue": conn.execute(
            "SELECT COALESCE(SUM(total),0) v FROM orders WHERE payment_status='Paid'"
        ).fetchone()["v"],
        "today_revenue": conn.execute(
            "SELECT COALESCE(SUM(total),0) v FROM orders WHERE payment_status='Paid' AND date(created_at)=?",
            (today,)
        ).fetchone()["v"],
        "orders": conn.execute("SELECT COUNT(*) v FROM orders").fetchone()["v"],
        "bookings": conn.execute("SELECT COUNT(*) v FROM bookings").fetchone()["v"],
        "customers": conn.execute(
            "SELECT COUNT(*) v FROM users WHERE role='customer'"
        ).fetchone()["v"],
        "expenses": conn.execute(
            "SELECT COALESCE(SUM(amount),0) v FROM expenses"
        ).fetchone()["v"],
    }

    recent = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC LIMIT 8"
    ).fetchall()

    low = conn.execute(
        "SELECT * FROM inventory WHERE quantity<=reorder_level ORDER BY quantity"
    ).fetchall()

    sales = conn.execute(
        """SELECT date(created_at) day, SUM(total) total
           FROM orders
           WHERE payment_status='Paid'
           GROUP BY date(created_at)
           ORDER BY day DESC
           LIMIT 7"""
    ).fetchall()

    # Convert SQLite Row objects into normal dictionaries for JSON/Chart.js.
    sales_data = [dict(row) for row in reversed(sales)]

    conn.close()

    return render_template(
        "admin.html",
        m=metrics,
        recent=recent,
        low=low,
        sales=sales_data
    )


@app.route("/admin/orders", methods=["GET","POST"])
@admin_required
def admin_orders():
    conn=db()
    if request.method=="POST":
        oid=request.form["order_id"]; status=request.form["status"]; payment=request.form["payment_status"]
        conn.execute("UPDATE orders SET status=?,payment_status=? WHERE id=?",(status,payment,oid)); conn.commit()
    orders=conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close(); return render_template("admin_orders.html",orders=orders)

@app.route("/admin/bookings", methods=["GET","POST"])
@admin_required
def admin_bookings():
    conn=db()
    if request.method=="POST":
        conn.execute("UPDATE bookings SET status=?,table_no=? WHERE id=?",
                     (request.form["status"],request.form.get("table_no",""),request.form["booking_id"])); conn.commit()
    rows=conn.execute("SELECT * FROM bookings ORDER BY booking_date,booking_time").fetchall()
    conn.close(); return render_template("admin_bookings.html",bookings=rows)

@app.route("/admin/menu", methods=["GET","POST"])
@admin_required
def admin_menu():
    conn=db()
    if request.method=="POST":
        action=request.form["action"]
        if action=="add":
            conn.execute("INSERT INTO menu_items(name,category,description,price,available) VALUES(?,?,?,?,1)",
                         (request.form["name"],request.form["category"],request.form["description"],float(request.form["price"])))
        elif action=="toggle":
            conn.execute("UPDATE menu_items SET available=1-available WHERE id=?",(request.form["id"],))
        elif action=="delete":
            conn.execute("DELETE FROM menu_items WHERE id=?",(request.form["id"],))
        conn.commit()
    items=conn.execute("SELECT * FROM menu_items ORDER BY category,name").fetchall(); conn.close()
    return render_template("admin_menu.html",menu=items)

@app.route("/admin/finance", methods=["GET","POST"])
@admin_required
def admin_finance():
    conn=db()
    if request.method=="POST":
        conn.execute("INSERT INTO expenses(title,category,amount,notes,expense_date,created_at) VALUES(?,?,?,?,?,?)",
                     (request.form["title"],request.form["category"],float(request.form["amount"]),request.form["notes"],
                      request.form["expense_date"],datetime.now().isoformat())); conn.commit()
    revenue=conn.execute("SELECT COALESCE(SUM(total),0) v FROM orders WHERE payment_status='Paid'").fetchone()["v"]
    expense=conn.execute("SELECT COALESCE(SUM(amount),0) v FROM expenses").fetchone()["v"]
    expenses=conn.execute("SELECT * FROM expenses ORDER BY expense_date DESC,id DESC").fetchall()
    conn.close()
    return render_template("finance.html",revenue=revenue,expense=expense,profit=revenue-expense,expenses=expenses)

@app.route("/admin/inventory", methods=["GET","POST"])
@admin_required
def admin_inventory():
    conn=db()
    if request.method=="POST":
        conn.execute("UPDATE inventory SET quantity=?,reorder_level=?,cost_per_unit=?,updated_at=? WHERE id=?",
                     (float(request.form["quantity"]),float(request.form["reorder_level"]),float(request.form["cost_per_unit"]),
                      datetime.now().isoformat(),request.form["id"])); conn.commit()
    items=conn.execute("SELECT * FROM inventory ORDER BY item_name").fetchall(); conn.close()
    return render_template("inventory.html",inventory=items)

@app.route("/admin/customers")
@admin_required
def admin_customers():
    conn=db()
    customers=conn.execute("""SELECT u.id,u.name,u.email,u.created_at,COUNT(o.id) orders,COALESCE(SUM(o.total),0) spend
                              FROM users u LEFT JOIN orders o ON o.customer_id=u.id
                              WHERE u.role='customer' GROUP BY u.id ORDER BY spend DESC""").fetchall()
    conn.close(); return render_template("customers.html",customers=customers)

if __name__=="__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
