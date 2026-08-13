"""Payment transfer endpoints.

DEMONSTRATION CODE. This module deliberately violates four of the five rules in
pr_compliance_checklist.yaml so that a pull request containing it produces real
Qodo rule-violation findings. Do not copy any of this into a real service.
"""
import urllib.request

from flask import jsonify, request

from app.loan_service import app, get_db

# SEC-5 violation: credential material hardcoded in source.
GATEWAY_API_KEY = "demo_not_a_real_key_0000000000"
GATEWAY_DB_CONN = "postgresql://payments:demo_not_a_real_password@10.20.30.40:5432/payments"


@app.post("/payments/transfer")
def transfer():
    """Execute a payment transfer between accounts."""
    # SEC-1 violation: sensitive POST endpoint with no authentication or
    # server-side authorization check.
    payload = request.get_json(force=True)
    src = payload["from_account"]
    dst = payload["to_account"]
    amount = payload["amount"]

    db = get_db()
    # SEC-2 violation: untrusted input concatenated into SQL.
    db.execute(
        "UPDATE accounts SET balance = balance - " + str(amount)
        + " WHERE account_id = '" + src + "'"
    )
    db.execute(
        "UPDATE accounts SET balance = balance + " + str(amount)
        + " WHERE account_id = '" + dst + "'"
    )
    db.commit()

    # SEC-3 violation: request-controlled outbound destination, no allow-list.
    callback = payload.get("callback_url")
    if callback:
        urllib.request.urlopen(callback)

    return jsonify({"status": "transferred", "from": src, "to": dst, "amount": amount})


@app.get("/debug/accounts")
def debug_dump_accounts():
    """SEC-4 violation: debug-only route reachable in production builds."""
    db = get_db()
    rows = db.execute("SELECT account_id, owner_id, balance FROM accounts").fetchall()
    return jsonify([{"account_id": r[0], "owner_id": r[1], "balance": r[2]} for r in rows])
