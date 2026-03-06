# 💰 AI Finance Advisor — Web App

Flask + PostgreSQL web app deployable to Railway or Render.

## 📁 Structure
```
finance_web/
├── app.py              ← All Flask routes
├── models.py           ← SQLAlchemy DB models
├── config.py           ← DB + secret key config
├── requirements.txt
├── Procfile            ← For deployment
├── .env.example        ← Copy to .env for local dev
├── .gitignore
├── ai/
│   ├── ml_model.py
│   └── finance_advisor.py
└── templates/
    ├── base.html
    ├── auth/           ← login, register
    └── dashboard/      ← all app pages
```

---

## 💻 Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env file
cp .env.example .env
# Edit .env — set SECRET_KEY to any random string
# Leave DATABASE_URL empty to use local SQLite

# 3. Run
python app.py
```
Open http://localhost:5000

---

## 🚀 Deploy to Railway (Free)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/finance-advisor.git
git push -u origin main
```

### Step 2 — Create Railway project
1. Go to https://railway.app and sign in with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select your repository

### Step 3 — Add PostgreSQL
1. In your Railway project, click **+ New → Database → PostgreSQL**
2. Railway auto-sets `DATABASE_URL` in your environment ✅

### Step 4 — Set environment variables
In Railway → your service → **Variables**, add:
```
SECRET_KEY = any-long-random-string-here
```
Railway already sets `DATABASE_URL` from the Postgres plugin — you don't need to add it.

### Step 5 — Deploy
Railway auto-deploys on every `git push`. Your app will be live at:
```
https://your-app-name.up.railway.app
```

---

## 🔁 Deploy to Render (Alternative)

1. Push to GitHub (same as above)
2. Go to https://render.com → New → Web Service
3. Connect your repo
4. Set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
5. Add a **PostgreSQL** database from Render dashboard
6. Copy the **Internal Database URL** → set as `DATABASE_URL` env var
7. Set `SECRET_KEY` env var

---

## 🗄️ Database

- **Local dev**: SQLite (`finance.db` auto-created, ignored by git)
- **Production**: PostgreSQL (set `DATABASE_URL` env var)
- Tables are created automatically on first run (`db.create_all()`)
- No migrations needed for initial deploy

---

## 🔒 Security Notes

- `.env` is in `.gitignore` — never commit it
- Passwords are hashed with `werkzeug.security`
- Each user only sees their own data (all queries filter by `user_id`)
