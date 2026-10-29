// ============================================================
// RECHARGE TRACKER — Frontend Application
// Credentials are injected at runtime via index.html <meta> tags
// so they are NEVER hardcoded in this file or committed to git.
// ============================================================

const SUPABASE_URL  = document.querySelector('meta[name="sb-url"]')?.content  || "";
const SUPABASE_ANON = document.querySelector('meta[name="sb-anon"]')?.content || "";

// ─────────────────────────────────────────────────────────────
// AUTH STATE
// ─────────────────────────────────────────────────────────────
let supabaseClient = null;
let currentSession = null;

// ─────────────────────────────────────────────────────────────
// INIT — load Supabase JS SDK dynamically
// ─────────────────────────────────────────────────────────────
async function initSupabase() {
  const { createClient } = supabase;
  supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON, {
    auth: { persistSession: true, autoRefreshToken: true }
  });

  const { data: { session } } = await supabaseClient.auth.getSession();
  if (session) {
    currentSession = session;
    showApp();
  } else {
    showAuth();
  }

  supabaseClient.auth.onAuthStateChange((_event, session) => {
    currentSession = session;
    if (session) showApp();
    else showAuth();
  });
}

// ─────────────────────────────────────────────────────────────
// AUTH UI
// ─────────────────────────────────────────────────────────────
function showAuth() {
  document.getElementById("auth-screen").style.display = "flex";
  document.getElementById("app-screen").classList.remove("visible");
}

function showApp() {
  document.getElementById("auth-screen").style.display = "none";
  document.getElementById("app-screen").classList.add("visible");
  loadDashboard();
}

// Auth tabs
document.querySelectorAll(".auth-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("login-form").classList.toggle("hidden", tab.dataset.tab !== "login");
    document.getElementById("signup-form").classList.toggle("hidden", tab.dataset.tab !== "signup");
    document.getElementById("auth-msg").textContent = "";
  });
});

// Login
document.getElementById("btn-login").addEventListener("click", async () => {
  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const msg      = document.getElementById("auth-msg");
  const btn      = document.getElementById("btn-login");

  if (!email || !password) { msg.textContent = "Please enter email and password."; msg.className = "auth-msg error"; return; }

  btn.disabled = true; btn.textContent = "Signing in…";
  const { error } = await supabaseClient.auth.signInWithPassword({ email, password });
  btn.disabled = false; btn.textContent = "Sign In";

  if (error) { msg.textContent = error.message; msg.className = "auth-msg error"; }
});

// Signup
document.getElementById("btn-signup").addEventListener("click", async () => {
  const email    = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;
  const msg      = document.getElementById("auth-msg");
  const btn      = document.getElementById("btn-signup");

  if (!email || !password) { msg.textContent = "Please enter email and password."; msg.className = "auth-msg error"; return; }
  if (password.length < 6) { msg.textContent = "Password must be at least 6 characters."; msg.className = "auth-msg error"; return; }

  btn.disabled = true; btn.textContent = "Creating account…";
  const { error } = await supabaseClient.auth.signUp({ email, password });
  btn.disabled = false; btn.textContent = "Create Account";

  if (error) {
    msg.textContent = error.message; msg.className = "auth-msg error";
  } else {
    msg.textContent = "Account created! Check your email to confirm, then sign in.";
    msg.className = "auth-msg success";
  }
});

// Logout
document.getElementById("btn-logout").addEventListener("click", async () => {
  await supabaseClient.auth.signOut();
});

// ─────────────────────────────────────────────────────────────
// API HELPERS
// ─────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  if (!currentSession) throw new Error("Not authenticated");
  const token = currentSession.access_token;
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      ...(options.headers || {})
    }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ─────────────────────────────────────────────────────────────
