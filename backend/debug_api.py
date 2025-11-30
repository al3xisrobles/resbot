#!/usr/bin/env python3
"""Debug script to test Resy API calls"""

import json
import requests
from resy_bot.models import ResyConfig

# Load credentials
with open('credentials.json', 'r') as f:
    config_data = json.load(f)

config = ResyConfig(**config_data)

# Test 1: Check if auth headers are working
print("=" * 60)
print("Testing Resy API Connection")
print("=" * 60)

headers = {
    "Authorization": config.get_authorization(),
    "X-Resy-Auth-Token": config.token,
    "X-Resy-Universal-Auth": config.token,
    "Origin": "https://resy.com",
    "X-origin": "https://resy.com",
    "Referrer": "https://resy.com/",
    "Accept": "application/json, text/plain, */*",
}

print("\nHeaders:")
print(f"  Authorization: {config.get_authorization()[:30]}...")
print(f"  X-Resy-Auth-Token: {config.token[:30]}...")

# Test 2: Try the find endpoint with your parameters
print("\n" + "=" * 60)
print("Testing /4/find endpoint")
print("=" * 60)

params = {
    "lat": "0",
    "long": "0",
    "day": "2025-12-12",
    "party_size": 2,
    "venue_id": "443"
}

print(f"\nRequest: GET https://api.resy.com/4/find")
print(f"Params: {params}")

resp = requests.get(
    "https://api.resy.com/4/find",
    params=params,
    headers=headers
)

print(f"\nResponse Status: {resp.status_code}")
print(f"Response Headers: {dict(resp.headers)}")
print(f"Response Body: {resp.text[:500]}")

# Test 3: Try a different date (today + 7 days)
from datetime import date, timedelta
future_date = (date.today() + timedelta(days=7)).isoformat()

print("\n" + "=" * 60)
print(f"Testing with different date: {future_date}")
print("=" * 60)

params['day'] = future_date
resp2 = requests.get(
    "https://api.resy.com/4/find",
    params=params,
    headers=headers
)

print(f"Response Status: {resp2.status_code}")
print(f"Response Body: {resp2.text[:500]}")

# Test 4: Check if we can access a known venue (try without venue_id)
print("\n" + "=" * 60)
print("Testing without venue_id")
print("=" * 60)

params_no_venue = {
    "lat": "40.7128",  # NYC coordinates
    "long": "-74.0060",
    "day": future_date,
    "party_size": 2
}

resp3 = requests.get(
    "https://api.resy.com/4/find",
    params=params_no_venue,
    headers=headers
)

print(f"Response Status: {resp3.status_code}")
print(f"Response Body: {resp3.text[:500]}")
