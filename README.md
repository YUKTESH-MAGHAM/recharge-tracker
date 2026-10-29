# Recharge Tracker — Setup & Deployment Guide

> Digital wallet for grocery allowances. FastAPI + Supabase + Vercel.

---

## Step 1 — Create a Supabase Project (free)

1. Go to [https://supabase.com](https://supabase.com) and sign up (free, no credit card).
2. Click **New project** and fill in a name + strong database password. Choose the **Asia (Mumbai)** region for best IST performance.
3. Wait ~2 minutes for provisioning.

### Set up the database

1. In your project, go to **SQL Editor** (left sidebar).
2. Paste the entire contents of [`supabase_setup.sql`](./supabase_setup.sql).
3. Click **Run** — you should see `transactions table ready ✓`.

### Get your credentials

Go to **Settings → API** and copy:

| Value | Where to use |
|-------|-------------|
| **Project URL** (`https://xxxx.supabase.co`) | Frontend (`app.js`) + Vercel env vars |
| **anon / public key** | Frontend (`app.js`) + Vercel env vars |
| **service_role key** ⚠️ Keep secret! | Vercel env vars ONLY |
| **JWT Secret** (Settings → API → JWT Settings) | Vercel env vars ONLY |

---

## Step 2 — Configure the Frontend

Open [`public/app.js`](./public/app.js) and update lines 10–11:

```js
const SUPABASE_URL  = "https://YOUR_PROJECT_REF.supabase.co";
const SUPABASE_ANON = "YOUR_ANON_KEY_HERE";
```

> ⚠️ **Only the public anon key goes here** — never the service_role key.

---

## Step 3 — Deploy to Vercel (free hobby plan)

### Option A — Vercel CLI (recommended)

```bash
# Install Vercel CLI (one-time)
npm install -g vercel

# From the project folder
cd "grocery tracker"
vercel

# Follow the prompts → link to a new project
# When asked for environment variables, add them (see below)
```

### Option B — GitHub + Vercel Dashboard

1. Push this folder to a GitHub repository.
2. Go to [https://vercel.com](https://vercel.com) → **New Project** → Import your repo.
3. Framework preset: **Other**. No build command needed.
4. Add environment variables (see below).
5. Click **Deploy**.

### Environment Variables to add in Vercel

In Vercel dashboard → your project → **Settings → Environment Variables**:

| Name | Value |
|------|-------|
| `SUPABASE_URL` | `https://your-project.supabase.co` |
| `SUPABASE_ANON_KEY` | your anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | your service_role key |
| `SUPABASE_JWT_SECRET` | your JWT secret |

> ⚠️ The service_role key and JWT secret must **never** be in frontend code.

---

## Step 4 — Enable Email Auth in Supabase

1. Supabase dashboard → **Authentication → Providers**.
2. Make sure **Email** is enabled (it is by default).
3. For local testing without email confirmation: **Authentication → Settings → Disable email confirmations**.

---

## Step 5 — Install on Android as a PWA

1. Open your Vercel app URL in **Chrome** on Android.
2. Tap the ⋮ menu → **Add to Home screen** (or look for the install banner).
3. The app installs like a native app — no app store needed.

---

## Running Locally (for development)

```bash
# Install Python deps
pip install -r requirements.txt

# Copy and fill in your env file
cp .env.example .env
# Edit .env with your actual Supabase credentials

# Run the API
uvicorn api.index:app --reload --port 8000

# Serve the frontend (in another terminal)
npx serve public -p 3000
```

Open `http://localhost:3000` in your browser.

> **Note**: The frontend `app.js` must also have your Supabase URL + anon key filled in for local use.

---

## Project Structure

```
grocery-tracker/
├── api/
│   ├── index.py          ← FastAPI app (all endpoints)
│   ├── auth.py           ← JWT token verification
│   ├── balance.py        ← Balance calculation logic
│   ├── models.py         ← Pydantic request/response models
│   └── supabase_client.py← Supabase admin client
├── public/
│   ├── index.html        ← SPA shell
│   ├── app.js            ← Frontend logic
│   ├── style.css         ← Mobile-first CSS
│   ├── manifest.json     ← PWA manifest
│   ├── sw.js             ← Service worker
│   └── icons/            ← App icons (192 + 512)
├── supabase_setup.sql    ← Run this in Supabase SQL Editor
├── vercel.json           ← Vercel routing config
├── requirements.txt      ← Python dependencies
├── .env.example          ← Environment variable template
└── README.md             ← This file
```

---

## Balance Logic (how it works)

All balances are **calculated from raw transactions** — nothing is stored:

```
wallet_balance   = Σ(recharges) − Σ(expenses)   [all time]
opening_balance  = previous day's closing balance (or 0 on day 1)
closing_balance  = opening + today's recharges − today's expenses
```

A balance carried forward is **not a new recharge** — it never appears as a transaction.

---

## Free Tier Limits

| Service | Free Tier |
|---------|-----------|
| Supabase | 500 MB database, 50,000 monthly active users |
| Vercel | Unlimited hobby deployments, 100 GB bandwidth/month |
| Supabase Auth | Unlimited email/password users on free plan |

All tools used are 100% free tier — no credit card required.
