import imaplib
import email
import re
from email import policy
import datetime
import os

# -------------------------
# CONFIG
# -------------------------
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT   = 993

EMAIL_USER = "alexwtz@gmail.com"
EMAIL_PASS = "hekbudmzlwlkyjus"  # Gmail → Security → App Passwords

#SAVE_FOLDER = "exported_eml"
SAVE_FOLDER="d:/mail/gmail_alexwtz_20251119-2108/gmail_alexwtz2/"

# -------------------------
# PREPARE EXPORT FOLDER
# -------------------------
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

# -------------------------
# DATE RANGE
# -------------------------
start_date = datetime.datetime(2025, 8, 23)
end_date   = datetime.datetime.now()

start_str = start_date.strftime("%d-%b-%Y")
end_str   = end_date.strftime("%d-%b-%Y")

# -------------------------
# CONNECT TO GMAIL IMAP
# -------------------------
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
mail.login(EMAIL_USER, EMAIL_PASS)
mail.select("INBOX")

# Gmail IMAP date search format:
# SINCE dd-Mon-yyyy  BEFORE dd-Mon-yyyy
query = f'(SINCE "{start_str}" BEFORE "{end_str}")'
print("IMAP search query → ", query)

result, data = mail.search(None, query)

if result != "OK":
    print("Search failed.")
    exit()

email_ids = data[0].split()
print(f"Found {len(email_ids)} emails.")

import unicodedata

def safe_filename(name):
    if not name:
        return "email"

    # Normalize unicode (removes weird invisible chars)
    name = unicodedata.normalize("NFKD", name)

    # Replace ALL whitespace variants with normal spaces
    name = re.sub(r'\s+', ' ', name)

    # Remove forbidden Windows characters
    name = re.sub(r'[\\\/:*?"<>|]', '_', name)

    # Remove non-breaking spaces explicitly
    name = name.replace('\xa0', ' ')

    # Trim spaces/dots
    name = name.strip(" .")

    # Safety limit
    return name[:150] or "email"

# -------------------------
# DOWNLOAD EACH EMAIL AS EML
# -------------------------
for num in email_ids:
    result, msg_data = mail.fetch(num, "(RFC822)")
    if result != "OK":
        print(f"Failed to fetch {num}")
        continue

    raw_email = msg_data[0][1]

    # Parse for safe filename
    msg = email.message_from_bytes(raw_email, policy=policy.default)
    subject = msg.get("Subject", "no_subject").replace("/", "_").replace("\\", "_")
    subject = safe_filename(subject)

    filename = f"{num.decode()}_{subject}.eml"
    path = os.path.join(SAVE_FOLDER, filename)

    with open(path, "wb") as f:
        f.write(raw_email)

    print("Saved:", path)

mail.close()
mail.logout()

print("\nDone! All mails exported.")