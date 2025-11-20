import imaplib
import email
from dotenv import load_dotenv
import os
from email import policy
from email.parser import BytesParser
from email.header import decode_header, make_header
load_dotenv()

IMAP_SERVER = "127.0.0.1"  # pour Proton Mail Bridge : 127.0.0.1
IMAP_PORT = 1143           # pour Bridge en mode non chiffré
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
EML_FOLDER = os.getenv("EML_FOLDER")

#MAILBOX = '"All Mail"'          # boîte à nettoyer
MAILBOX="INBOX"

from email import parser

def fix_eml_headers(raw_bytes):
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    if "Sender" in msg and len(msg["Sender"])>0:
        return raw_bytes

    # Validate From header
    from_header = msg.get("From")
    if not from_header:
        raise ValueError("Missing 'From' header — ProtonMail will reject this message")

    # Decode From header to extract real email address
    decoded_from = str(make_header(decode_header(from_header)))

    # Extract email inside <>
    import re
    match = re.search(r'<([^>]+)>', decoded_from)
    if match:
        email_addr = match.group(1).strip()
    else:
        # Something like "info@ssls.com" without braces
        email_addr = decoded_from.strip()

    # ----- FIX SENDER HEADER -----

    # Remove ALL existing Sender headers (even empty or invalid ones)
    while "Sender" in msg:
        del msg["Sender"]

    # Add a clean Sender header based on the email address
    msg["Sender"] = email_addr

    # Re-serialize message
    return msg.as_bytes()

def get_existing_message_ids(mail):
    print("[+] Fetching existing message IDs from Proton…")
    mail.select(MAILBOX)

    result, data = mail.search(None, "ALL")
    if result != "OK":
        print("Error searching mailbox")
        return set()

    uids = data[0].split()
    message_ids = set()

    for uid in uids:
        result, msg_data = mail.fetch(uid, "(RFC822)")
        if result != "OK":
            continue

        msg = email.message_from_bytes(msg_data[0][1])
        msgid = msg.get("Message-ID")

        if msgid:
            message_ids.add(msgid.strip())

    print(f"[+] Existing messages: {len(message_ids)}")
    return message_ids

def import_eml_if_new(mail, existing_ids):
    for filename in os.listdir(EML_FOLDER):
        if not filename.lower().endswith(".eml"):
            continue

        try:
            filepath = os.path.join(EML_FOLDER, filename)
            with open(filepath, "rb") as f:
                raw = f.read()
        except Exception as e:
            print(f"[!] Failed to read file - {e}")
            continue
        msg = email.message_from_bytes(raw)
        msgid = msg.get("Message-ID")

        if not msgid:
            print(f"[!] {filename} has NO Message-ID — skipping")
            continue

        msgid = msgid.strip()

        if msgid in existing_ids:
            print(f"[=] SKIP (already exists): {filename}")
            continue

        print(f"[+] Importing: {filename}")

        # Upload (APPEND) to Proton Mail
        try:
            raw = fix_eml_headers(raw)
            result = mail.append(MAILBOX, "", None, raw)
            if result[0] == "OK":
                print(f"[✓] Imported: {filename}")
                existing_ids.add(msgid)
            else:
                print(f"[!] FAILED to import: {filename} — {result}")
        except Exception as e:
            print(f"Error on imap - {e}")

def main():
    mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
    mail.login(USERNAME, PASSWORD)

    existing_ids = get_existing_message_ids(mail)
    import_eml_if_new(mail, existing_ids)

    mail.logout()
    print("[✓] Done.")


if __name__ == "__main__":
    main()
