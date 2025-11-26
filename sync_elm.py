import imaplib
import email
import json

from dotenv import load_dotenv
import os
from email import policy
from email.parser import BytesParser
from email.header import decode_header, make_header
import shutil

load_dotenv()

IMAP_SERVER = "127.0.0.1"  # pour Proton Mail Bridge : 127.0.0.1
IMAP_PORT = 1143           # pour Bridge en mode non chiffré
USERNAME = os.getenv("USR")
PASSWORD = os.getenv("PWD")
EML_FOLDER = os.getenv("EML_FOLDER")
EML_ARCHIVE = os.getenv("EML_ARCHIVE")
EML_ERROR = os.getenv("EML_ERROR")

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

    '''
    for uid in uids:
        result, msg_data = mail.fetch(uid, "(RFC822)")
        if result != "OK":
            continue

        msg = email.message_from_bytes(msg_data[0][1])
        msgid = msg.get("Message-ID")

        if msgid:
            message_ids.add(msgid.strip())

    
    '''
    # batch size: fetch 500 at a time (tune as you like)
    batch_size = 2500
    batch_id = 1
    for i in range(0, len(uids), batch_size):
        print(f"Fetching batch {batch_id}/{int(round(len(uids)/batch_size,0))}")
        batch_id = batch_id + 1
        batch = b",".join(uids[i:i + batch_size])

        # fetch only the header, not whole mail
        result, msg_data = mail.fetch(
            batch,
            "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])"
        )

        if result != "OK":
            continue

        # parse each header block
        for part in msg_data:
            if isinstance(part, tuple):
                header = part[1]
                try:
                    msg = email.message_from_bytes(header)
                    msgid = msg.get("Message-ID")
                    if msgid:
                        message_ids.add(msgid.strip())
                except Exception as e:
                    print(e)

    print(f"[+] Existing messages: {len(message_ids)}")
    return message_ids

def import_eml_if_new(mail, existing_ids,restart=-1):
    cnt_mail = 0
    nb_file = len(os.listdir(EML_FOLDER))
    print(f"{nb_file} mails found")
    list = os.listdir(EML_FOLDER)
    #list.reverse()
    for filename in list:
        try:
            error = False
            cnt_mail = cnt_mail + 1
            if cnt_mail % 1000 == 0:
                print(f"Already checked {cnt_mail}/{nb_file} e-mails")
            if restart > -1 and restart > cnt_mail:
                continue

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
                #try:
                #    print(f"[=] SKIP (already exists): {filename}")
                #except:
                #    print(f"[=] SKIP (already exists): error on filename code")
                dst = os.path.join(EML_ARCHIVE, filename)
                shutil.move(filepath, dst)
                continue

            #try:
            #    print(f"[+] Importing: {filename}")
            #except:
            #    print(f"[+] Importing: error on filename code")

            # Upload (APPEND) to Proton Mail
            try:
                raw = fix_eml_headers(raw)
            except:
                print("error fixing header")
            result = mail.append(MAILBOX, r"(\Seen)", None, raw)
            if result[0] == "OK":
                try:
                    print(f"[{round(cnt_mail/nb_file*100,1)}%]-[{cnt_mail}] Imported: {filename}")
                except:
                    print(f"[✓] Imported: error on filename code")
                existing_ids.add(msgid)
            else:
                error=True
                try:
                    print(f"[!] FAILED to import: {filename} — {result}")
                except:
                    print(f"[!] FAILED to import: error on filename code")
            if error:
                dst = os.path.join(EML_ERROR, filename)
                shutil.move(filepath, dst)
                print(f"file move to {dst}")

        except Exception as e:
            print(f"[!] Failed to import: {e}")
            dst = os.path.join(EML_ERROR, filename)
            shutil.move(filepath, dst)
            print(f"file move to {dst}")
            mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
            mail.login(USERNAME, PASSWORD)

def main():


    mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
    mail.login(USERNAME, PASSWORD)

    relaod = True

    if not relaod and os.path.exists("existing_ids.json"):
        existing_ids = set(json.load(open("existing_ids.json")))
    else:
        existing_ids = get_existing_message_ids(mail)
        json.dump(list(existing_ids), open("existing_ids.json", "w"))

    import_eml_if_new(mail, existing_ids)

    print("[✓] Done.")
if __name__ == "__main__":
    main()
