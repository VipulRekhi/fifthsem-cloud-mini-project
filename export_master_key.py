"""
Helper script to safely read your local storage/keys/master.key
and print the 64-character hex string needed for the
ENCRYPTION_MASTER_KEY_HEX environment variable on Render.

Usage:
    python export_master_key.py
"""

from pathlib import Path

KEY_FILE = Path(__file__).resolve().parent / "storage" / "keys" / "master.key"

if not KEY_FILE.exists():
    print(f"Error: Key file '{KEY_FILE}' not found.")
    print("Run the application locally first or upload a file to generate a key.")
    exit(1)

with open(KEY_FILE, "rb") as f:
    key_bytes = f.read()

if len(key_bytes) != 32:
    print(f"Error: Expected 32-byte key, found {len(key_bytes)} bytes.")
    exit(1)

hex_key = key_bytes.hex()
print("=" * 70)
print("SUCCESS: 256-bit AES Master Key Exported")
print("=" * 70)
print(f"Key Hex (64 chars):\n{hex_key}")
print("=" * 70)
print("Add this to your Render Dashboard Environment Variables:")
print(f"Key:   ENCRYPTION_MASTER_KEY_HEX")
print(f"Value: {hex_key}")
print("=" * 70)
