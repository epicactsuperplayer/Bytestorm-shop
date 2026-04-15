"""
BYTESTORM — Vercel Serverless Function
File: api/paypal-webhook.py

Vercel automatically exposes this as:
https://your-site.vercel.app/api/paypal-webhook

Set that URL as your PayPal webhook endpoint.
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
import os


# ============================================================
# HELPERS
# ============================================================

def get_paypal_token():
    resp = requests.post(
        "https://api-m.paypal.com/v1/oauth2/token",
        auth=(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_SECRET"]),
        data={"grant_type": "client_credentials"},
    )
    return resp.json().get("access_token")


def verify_paypal_webhook(headers, raw_body):
    token = get_paypal_token()
    resp = requests.post(
        "https://api-m.paypal.com/v1/notifications/verify-webhook-signature",
        json={
            "auth_algo":         headers.get("paypal-auth-algo"),
            "cert_url":          headers.get("paypal-cert-url"),
            "transmission_id":   headers.get("paypal-transmission-id"),
            "transmission_sig":  headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id":        os.environ["PAYPAL_WEBHOOK_ID"],
            "webhook_event":     json.loads(raw_body),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json().get("verification_status") == "SUCCESS"


def create_printful_order(name, email, address, size):
    variants = {
        "S":   os.environ.get("VARIANT_S"),
        "M":   os.environ.get("VARIANT_M"),
        "L":   os.environ.get("VARIANT_L"),
        "XL":  os.environ.get("VARIANT_XL"),
        "2XL": os.environ.get("VARIANT_2XL"),
    }
    variant_id = variants.get(size.upper())
    if not variant_id:
        return {"error": f"Unknown size: {size}"}

    resp = requests.post(
        "https://api.printful.com/orders",
        json={
            "recipient": {
                "name":         name,
                "address1":     address.get("address_line_1", ""),
                "address2":     address.get("address_line_2", ""),
                "city":         address.get("admin_area_2", ""),
                "state_code":   address.get("admin_area_1", ""),
                "country_code": address.get("country_code", ""),
                "zip":          address.get("postal_code", ""),
                "email":        email,
            },
            "items": [{
                "variant_id": int(variant_id),
                "quantity":   1,
                "name":       "Bytestorm Esports T-Shirt",
            }],
            "confirm": True,
        },
        headers={
            "Authorization": f"Bearer {os.environ['PRINTFUL_API_KEY']}",
            "X-PF-Store-Id":  os.environ["PRINTFUL_STORE_ID"],
        },
    )
    return resp.json()


# ============================================================
# VERCEL HANDLER
# ============================================================

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length   = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)
        headers  = {k.lower(): v for k, v in self.headers.items()}

        try:
            event = json.loads(raw_body)
        except Exception:
            self._respond(400, {"error": "invalid json"})
            return

        # Only handle completed payments
        if event.get("event_type") != "PAYMENT.CAPTURE.COMPLETED":
            self._respond(200, {"status": "ignored"})
            return

        # Verify it's genuinely from PayPal
        if not verify_paypal_webhook(headers, raw_body):
            self._respond(400, {"error": "webhook verification failed"})
            return

        # Extract order details
        resource = event.get("resource", {})
        payer    = resource.get("payer", {})
        shipping = resource.get("shipping", {})

        name    = shipping.get("name", {}).get("full_name", "Customer")
        email   = payer.get("email_address", "")
        address = shipping.get("address", {})
        size    = resource.get("custom_id", "L")  # passed from your website

        result = create_printful_order(name, email, address, size)

        if "error" in result:
            self._respond(500, {"status": "printful_error", "detail": result})
        else:
            self._respond(200, {"status": "order_created", "printful_id": result.get("result", {}).get("id")})

    def do_GET(self):
        self._respond(200, {"status": "online", "service": "Bytestorm Auto-Fulfillment"})

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
