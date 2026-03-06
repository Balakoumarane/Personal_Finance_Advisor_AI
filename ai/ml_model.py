import numpy as np
from datetime import date
from collections import defaultdict


class MLModel:
    _id_counter = 1

    def __init__(self, model_type: str = "LinearRegression"):
        self.model_id = MLModel._id_counter
        MLModel._id_counter += 1
        self.model_type = model_type
        self.accuracy = 0.0
        self.training_dataset = ""
        self.last_trained_date = date.today()
        self._model = None
        self._trained = False
        self._category_keywords = {
            "Food & Dining":    ["food","restaurant","eat","lunch","dinner","breakfast","swiggy","zomato","cafe","pizza","biryani","hotel"],
            "Transport":        ["uber","ola","bus","train","fuel","petrol","auto","metro","cab","travel","taxi"],
            "Shopping":         ["amazon","flipkart","mall","clothes","shirt","shoes","grocery","supermarket","shop"],
            "Entertainment":    ["movie","netflix","spotify","game","concert","show","ticket","cinema","hotstar"],
            "Health & Medical": ["doctor","hospital","medicine","pharmacy","health","gym","clinic","apollo"],
            "Education":        ["book","course","fee","college","school","tuition","udemy","study"],
            "Utilities":        ["electricity","water","internet","wifi","bill","phone","recharge","gas"],
            "Rent":             ["rent","house","flat","pg","hostel","deposit"],
        }

    def trainModel(self, transactions: list):
        """Train a simple linear regression from scratch using numpy."""
        monthly = defaultdict(float)
        for t in transactions:
            if t.type == "expense":
                key = (t.date.year, t.date.month)
                monthly[key] += t.amount

        if len(monthly) < 2:
            self._trained = False
            return

        sorted_keys = sorted(monthly.keys())
        x = np.array(range(len(sorted_keys)), dtype=float)
        y = np.array([monthly[k] for k in sorted_keys], dtype=float)

        # Manual linear regression: y = mx + b
        n = len(x)
        x_mean, y_mean = x.mean(), y.mean()
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        self._m = numerator / denominator if denominator != 0 else 0
        self._b = y_mean - self._m * x_mean
        self._n_months = len(sorted_keys)

        # Compute R² accuracy
        y_pred = self._m * x + self._b
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        self.accuracy = float(1 - ss_res / ss_tot) if ss_tot != 0 else 1.0
        self.accuracy = max(0.0, min(1.0, self.accuracy))

        self._trained = True
        self.training_dataset = f"{len(transactions)} transactions"
        self.last_trained_date = date.today()

    def predictFutureExpense(self) -> float:
        """Predict next month's expense using trained linear regression."""
        if not self._trained:
            return 0.0
        prediction = self._m * self._n_months + self._b
        return max(0.0, float(prediction))

    def classifyTransaction(self, description: str) -> str:
        """Classify a transaction description into a category using keyword matching."""
        desc_lower = description.lower()
        for category, keywords in self._category_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                return category
        return "Other Expense"

    def detectAnomaly(self, transactions: list) -> list:
        """
        Detect anomalous expense transactions using Z-score method.
        Returns list of anomalous transactions.
        """
        expenses = [t for t in transactions if t.type == "expense"]
        if len(expenses) < 3:
            return []

        amounts = np.array([t.amount for t in expenses])
        mean = amounts.mean()
        std = amounts.std()

        if std == 0:
            return []

        anomalies = []
        for t in expenses:
            z_score = abs(t.amount - mean) / std
            if z_score > 2.0:
                anomalies.append(t)
        return anomalies

    def evaluateModel(self) -> float:
        return self.accuracy

    def getMonthlySpendingTrend(self, transactions: list) -> dict:
        """Return spending per month for trend visualization."""
        monthly = defaultdict(float)
        for t in transactions:
            if t.type == "expense":
                key = f"{t.date.year}-{t.date.month:02d}"
                monthly[key] += t.amount
        return dict(sorted(monthly.items()))
