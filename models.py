from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(120), nullable=False)
    email            = db.Column(db.String(120), unique=True, nullable=False)
    phone_number     = db.Column(db.String(20))
    password_hash    = db.Column(db.String(256), nullable=False)
    monthly_income   = db.Column(db.Float, default=0.0)
    registration_date = db.Column(db.Date, default=date.today)
    preferred_budget_limit = db.Column(db.Float, default=0.0)

    # Relationships
    transactions  = db.relationship("Transaction",  backref="user", lazy=True, cascade="all, delete-orphan")
    categories    = db.relationship("Category",     backref="user", lazy=True, cascade="all, delete-orphan")
    budgets       = db.relationship("Budget",       backref="user", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_budget(self):
        return Budget.query.filter_by(user_id=self.id).first()

    def get_category_by_name(self, name):
        return Category.query.filter_by(user_id=self.id, category_name=name).first()


class Category(db.Model):
    __tablename__ = "categories"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_name  = db.Column(db.String(80), nullable=False)
    category_type  = db.Column(db.String(20), nullable=False)   # "income" / "expense"
    monthly_budget = db.Column(db.Float, default=0.0)
    total_spent    = db.Column(db.Float, default=0.0)

    transactions = db.relationship("Transaction", backref="category", lazy=True)


class Transaction(db.Model):
    __tablename__ = "transactions"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id    = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    date           = db.Column(db.Date, default=date.today)
    amount         = db.Column(db.Float, nullable=False)
    type           = db.Column(db.String(10), nullable=False)   # "income" / "expense"
    description    = db.Column(db.String(200), nullable=False)
    payment_method = db.Column(db.String(50), default="Cash")
    location       = db.Column(db.String(100), default="")


class Budget(db.Model):
    __tablename__ = "budgets"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    monthly_limit    = db.Column(db.Float, default=0.0)
    spent_amount     = db.Column(db.Float, default=0.0)
    remaining_amount = db.Column(db.Float, default=0.0)
    start_date       = db.Column(db.Date, default=date.today)
    end_date         = db.Column(db.Date, default=date.today)

    def set_limit(self, amount):
        self.monthly_limit    = amount
        self.remaining_amount = amount - self.spent_amount

    def recalculate(self):
        self.remaining_amount = self.monthly_limit - self.spent_amount

    def status(self):
        if self.monthly_limit == 0:
            return "NOT SET"
        pct = self.spent_amount / self.monthly_limit
        if pct >= 1.0:  return "EXCEEDED"
        if pct >= 0.8:  return "WARNING"
        if pct >= 0.5:  return "MODERATE"
        return "GOOD"

    def pct(self):
        if self.monthly_limit == 0: return 0.0
        return min(self.spent_amount / self.monthly_limit * 100, 100.0)


class Notification(db.Model):
    __tablename__ = "notifications"

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message           = db.Column(db.String(300), nullable=False)
    notification_type = db.Column(db.String(50))
    date_sent         = db.Column(db.DateTime, default=datetime.utcnow)
    status            = db.Column(db.String(20), default="unread")


DEFAULT_CATEGORIES = [
    ("Food & Dining",    "expense"),
    ("Transport",        "expense"),
    ("Shopping",         "expense"),
    ("Entertainment",    "expense"),
    ("Health & Medical", "expense"),
    ("Education",        "expense"),
    ("Utilities",        "expense"),
    ("Rent",             "expense"),
    ("Salary",           "income"),
    ("Freelance",        "income"),
    ("Other Income",     "income"),
    ("Other Expense",    "expense"),
]


def seed_categories(user):
    for name, ctype in DEFAULT_CATEGORIES:
        cat = Category(user_id=user.id, category_name=name, category_type=ctype)
        db.session.add(cat)
    db.session.commit()
