import imaplib
import email
from dotenv import load_dotenv
import os

load_dotenv()

IMAP_SERVER = "127.0.0.1"  # pour Proton Mail Bridge : 127.0.0.1
IMAP_PORT = 1143           # pour Bridge en mode non chiffré
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")


#MAILBOX = '"All Mail"'          # boîte à nettoyer
MAILBOX="INBOX"

def main():
    mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
    mail.login(USERNAME, PASSWORD)

    #result, folders = mail.list()
    #for f in folders:
    #    print(f.decode())


    status, info = mail.select(MAILBOX, readonly=False)
    print("Select:", status, info)

    print("[+] Scanning mailbox for duplicates…")

    result, data = mail.search(None, "ALL")
    all_ids = data[0].split()

    message_ids_seen = {}
    message_seen = {}
    duplicates = []

    print(f"There are {len(all_ids)} mails")

    for msg_uid in all_ids:
        result, msg_data = mail.fetch(msg_uid, "(RFC822)")
        if result != "OK":
            continue
        msg_uid = msg_uid.decode()
        msg = email.message_from_bytes(msg_data[0][1])
        message_id = msg.get("Message-ID")

        sender = msg.get("From", "(no sender)")
        subject = msg.get("Subject", "(no subject)")
        date = msg.get("Date", "(no date)")

        header = (f"{sender} - {subject} - {date}")

        if header not in message_seen:
            message_seen[header] = [msg_uid]
        else:
            message_seen[header].append(msg_uid)

        if not message_id:
            continue

        if message_id not in message_ids_seen:
            message_ids_seen[message_id] = msg_uid
        else:
            duplicates.append(msg_uid)


    print(f"[+] Found {len(duplicates)} duplicates")

    # Delete duplicates
    for dup_uid in duplicates:
        #mail.store(dup_uid, "+FLAGS", "\\Deleted")
        result = mail.uid("STORE", dup_uid, "+FLAGS", "(\\Deleted)")
        print("STORE:", result)

    for x in message_seen.keys():
        if len(message_seen[x]) > 1:
            #keep first
            isFirst = True
            for y in message_seen[x]:
                if isFirst:
                    isFirst = False
                else:
                    #mail.store(y, "+FLAGS", "\\Deleted")
                    result = mail.uid("STORE", y, "+FLAGS", "(\\Deleted)")
                    print("STORE:", result)

            print(f"{len(message_seen[x])} msgs - {x}")
    res = mail.expunge()
    print("Expunge:", res)
    mail.logout()

    print("[+] Cleanup complete!")

if __name__ == "__main__":
    main()
