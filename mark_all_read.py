import imaplib
import email
from dotenv import load_dotenv
import os
load_dotenv()

IMAP_SERVER = "127.0.0.1"  # pour Proton Mail Bridge : 127.0.0.1
IMAP_PORT = 1143           # pour Bridge en mode non chiffré
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
EML_FOLDER = os.getenv("EML_FOLDER")

#MAILBOX = '"All Mail"'          # boîte à nettoyer
MAILBOX="INBOX"


def main():
    mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
    mail.login(USERNAME, PASSWORD)
    # Sélectionner inbox (ou autre dossier)
    imap.select(MAILBOX)
    
    # Rechercher tous les messages NON lus
    status, messages = imap.search(None, 'UNSEEN')
    
    if status != "OK":
        print("Erreur lors de la recherche.")
        exit()
    
    msg_ids = messages[0].split()
    
    print(f"Messages non lus : {len(msg_ids)}")
    
    # Marquer chaque message comme lu
    for msg_id in msg_ids:
        imap.store(msg_id, '+FLAGS', '\\Seen')
    
    print("✔️ Tous les messages ont été marqués comme lus.")
    
    # Fermer la session
    imap.close()
    imap.logout()
    


if __name__ == "__main__":
    main()