// FORMATTING HELPERS
// ─────────────────────────────────────────────────────────────
const fmt = (n) => "₹" + parseFloat(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ─────────────────────────────────────────────────────────────
// NAVIGATION
// ─────────────────────────────────────────────────────────────
let activeView = "daily";

document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => {
    const view = btn.dataset.view;
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.getElementById(`view-${view}`).classList.add("active");
    activeView = view;
    if (view === "weekly")  loadWeeklyReport();
    if (view === "monthly") loadMonthlyReport();
  });
});

// ─────────────────────────────────────────────────────────────
// DASHBOARD LOAD
// ─────────────────────────────────────────────────────────────
async function loadDashboard() {
  await Promise.all([loadBalance(), loadDailyLedger()]);
}

// ─────────────────────────────────────────────────────────────
// WALLET BALANCE
// ─────────────────────────────────────────────────────────────
async function loadBalance() {
  try {
    const data = await apiFetch("/api/balance");
    document.getElementById("wallet-balance").textContent = fmt(data.wallet_balance);
    document.getElementById("today-received").textContent = fmt(data.today_received);
    document.getElementById("today-spent").textContent    = fmt(data.today_spent);
    document.getElementById("today-closing").textContent  = fmt(data.today_closing);
  } catch (e) {
    console.error("Balance load error:", e);
  }
}

// ─────────────────────────────────────────────────────────────
// TRANSACTION ENTRY FORM
// ─────────────────────────────────────────────────────────────
let selectedType = "expense";
let submitting   = false;

function setType(type) {
  selectedType = type;
  const expBtn = document.getElementById("btn-type-expense");
  const recBtn = document.getElementById("btn-type-recharge");
  const nameInput = document.getElementById("txn-name");

  expBtn.classList.remove("active-expense", "active-recharge");
  recBtn.classList.remove("active-expense", "active-recharge");

  if (type === "expense") {
    expBtn.classList.add("active-expense");
    nameInput.value    = "";
    nameInput.readOnly = false;
    nameInput.placeholder = "e.g. Milk, Vegetables…";
  } else {
    recBtn.classList.add("active-recharge");
    nameInput.value    = "Recharge";
    nameInput.readOnly = true;
  }
}

document.getElementById("btn-type-expense").addEventListener("click",   () => setType("expense"));
document.getElementById("btn-type-recharge").addEventListener("click",  () => setType("recharge"));

document.getElementById("btn-save").addEventListener("click", async () => {
  if (submitting) return;

  const name   = document.getElementById("txn-name").value.trim();
  const amount = parseFloat(document.getElementById("txn-amount").value);
  const msg    = document.getElementById("save-msg");

  if (!name)       { showSaveMsg("Enter an item name.", "err"); return; }
  if (!amount || amount <= 0) { showSaveMsg("Enter a valid amount.", "err"); return; }

  submitting = true;
  const btn  = document.getElementById("btn-save");
  btn.disabled = true;
  btn.textContent = "Saving…";
  msg.textContent = "";

  try {
    await apiFetch("/api/transactions", {
      method: "POST",
      body: JSON.stringify({ type: selectedType, name, amount })
    });
    document.getElementById("txn-amount").value = "";
    showSaveMsg(selectedType === "recharge" ? "✓ Recharge saved!" : `✓ ${name} saved!`, "ok");
    await loadDashboard();
    if (activeView === "weekly")  loadWeeklyReport();
    if (activeView === "monthly") loadMonthlyReport();
    showToast("Transaction saved ✓");
  } catch (e) {
    showSaveMsg(`✗ ${e.message}`, "err");
  } finally {
    submitting = false;
    btn.disabled = false;
    btn.textContent = "Save Transaction";
  }
});

function showSaveMsg(text, cls) {
  const el = document.getElementById("save-msg");
  el.textContent = text;
  el.className   = `save-msg ${cls}`;
  setTimeout(() => { el.textContent = ""; }, 4000);
}

