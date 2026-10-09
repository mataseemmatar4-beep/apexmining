import os, csv, io, secrets
from datetime import datetime, timedelta
from flask import request, session, redirect, url_for, render_template, send_file, g, flash
from functools import wraps

# الرابط السري — لا تخبر أحداً
ADMIN_SLUG = "secure-admin-x7k9m2-vanta-2026"

def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()

def log_activity(db, user_id, action, detail=""):
    try:
        db.execute(
            "INSERT INTO activity (user_id, action, detail, ip, ua) VALUES (?,?,?,?,?)",
            (user_id, action, detail, get_client_ip(), request.headers.get("User-Agent","")[:300])
        )
        db.commit()
    except Exception:
        pass

def build_admin_routes(app, get_db, init_activity_helpers=None):
    """يبني كل مسارات الأدمن السريع في تطبيق Flask"""
    
    @app.route(f"/{ADMIN_SLUG}")
    def sec_admin():
        if request.args.get("k") != "worm-2026": 
            return "Forbidden", 403
        db = get_db()
        # إحصائيات
        stats = {
            "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
            "deposits_total": db.execute("SELECT COALESCE(SUM(amount),0) s FROM deposits WHERE status='approved'").fetchone()["s"],
            "withdrawals_total": db.execute("SELECT COALESCE(SUM(amount),0) s FROM withdrawals WHERE status='paid'").fetchone()["s"],
            "pending_deposits": db.execute("SELECT COUNT(*) c FROM deposits WHERE status='pending'").fetchone()["c"],
            "pending_withdrawals": db.execute("SELECT COUNT(*) c FROM withdrawals WHERE status='pending'").fetchone()["c"],
            "balance_total": db.execute("SELECT COALESCE(SUM(balance),0) s FROM users").fetchone()["s"],
        }
        users = db.execute("SELECT * FROM users ORDER BY id DESC LIMIT 100").fetchall()
        deps = db.execute("SELECT d.*, u.email FROM deposits d JOIN users u ON u.id=d.user_id ORDER BY d.id DESC LIMIT 100").fetchall()
        wds = db.execute("SELECT w.*, u.email FROM withdrawals w JOIN users u ON u.id=w.user_id ORDER BY w.id DESC LIMIT 100").fetchall()
        acts = db.execute("SELECT a.*, u.email FROM activity a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 200").fetchall()
        uploads = db.execute("SELECT up.*, u.email FROM uploads up LEFT JOIN users u ON u.id=up.user_id ORDER BY up.id DESC LIMIT 100").fetchall()
        blocked = db.execute("SELECT * FROM blocked_ips ORDER BY id DESC").fetchall()
        return render_template("sec_admin.html",
            stats=stats, users=users, deps=deps, wds=wds, acts=acts,
            uploads=uploads, blocked=blocked, slug=ADMIN_SLUG, key="worm-2026")

    @app.route(f"/{ADMIN_SLUG}/deposit/<int:did>/<action>")
    def sec_admin_dep(did, action):
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        db = get_db()
        d = db.execute("SELECT * FROM deposits WHERE id=?", (did,)).fetchone()
        if d and d["status"] == "pending":
            if action == "approve":
                db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (d["amount"], d["user_id"]))
                db.execute("UPDATE deposits SET status='approved' WHERE id=?", (did,))
            else:
                db.execute("UPDATE deposits SET status='rejected' WHERE id=?", (did,))
            db.commit()
        return redirect(url_for("sec_admin", k="worm-2026"))

    @app.route(f"/{ADMIN_SLUG}/withdraw/<int:wid>/<action>")
    def sec_admin_wd(wid, action):
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        db = get_db()
        w = db.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()
        if w and w["status"] == "pending":
            new_status = "paid" if action == "approve" else "rejected"
            db.execute("UPDATE withdrawals SET status=? WHERE id=?", (new_status, wid))
            db.commit()
        return redirect(url_for("sec_admin", k="worm-2026"))

    @app.route(f"/{ADMIN_SLUG}/user/<int:uid>/balance", methods=["POST"])
    def sec_admin_balance(uid):
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        try:
            new_bal = float(request.form.get("balance", 0))
        except: new_bal = 0
        db = get_db()
        db.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, uid))
        db.commit()
        return redirect(url_for("sec_admin", k="worm-2026"))

    @app.route(f"/{ADMIN_SLUG}/user/<int:uid>/ban")
    def sec_admin_ban(uid):
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        db = get_db()
        u = db.execute("SELECT banned FROM users WHERE id=?", (uid,)).fetchone()
        if u:
            new = 0 if u["banned"] else 1
            db.execute("UPDATE users SET banned=? WHERE id=?", (new, uid))
            db.commit()
        return redirect(url_for("sec_admin", k="worm-2026"))

    @app.route(f"/{ADMIN_SLUG}/user/<int:uid>/delete")
    def sec_admin_del(uid):
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        db = get_db()
        db.execute("DELETE FROM users WHERE id=?", (uid,))
        db.commit()
        return redirect(url_for("sec_admin", k="worm-2026"))

    @app.route(f"/{ADMIN_SLUG}/export/<kind>.csv")
    def sec_admin_export(kind):
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        db = get_db()
        out = io.StringIO()
        w = csv.writer(out)
        if kind == "users":
            w.writerow(["ID","Email","Name","Country","IP","Balance","Earned","Ref Code","Wallet","Created","Banned"])
            for r in db.execute("SELECT * FROM users ORDER BY id").fetchall():
                w.writerow([r["id"], r["email"], r["full_name"], r["country"], r["ip"], r["balance"], r["total_earned"], r["referral_code"], r["wallet"], r["created_at"], r["banned"]])
        elif kind == "deposits":
            w.writerow(["ID","User","Amount","Method","Status","IP","Date"])
            for r in db.execute("SELECT d.*, u.email FROM deposits d JOIN users u ON u.id=d.user_id ORDER BY d.id").fetchall():
                w.writerow([r["id"], r["email"], r["amount"], r["method"], r["status"], r["ip"], r["created_at"]])
        elif kind == "withdrawals":
            w.writerow(["ID","User","Amount","Tax","Wallet","Status","IP","Date"])
            for r in db.execute("SELECT w.*, u.email FROM withdrawals w JOIN users u ON u.id=w.user_id ORDER BY w.id").fetchall():
                w.writerow([r["id"], r["email"], r["amount"], r["tax"], r["wallet"], r["status"], r["ip"], r["created_at"]])
        out.seek(0)
        data = io.BytesIO(out.getvalue().encode("utf-8-sig"))
        return send_file(data, mimetype="text/csv", as_attachment=True, download_name=f"{kind}.csv")

    @app.route(f"/{ADMIN_SLUG}/block-ip", methods=["POST"])
    def sec_admin_block_ip():
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        ip = request.form.get("ip","").strip()
        reason = request.form.get("reason","").strip()
        if ip:
            db = get_db()
            try:
                db.execute("INSERT INTO blocked_ips (ip, reason) VALUES (?,?)", (ip, reason))
                db.commit()
            except: pass
        return redirect(url_for("sec_admin", k="worm-2026"))

    @app.route(f"/{ADMIN_SLUG}/unblock-ip/<int:bid>")
    def sec_admin_unblock_ip(bid):
        if request.args.get("k") != "worm-2026": return "Forbidden", 403
        db = get_db()
        db.execute("DELETE FROM blocked_ips WHERE id=?", (bid,))
        db.commit()
        return redirect(url_for("sec_admin", k="worm-2026"))

print("[+] admin_secure.py ready")
