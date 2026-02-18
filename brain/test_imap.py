"""Quick IMAP diagnostic — run from your terminal: python3 brain/test_imap.py"""

import imaplib
import ssl
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load credentials from .env
pw = ""
addr = ""
env_path = Path(__file__).parent / ".env"
for line in env_path.read_text().splitlines():
    if line.startswith("OUTBOT_EMAIL_ADDRESS="):
        addr = line.split("=", 1)[1].strip()
    elif line.startswith("OUTBOT_EMAIL_APP_PASSWORD="):
        pw = line.split("=", 1)[1].strip()

print(f"Address: {addr}")
print(f"Password: {pw[:4]}****")
print()

# Build SSL context with corporate proxy certs
print("0. Building SSL context with macOS system certs...")
ctx = ssl.create_default_context()
try:
    from brain.core.claude_client import _get_ca_certs
    ca_path = _get_ca_certs()
    if ca_path:
        ctx.load_verify_locations(ca_path)
        print(f"   Loaded CA bundle: {ca_path}")
    else:
        print("   No extra CA bundle (using system defaults)")
except Exception as e:
    print(f"   Warning: {e}")

print("1. Connecting to imap.gmail.com:993...")
try:
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=ctx)
    print(f"   OK — {conn.welcome.decode()[:70]}")
except Exception as e:
    print(f"   FAIL — {e}")
    print("   Check: Is port 993 blocked by your network/firewall?")
    print("   Trying without custom SSL context...")
    try:
        conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        print(f"   OK (default SSL) — {conn.welcome.decode()[:70]}")
    except Exception as e2:
        print(f"   Also failed: {e2}")
        sys.exit(1)

print("2. Logging in...")
try:
    conn.login(addr, pw)
    print("   OK — authenticated")
except imaplib.IMAP4.error as e:
    print(f"   FAIL — {e}")
    print("   Check: Is IMAP enabled in Gmail Settings > Forwarding and POP/IMAP?")
    print("   Check: Is the App Password correct?")
    sys.exit(1)

print("3. Selecting INBOX...")
try:
    status, data = conn.select("INBOX", readonly=True)
    print(f"   OK — {data[0].decode()} messages in inbox")
except Exception as e:
    print(f"   FAIL — {e}")
    sys.exit(1)

print("4. Searching for unread...")
try:
    status, data = conn.search(None, "UNSEEN")
    ids = data[0].split() if data[0] else []
    print(f"   OK — {len(ids)} unread")
except Exception as e:
    print(f"   FAIL — {e}")

conn.close()
conn.logout()
print("\nAll IMAP checks passed!")
