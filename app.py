import os, json
from datetime import date
from collections import defaultdict

from flask import (Flask, render_template, redirect, url_for,
                   request, flash, jsonify, session)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)

from config import Config
from models import db, User, Category, Transaction, Budget, Notification, seed_categories
from ai.finance_advisor import FinanceAdvisor

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

advisor = FinanceAdvisor()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── DB init ───────────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name   = request.form.get("name", "").strip()
        email  = request.form.get("email", "").strip().lower()
        phone  = request.form.get("phone", "").strip()
        pwd    = request.form.get("password", "")
        income = request.form.get("monthly_income", "0")

        if not all([name, email, phone, pwd, income]):
            flash("Please fill in all fields.", "danger")
            return render_template("auth/register.html")
        try:
            income = float(income)
        except ValueError:
            flash("Enter a valid income amount.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html")

        user = User(name=name, email=email, phone_number=phone,
                    monthly_income=income,
                    preferred_budget_limit=income * 0.8)
        user.set_password(pwd)
        db.session.add(user)
        db.session.flush()   # get user.id before commit

        seed_categories(user)

        budget = Budget(user_id=user.id,
                        monthly_limit=income * 0.8,
                        remaining_amount=income * 0.8,
                        start_date=date.today().replace(day=1),
                        end_date=date.today().replace(day=28))
        db.session.add(budget)
        db.session.commit()

        login_user(user)
        flash(f"Welcome, {user.name}! Your account has been created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pwd   = request.form.get("password", "")
        user  = User.query.filter_by(email=email).first()
        if user and user.check_password(pwd):
            login_user(user, remember=True)
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/dashboard")
@login_required
def dashboard():
    today  = date.today()
    txns   = Transaction.query.filter_by(user_id=current_user.id).all()
    mt     = [t for t in txns if t.date.month == today.month and t.date.year == today.year]
    inc    = sum(t.amount for t in mt if t.type == "income")
    exp    = sum(t.amount for t in mt if t.type == "expense")
    sav    = (inc - exp) if inc > 0 else current_user.monthly_income - exp
    budget = current_user.get_budget()
    recent = sorted(txns, key=lambda t: t.date, reverse=True)[:8]
    return render_template("dashboard/dashboard.html",
                           income=inc, expense=exp, savings=sav,
                           txn_count=len(mt), budget=budget,
                           recent=recent)


# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/transactions")
@login_required
def transactions():
    f   = request.args.get("filter", "all").lower()
    q   = request.args.get("q", "").lower()
    qry = Transaction.query.filter_by(user_id=current_user.id)
    if f in ("income", "expense"):
        qry = qry.filter_by(type=f)
    txns = sorted(qry.all(), key=lambda t: t.date, reverse=True)
    if q:
        txns = [t for t in txns if q in t.description.lower()]
    return render_template("dashboard/transactions.html",
                           transactions=txns, filter=f, q=q)


@app.route("/transactions/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
        except ValueError:
            flash("Enter a valid amount.", "danger")
            return render_template("dashboard/add_transaction.html", categories=categories)

        desc   = request.form.get("description", "").strip()
        t_type = request.form.get("type", "expense")
        cat_id = request.form.get("category_id")
        pm     = request.form.get("payment_method", "Cash")
        loc    = request.form.get("location", "")

        if not desc or not cat_id:
            flash("Description and category are required.", "danger")
            return render_template("dashboard/add_transaction.html", categories=categories)

        cat = Category.query.get(int(cat_id))
        if not cat or cat.user_id != current_user.id:
            flash("Invalid category.", "danger")
            return render_template("dashboard/add_transaction.html", categories=categories)

        txn = Transaction(user_id=current_user.id, category_id=cat.id,
                          amount=amount, type=t_type,
                          description=desc, payment_method=pm, location=loc)
        db.session.add(txn)

        # Update budget and category totals
        if t_type == "expense":
            budget = current_user.get_budget()
            if budget:
                budget.spent_amount += amount
                budget.recalculate()
            cat.total_spent += amount

        db.session.commit()
        flash("Transaction added successfully!", "success")
        return redirect(url_for("transactions"))

    return render_template("dashboard/add_transaction.html", categories=categories)


@app.route("/transactions/delete/<int:txn_id>", methods=["POST"])
@login_required
def delete_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != current_user.id:
        flash("Unauthorised.", "danger")
        return redirect(url_for("transactions"))
    if txn.type == "expense":
        budget = current_user.get_budget()
        if budget:
            budget.spent_amount = max(0, budget.spent_amount - txn.amount)
            budget.recalculate()
        txn.category.total_spent = max(0, txn.category.total_spent - txn.amount)
    db.session.delete(txn)
    db.session.commit()
    flash("Transaction deleted.", "success")
    return redirect(url_for("transactions"))


@app.route("/api/classify", methods=["POST"])
@login_required
def classify():
    desc      = request.json.get("description", "")
    suggested = advisor.classify(desc)
    cat       = current_user.get_category_by_name(suggested)
    return jsonify({"category": suggested, "category_id": cat.id if cat else None})


# ═══════════════════════════════════════════════════════════════════════════════
#  BUDGET
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    b = current_user.get_budget()
    if request.method == "POST":
        try:
            new_limit = float(request.form["monthly_limit"])
        except ValueError:
            flash("Enter a valid amount.", "danger")
            return render_template("dashboard/budget.html", budget=b)
        if b:
            b.set_limit(new_limit)
        else:
            b = Budget(user_id=current_user.id, monthly_limit=new_limit,
                       remaining_amount=new_limit)
            db.session.add(b)
        db.session.commit()
        flash(f"Budget updated to ₹{new_limit:,.0f}!", "success")
        return redirect(url_for("budget"))
    return render_template("dashboard/budget.html", budget=b)


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/reports")
@login_required
def reports():
    today  = date.today()
    txns   = Transaction.query.filter_by(user_id=current_user.id).all()
    mt     = [t for t in txns if t.date.month == today.month and t.date.year == today.year]
    inc    = sum(t.amount for t in mt if t.type == "income")
    exp    = sum(t.amount for t in mt if t.type == "expense")
    sav    = inc - exp

    cat_spend = defaultdict(float)
    for t in mt:
        if t.type == "expense":
            cat_spend[t.category.category_name] += t.amount
    top_cat = max(cat_spend, key=cat_spend.get) if cat_spend else "N/A"

    # Monthly trend (last 6 months)
    monthly = defaultdict(float)
    for t in txns:
        if t.type == "expense":
            key = f"{t.date.year}-{t.date.month:02d}"
            monthly[key] += t.amount
    trend = dict(sorted(monthly.items())[-6:])

    return render_template("dashboard/reports.html",
                           income=inc, expense=exp, savings=sav,
                           top_cat=top_cat,
                           cat_spend=json.dumps(dict(cat_spend)),
                           trend_labels=json.dumps(list(trend.keys())),
                           trend_values=json.dumps(list(trend.values())))


# ═══════════════════════════════════════════════════════════════════════════════
#  AI ADVISOR
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/ai")
@login_required
def ai_advisor():
    return render_template("dashboard/ai_advisor.html")


@app.route("/api/ai-analyze", methods=["POST"])
@login_required
def ai_analyze():
    txns   = Transaction.query.filter_by(user_id=current_user.id).all()
    budget = current_user.get_budget()

    # Convert DB transactions to simple objects for ML model
    class TxnProxy:
        def __init__(self, t):
            self.amount      = t.amount
            self.type        = t.type
            self.description = t.description
            self.date        = t.date
            class CatProxy:
                def __init__(self, c): self.category_name = c.category_name
            self.category = CatProxy(t.category)

    proxies = [TxnProxy(t) for t in txns]
    result  = advisor.analyze(current_user, proxies, budget)

    # Save budget alert notifications
    if budget and budget.status() in ("EXCEEDED", "WARNING"):
        msg = (f"Budget exceeded! Spent ₹{budget.spent_amount:,.0f}"
               if budget.status() == "EXCEEDED"
               else f"Budget warning — ₹{budget.remaining_amount:,.0f} remaining")
        n = Notification(user_id=current_user.id, message=msg,
                         notification_type="budget_alert")
        db.session.add(n)
        db.session.commit()

    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    notifications = (Notification.query
                     .filter_by(user_id=current_user.id, status="unread")
                     .order_by(Notification.date_sent.desc())
                     .limit(10).all())
    if request.method == "POST":
        current_user.name         = request.form.get("name", current_user.name).strip()
        current_user.phone_number = request.form.get("phone", current_user.phone_number).strip()
        try:
            current_user.monthly_income = float(request.form.get("monthly_income", current_user.monthly_income))
        except ValueError:
            flash("Enter a valid income.", "danger")
            return render_template("dashboard/profile.html", notifications=notifications)
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("profile"))

    return render_template("dashboard/profile.html", notifications=notifications)


if __name__ == "__main__":
    app.run(debug=True)
