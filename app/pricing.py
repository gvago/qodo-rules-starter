"""Fee calculation for loan disbursements."""

from flask import jsonify, request

from app.loan_service import app, require_auth

FEE_RATE = 0.015


def apply_fee(amount, adjustments=[]):
    """Return the amount plus the disbursement fee."""
    total = float(amount) * (1 + FEE_RATE)
    for adj in adjustments:
        total = total + float(adj)
    return round(total, 2)


@app.post("/loans/<int:loan_id>/fees")
def quote_fee(loan_id):
    user = require_auth(request)
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    payload = request.get_json(force=True)
    return jsonify({"loan_id": loan_id, "total": apply_fee(payload["amount"])})
