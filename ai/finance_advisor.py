from collections import defaultdict
from ai.ml_model import MLModel


class FinanceAdvisor:
    def __init__(self):
        self.ml_model = MLModel()

    def analyze(self, user, transactions, budget):
        """
        Run full AI analysis.
        Returns dict with score, suggestions, predicted, potential, overspending.
        """
        self.ml_model.trainModel(transactions)

        total_exp    = sum(t.amount for t in transactions if t.type == "expense")
        total_inc    = sum(t.amount for t in transactions if t.type == "income")
        eff_income   = total_inc if total_inc > 0 else user.monthly_income
        savings      = eff_income - total_exp
        savings_rate = (savings / eff_income * 100) if eff_income > 0 else 0

        # Category breakdown
        cat_spend = defaultdict(float)
        for t in transactions:
            if t.type == "expense":
                cat_spend[t.category.category_name] += t.amount

        suggestions = []

        # Savings rate
        if savings_rate < 10:
            suggestions.append(f"⚠️ Savings rate is {savings_rate:.1f}%. Aim for at least 20%.")
        elif savings_rate < 20:
            suggestions.append(f"📈 Savings rate is {savings_rate:.1f}%. Try to push above 20%.")
        else:
            suggestions.append(f"✅ Great savings rate of {savings_rate:.1f}%! Keep it up.")

        # Category tips
        for cat, spent in cat_spend.items():
            if eff_income == 0: break
            pct = spent / eff_income * 100
            if cat == "Food & Dining" and pct > 30:
                suggestions.append(f"🍽️ Food spending is {pct:.1f}% of income. Cutting 20% saves ₹{spent*0.2:,.0f}/month.")
            if cat == "Entertainment" and pct > 15:
                suggestions.append(f"🎬 Entertainment at {pct:.1f}% of income. Consider a cap of 10%.")
            if cat == "Shopping" and pct > 20:
                suggestions.append(f"🛍️ Shopping is {pct:.1f}% of income. Recommended limit: ₹{eff_income*0.15:,.0f}/month.")

        # Budget alerts
        if budget:
            st = budget.status()
            if st == "EXCEEDED":
                suggestions.append(f"🚨 Budget exceeded! Spent ₹{budget.spent_amount:,.0f} vs limit ₹{budget.monthly_limit:,.0f}.")
            elif st == "WARNING":
                suggestions.append(f"⚡ Budget warning — only ₹{budget.remaining_amount:,.0f} left this month.")

        # Prediction
        predicted = self.ml_model.predictFutureExpense()
        if predicted > 0:
            suggestions.append(f"🔮 Predicted next month's expense: ₹{predicted:,.0f} (Model R²: {self.ml_model.accuracy*100:.1f}%)")

        # Anomalies
        for a in self.ml_model.detectAnomaly(transactions)[:2]:
            suggestions.append(f"🔍 Unusual spend: {a.description} — ₹{a.amount:,.0f}")

        # Emergency fund
        if eff_income > 0 and savings < eff_income * 3:
            suggestions.append(f"💰 Build an emergency fund of ₹{eff_income*3:,.0f} (3 months income).")

        # Score
        score = min(100.0, max(0.0, savings_rate * 2.5 + 20 + (
            {"GOOD": 30, "MODERATE": 20, "WARNING": 10, "EXCEEDED": 0, "NOT SET": 15}
            .get(budget.status() if budget else "NOT SET", 0)
        )))

        overspending = total_exp > user.monthly_income
        potential    = max(cat_spend.values()) * 0.2 if cat_spend else 0.0

        return {
            "score":       round(score, 1),
            "suggestions": suggestions,
            "predicted":   round(predicted, 2),
            "potential":   round(potential, 2),
            "overspending": overspending,
            "savings_rate": round(savings_rate, 1),
            "cat_spend":   dict(cat_spend),
        }

    def classify(self, description: str) -> str:
        return self.ml_model.classifyTransaction(description)