// ─────────────────────────────────────────────────────────────
// DAILY LEDGER
// ─────────────────────────────────────────────────────────────
async function loadDailyLedger() {
  const container = document.getElementById("daily-container");
  container.innerHTML = '<div class="spinner"></div>';

  try {
    const days = await apiFetch("/api/reports/daily");
    if (!days || days.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🧾</div>
          <div class="empty-title">No transactions yet</div>
          <div class="empty-sub">Add your first recharge or expense above</div>
        </div>`;
      return;
    }

    container.innerHTML = days.map(day => renderDayBlock(day)).join("");

    // Bind delete buttons
    container.querySelectorAll(".txn-delete").forEach(btn => {
      btn.addEventListener("click", () => deleteTransaction(btn.dataset.id));
    });
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">Error loading ledger</div><div class="empty-sub">${e.message}</div></div>`;
  }
}

function renderDayBlock(day) {
  const txnRows = day.transactions.map(t => `
    <tr>
      <td>${t.time_ist}</td>
      <td>${escHtml(t.name)}</td>
      <td class="right ${t.type === 'recharge' ? 'amount-received' : 'amount-dash'}">${t.type === 'recharge' ? fmt(t.amount) : '—'}</td>
      <td class="right ${t.type === 'expense'  ? 'amount-spent'    : 'amount-dash'}">${t.type === 'expense'  ? fmt(t.amount) : '—'}</td>
      <td class="right"><button class="txn-delete" data-id="${t.id}" title="Delete">✕</button></td>
    </tr>`).join("");

  return `
    <div class="day-block">
      <div class="day-header">
        <div class="day-label">${day.date_label}</div>
        <div class="day-opening">Opening: ${fmt(day.opening_balance)}</div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Item</th>
              <th class="right">Received</th>
              <th class="right">Spent</th>
              <th class="right"></th>
            </tr>
          </thead>
          <tbody>${txnRows || '<tr><td colspan="5" style="text-align:center;color:var(--text-dim);padding:16px">No transactions this day</td></tr>'}</tbody>
        </table>
        <table class="day-summary">
          <tbody>
            <tr><td>Opening Balance</td><td class="right">${fmt(day.opening_balance)}</td></tr>
            <tr><td>Amount Received</td><td class="right amount-received">${fmt(day.total_received)}</td></tr>
            <tr><td>Total Available</td><td class="right">${fmt(parseFloat(day.opening_balance) + parseFloat(day.total_received))}</td></tr>
            <tr><td>Amount Spent</td><td class="right amount-spent">${fmt(day.total_spent)}</td></tr>
            <tr><td><strong>END-OF-DAY BALANCE</strong></td><td class="right"><strong>${fmt(day.closing_balance)}</strong></td></tr>
          </tbody>
        </table>
      </div>
    </div>`;
}

async function deleteTransaction(id) {
  if (!confirm("Delete this transaction? Balances will be recalculated.")) return;
  try {
    await apiFetch(`/api/transactions/${id}`, { method: "DELETE" });
    showToast("Transaction deleted");
    await loadDashboard();
    if (activeView === "weekly")  loadWeeklyReport();
    if (activeView === "monthly") loadMonthlyReport();
  } catch (e) {
    showToast(`Error: ${e.message}`);
  }
}

// ─────────────────────────────────────────────────────────────
// WEEKLY REPORT
// ─────────────────────────────────────────────────────────────
let weekOffset = 0;  // 0 = current week, -1 = last week, etc.

async function loadWeeklyReport() {
  const container = document.getElementById("weekly-container");
  container.innerHTML = '<div class="spinner"></div>';

  // Calculate target week date
  const today = new Date();
  const targetDate = new Date(today);
  targetDate.setDate(today.getDate() + weekOffset * 7);
  const dateStr = toISODateLocal(targetDate);

  try {
    const r = await apiFetch(`/api/reports/weekly?week_start=${dateStr}`);
    updatePeriodLabel("weekly-period", formatWeekLabel(r.week_start, r.week_end, weekOffset));

    container.innerHTML = `
      <div class="report-card">
        <div class="table-wrap">
          <table>
            <thead><tr><th>Description</th><th class="right">Amount</th></tr></thead>
            <tbody>
              <tr><td>Opening Balance</td><td class="right">${fmt(r.opening_balance)}</td></tr>
              <tr><td>Total Received This Week</td><td class="right amount-received">${fmt(r.total_received)}</td></tr>
              <tr><td>Total Available</td><td class="right">${fmt(r.total_available)}</td></tr>
              <tr><td>Total Spent This Week</td><td class="right amount-spent">${fmt(r.total_spent)}</td></tr>
              <tr class="report-highlight"><td><strong>END-OF-WEEK BALANCE</strong></td><td class="right"><strong>${fmt(r.closing_balance)}</strong></td></tr>
            </tbody>
          </table>
        </div>
      </div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">${e.message}</div></div>`;
  }
}

document.getElementById("btn-week-prev").addEventListener("click", () => { weekOffset--; loadWeeklyReport(); });
document.getElementById("btn-week-next").addEventListener("click", () => { if (weekOffset < 0) { weekOffset++; loadWeeklyReport(); } });

function formatWeekLabel(startStr, endStr, offset) {
  const start = new Date(startStr + "T00:00:00");
  const end   = new Date(endStr   + "T00:00:00");
  const opts  = { day: "numeric", month: "short" };
  const label = `${start.toLocaleDateString("en-IN", opts)} – ${end.toLocaleDateString("en-IN", { ...opts, year: "numeric" })}`;
  return offset === 0 ? `This Week · ${label}` : label;
}

// ─────────────────────────────────────────────────────────────
// MONTHLY REPORT
// ─────────────────────────────────────────────────────────────
let monthOffset = 0;

async function loadMonthlyReport() {
  const container = document.getElementById("monthly-container");
  container.innerHTML = '<div class="spinner"></div>';

  const now = new Date();
  const target = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
  const year   = target.getFullYear();
  const month  = target.getMonth() + 1;

  try {
    const r = await apiFetch(`/api/reports/monthly?year=${year}&month=${month}`);
    updatePeriodLabel("monthly-period", monthOffset === 0 ? `Month to Date · ${r.month_label}` : r.month_label);

    container.innerHTML = `
      <div class="report-card">
        <div class="table-wrap">
          <table>
            <thead><tr><th>Description</th><th class="right">Amount</th></tr></thead>
            <tbody>
              <tr><td>Opening Balance</td><td class="right">${fmt(r.opening_balance)}</td></tr>
              <tr><td>Total Received This Month</td><td class="right amount-received">${fmt(r.total_received)}</td></tr>
              <tr><td>Total Available</td><td class="right">${fmt(r.total_available)}</td></tr>
              <tr><td>Total Spent This Month</td><td class="right amount-spent">${fmt(r.total_spent)}</td></tr>
              <tr class="report-highlight"><td><strong>END-OF-MONTH BALANCE</strong></td><td class="right"><strong>${fmt(r.closing_balance)}</strong></td></tr>
            </tbody>
          </table>
        </div>
      </div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">${e.message}</div></div>`;
  }
}

document.getElementById("btn-month-prev").addEventListener("click", () => { monthOffset--; loadMonthlyReport(); });
document.getElementById("btn-month-next").addEventListener("click", () => { if (monthOffset < 0) { monthOffset++; loadMonthlyReport(); } });

// ─────────────────────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────────────────────
function updatePeriodLabel(id, text) {
  document.getElementById(id).textContent = text;
}

function toISODateLocal(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function escHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2500);
}

// ─────────────────────────────────────────────────────────────
// SERVICE WORKER REGISTRATION
// ─────────────────────────────────────────────────────────────
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(e => console.warn("SW:", e));
  });
}

// ─────────────────────────────────────────────────────────────
// BOOT
// ─────────────────────────────────────────────────────────────
setType("expense");  // default to expense mode
initSupabase();
