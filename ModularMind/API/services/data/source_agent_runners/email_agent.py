"""
E-posta ajan çalıştırıcısı.
"""

import logging
import uuid
import time
import email
from typing import Dict, Any
from email.header import decode_header

from ModularMind.API.services.retrieval.models import Document

logger = logging.getLogger(__name__)

def run_email_reader(config, result):
    """
    E-posta okuyucu ajanını çalıştırır.
    
    Args:
        config: Ajan yapılandırması
        result: Sonuç nesnesi
    """
    # E-posta protokol tipini belirle
    protocol = config.options.get("protocol", "imap").lower()
    
    if protocol == "imap":
        _run_imap_reader(config, result)
    elif protocol == "pop3":
        _run_pop3_reader(config, result)
    else:
        raise ValueError(f"Desteklenmeyen e-posta protokolü: {protocol}")

def _run_imap_reader(config, result):
    """IMAP e-posta protokolü için okuyucu."""
    try:
        import imaplib
        
        # Bağlantı bilgileri
        host = config.options.get("host", "")
        port = config.options.get("port", 993)
        use_ssl = config.options.get("use_ssl", True)
        username = config.credentials.get("username", "")
        password = config.credentials.get("password", "")
        folder = config.options.get("folder", "INBOX")
        max_emails = config.options.get("max_emails", config.max_items)
        
        if not host or not username or not password:
            raise ValueError("IMAP için host, username ve password gereklidir")
        
        # IMAP bağlantısını kur
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
        
        # Giriş yap
        mail.login(username, password)
        
        # Klasörü seç
        mail.select(folder)
        
        # Son tarihten beri olan e-postaları ara
        search_criteria = "ALL"
        if config.last_run:
            # Son çalışma zamanından beri olanları ara
            date_str = time.strftime("%d-%b-%Y", time.localtime(config.last_run))
            search_criteria = f'(SINCE "{date_str}")'
        
        # Arama yap
        status, message_ids = mail.search(None, search_criteria)
        
        if status != "OK":
            raise Exception(f"E-posta arama hatası: {status}")
        
        # Mesaj ID'lerini al
        id_list = message_ids[0].split()
        
        # Limit uygula
        id_list = id_list[-max_emails:] if len(id_list) > max_emails else id_list
        
        # Belgeleri oluştur
        documents = []
        
        for msg_id in id_list:
            # Mesajı getir
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            
            if status != "OK":
                logger.warning(f"Mesaj getirme hatası: {status}")
                continue
            
            # Mesaj içeriğini parse et
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Başlığı decode et
            subject = ""
            subject_header = msg.get("Subject", "")
            if subject_header:
                decoded_chunks = decode_header(subject_header)
                subject = " ".join(
                    str(chunk[0], chunk[1] or "utf-8") if isinstance(chunk[0], bytes) else str(chunk[0])
                    for chunk in decoded_chunks
                )
            
            # Göndereni decode et
            from_addr = ""
            from_header = msg.get("From", "")
            if from_header:
                decoded_chunks = decode_header(from_header)
                from_addr = " ".join(
                    str(chunk[0], chunk[1] or "utf-8") if isinstance(chunk[0], bytes) else str(chunk[0])
                    for chunk in decoded_chunks
                )
            
            # Tarih
            date_str = msg.get("Date", "")
            
            # Mesaj içeriğini al
            body = ""
            
            if msg.is_multipart():
                # Çok parçalı mesaj
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Metin içeriğini al
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = part.get_content_charset() or "utf-8"
                        payload = part.get_payload(decode=True)
                        try:
                            body += payload.decode(charset)
                        except Exception:
                            body += payload.decode("utf-8", errors="replace")
            else:
                # Tek parçalı mesaj
                charset = msg.get_content_charset() or "utf-8"
                payload = msg.get_payload(decode=True)
                try:
                    body = payload.decode(charset)
                except Exception:
                    body = payload.decode("utf-8", errors="replace")
            
            # Metin oluştur
            text = f"From: {from_addr}\nSubject: {subject}\nDate: {date_str}\n\n{body}"
            
            # Metadata
            metadata = {
                "source": f"email:{username}",
                "source_type": "email",
                "from": from_addr,
                "subject": subject,
                "date": date_str,
                "protocol": "imap",
                "folder": folder
            }
            
            # Belge oluştur
            doc_id = f"email_{uuid.uuid4().hex}"
            document = Document(
                id=doc_id,
                text=text,
                metadata=metadata
            )
            
            # Belgeyi listeye ekle
            documents.append(document)
        
        # Sonucu güncelle
        result.documents = documents
        result.metadata["email_count"] = len(documents)
        
        # Bağlantıyı kapat
        mail.close()
        mail.logout()
        
    except ImportError:
        raise ImportError("E-posta okuyucu için imaplib kütüphanesi gereklidir")

