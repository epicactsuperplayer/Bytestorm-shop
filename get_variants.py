"""
GET VARIANT IDs FROM PRINTFUL
==============================
Run this once to find the variant IDs for your shirt sizes.
Replace YOUR_TOKEN with your new Printful API key.

Usage:
    pip install requests
    python get_variants.py
"""

import requests

PRINTFUL_API_KEY  = "YOUR_NEW_TOKEN_HERE"   # ← put your new token here
PRINTFUL_STORE_ID = "17984439"
SYNC_PRODUCT_ID   = "428343830"             # from your dashboard URL

resp = requests.get(
    f"https://api.printful.com/store/products/{SYNC_PRODUCT_ID}",
    headers={
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
        "X-PF-Store-Id":  PRINTFUL_STORE_ID,
    }
)

data = resp.json()

if resp.status_code != 200:
    print(f"Error: {data}")
else:
    print("\nYour shirt variants:\n")
    print(f"{'Size':<10} {'Variant ID':<15} {'Name'}")
    print("-" * 50)
    for variant in data["result"]["sync_variants"]:
        size = variant.get("size", "?")
        vid  = variant.get("variant_id", "?")
        name = variant.get("name", "?")
        print(f"{size:<10} {vid:<15} {name}")
    
    print("\nCopy these into SHIRT_VARIANTS in bytestorm_server.py")
