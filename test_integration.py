# -*- coding: utf-8 -*-
import os, sys, urllib.request, json
sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv()
from supabase import create_client

anon = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
r = anon.auth.sign_in_with_password({"email": "testuser@recharge.local", "password": "Test@12345"})
token = r.session.access_token
headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

def api(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request("http://127.0.0.1:8000" + path, headers=headers, method=method, data=data)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

errors = []

def check(label, actual, expected):
    ok = actual == expected
    print(("[PASS]" if ok else "[FAIL]") + " " + label + " | got=" + str(actual) + " expected=" + str(expected))
    if not ok:
        errors.append(label)

# Delete all test transactions first (clean slate)
s, txns = api("GET", "/api/transactions")
for t in (txns if isinstance(txns, list) else []):
    api("DELETE", "/api/transactions/" + t["id"])
print("Cleaned", len(txns) if isinstance(txns, list) else 0, "old transactions")

# Test 1: initial balance = 0
s, d = api("GET", "/api/balance")
print("GET /api/balance:", s)
check("Initial wallet balance", d.get("wallet_balance"), 0.0)

# Test 2: add recharge 1000
s, d = api("POST", "/api/transactions", {"type": "recharge", "name": "Recharge", "amount": 1000})
print("POST recharge 1000:", s, "id=" + str(d.get("id", d.get("detail", ""))[:20]))
check("Recharge created", s, 201)

# Test 3: add expense 150
s, d = api("POST", "/api/transactions", {"type": "expense", "name": "Tiffin", "amount": 150})
print("POST expense 150:", s)
check("Expense created", s, 201)

# Test 4: balance = 1000 - 150 = 850
s, d = api("GET", "/api/balance")
check("Wallet balance after txns", d.get("wallet_balance"), 850.0)
check("Today received", d.get("today_received"), 1000.0)
check("Today spent", d.get("today_spent"), 150.0)

# Test 5: daily ledger
s, d = api("GET", "/api/reports/daily")
print("GET /api/reports/daily:", s, "days=" + str(len(d)))
check("Daily ledger has 1 day", len(d), 1)
if d:
    check("Today closing balance", d[0]["closing_balance"], 850.0)
    check("Transactions count", len(d[0]["transactions"]), 2)

# Test 6: overdraft prevention
s, d = api("POST", "/api/transactions", {"type": "expense", "name": "Too much", "amount": 99999})
check("Overdraft rejected", s, 422)

# Test 7: weekly report
s, d = api("GET", "/api/reports/weekly")
print("GET /api/reports/weekly:", s)
check("Weekly report status", s, 200)
check("Weekly total received", d.get("total_received"), 1000.0)
check("Weekly total spent", d.get("total_spent"), 150.0)
check("Weekly closing", d.get("closing_balance"), 850.0)

# Test 8: monthly report
s, d = api("GET", "/api/reports/monthly")
print("GET /api/reports/monthly:", s)
check("Monthly report status", s, 200)
check("Monthly closing", d.get("closing_balance"), 850.0)

print("")
if errors:
    print("FAILED: " + str(len(errors)) + " tests -> " + str(errors))
    sys.exit(1)
else:
    print("ALL " + str(8) + " INTEGRATION TESTS PASSED")