def _run_pop3_reader(config, result):
    """POP3 e-posta protokolü için okuyucu."""
    try:
        import poplib
        
        # Bağlantı bilgileri
        host = config.options.get("host", "")
        port = config.options.get("port", 995)
        use_ssl = config.options.get("use_ssl", True)
        username = config.credentials.get("username", "")
        password = config.credentials.get("password", "")
        max_emails = config.options.get("max_emails", config.max_items)
        
        if not host or not username or not password:
            raise ValueError("POP3 için host, username ve password gereklidir")
        
        # POP3 bağlantısını kur
        if use_ssl:
            mail = poplib.POP3_SSL(host, port)
        else:
            mail = poplib.POP3(host, port)
        
        # Giriş yap
        mail.user(username)
        mail.pass_(password)
        
        # Posta kutusunun durumunu al
        msg_count, _ = mail.stat()
        
        # Limit uygula
        start_msg = max(1, msg_count - max_emails + 1)
        
        # Belgeleri oluştur
        documents = []
        
        for i in range(start_msg, msg_count + 1):
            # Mesajı getir
            response, lines, _ = mail.retr(i)
            
            if response != b"+OK":
                logger.warning(f"Mesaj getirme hatası: {response}")
                continue
            
            # Mesaj içeriğini parse et
            raw_email = b"\r\n".join(lines)
            msg = email.message_from_bytes(raw_email)
            
            # Başlığı decode et
            subject = ""
            subject_header = msg.get("Subject", "")
            if subject_header:
                decoded_chunks = decode_header(subject_header)
                subject = " ".join(
                    str(chunk[0], chunk[1] or "utf-8") if isinstance(chunk[0], bytes) else str(chunk[0])
                    for chunk in decoded_chunks
                )
            
            # Göndereni decode et
            from_addr = ""
            from_header = msg.get("From", "")
            if from_header:
                decoded_chunks = decode_header(from_header)
                from_addr = " ".join(
                    str(chunk[0], chunk[1] or "utf-8") if isinstance(chunk[0], bytes) else str(chunk[0])
                    for chunk in decoded_chunks
                )
            
            # Tarih
            date_str = msg.get("Date", "")
            
            # Mesaj içeriğini al
            body = ""
            
            if msg.is_multipart():
                # Çok parçalı mesaj
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Metin içeriğini al
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = part.get_content_charset() or "utf-8"
                        payload = part.get_payload(decode=True)
                        try:
                            body += payload.decode(charset)
                        except Exception:
                            body += payload.decode("utf-8", errors="replace")
            else:
                # Tek parçalı mesaj
                charset = msg.get_content_charset() or "utf-8"
                payload = msg.get_payload(decode=True)
                try:
                    body = payload.decode(charset)
                except Exception:
                    body = payload.decode("utf-8", errors="replace")
            
            # Metin oluştur
            text = f"From: {from_addr}\nSubject: {subject}\nDate: {date_str}\n\n{body}"
            
            # Metadata
            metadata = {
                "source": f"email:{username}",
                "source_type": "email",
                "from": from_addr,
                "subject": subject,
                "date": date_str,
                "protocol": "pop3"
            }
            
            # Belge oluştur
            doc_id = f"email_{uuid.uuid4().hex}"
            document = Document(
                id=doc_id,
                text=text,
                metadata=metadata
            )
            
            # Belgeyi listeye ekle
            documents.append(document)
        
        # Sonucu güncelle
        result.documents = documents
        result.metadata["email_count"] = len(documents)
        
        # Bağlantıyı kapat
        mail.quit()
        
    except ImportError:
        raise ImportError("E-posta okuyucu için poplib kütüphanesi gereklidir")