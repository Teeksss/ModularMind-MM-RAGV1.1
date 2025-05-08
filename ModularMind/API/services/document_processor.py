import os
import uuid
import logging
from typing import List, Dict, Any, Optional, BinaryIO, Tuple
from datetime import datetime
import tempfile
from pathlib import Path

import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import (
    PyPDFLoader, 
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    TextLoader,
    CSVLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader
)

from ModularMind.API.utils.text_utils import clean_text
from ModularMind.API.models.document import Document, DocumentChunk, DocumentMetadata

logger = logging.getLogger(__name__)

class UnsupportedFormatError(Exception):
    """Desteklenmeyen dosya formatı hatası."""
    pass

class DocumentProcessor:
    """
    Belge işleme servisi.
    Farklı formatlardaki belgeleri yükler, parçalar ve işler.
    """
    
    # Desteklenen dosya formatları
    SUPPORTED_FORMATS = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".html": "text/html",
        ".htm": "text/html"
    }
    
    def __init__(self):
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Belge işleme için geçici dizin
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Belge işleme için geçici dizin oluşturuldu: {self.temp_dir}")
    
    def is_supported_format(self, file_extension: str) -> bool:
        """
        Dosya formatının desteklenip desteklenmediğini kontrol eder.
        
        Args:
            file_extension: Dosya uzantısı
            
        Returns:
            bool: Format destekleniyorsa True
        """
        return file_extension.lower() in self.SUPPORTED_FORMATS
    
    def get_mime_type(self, file_extension: str) -> str:
        """
        Dosya uzantısına göre MIME türünü döndürür.
        
        Args:
            file_extension: Dosya uzantısı
            
        Returns:
            str: MIME türü
        """
        return self.SUPPORTED_FORMATS.get(file_extension.lower(), "application/octet-stream")
    
    def detect_language(self, text: str) -> str:
        """
        Metnin dilini tespit eder.
        Basit bir implementasyon, daha gelişmiş dil tespiti için
        langdetect veya fasttext gibi kütüphaneler kullanılabilir.
        
        Args:
            text: Tespit edilecek metin
            
        Returns:
            str: ISO 639-1 dil kodu (tr, en, vb.)
        """
        # Basit dil tespiti (ileride geliştirilebilir)
        # Türkçe'ye özgü karakterler
        tr_chars = set('çğıöşüÇĞİÖŞÜ')
        
        # Metin içindeki Türkçe karakter sayısı
        tr_count = sum(1 for c in text if c in tr_chars)
        
        # Basit bir eşik değeri ile karar ver
        if tr_count > len(text) * 0.01:
            return "tr"
        
        # Varsayılan olarak İngilizce
        return "en"
    
    def save_uploaded_file(self, file: BinaryIO, original_filename: str) -> str:
        """
        Yüklenen dosyayı geçici dizine kaydeder.
        
        Args:
            file: Dosya objesi
            original_filename: Orijinal dosya adı
            
        Returns:
            str: Kaydedilen dosyanın yolu
        """
        # Dosya uzantısını al
        _, ext = os.path.splitext(original_filename)
        
        # Benzersiz bir dosya adı oluştur
        temp_filename = f"{uuid.uuid4()}{ext}"
        temp_path = os.path.join(self.temp_dir, temp_filename)
        
        # Dosyayı kaydet
        with open(temp_path, "wb") as f:
            f.write(file.read())
        
        logger.debug(f"Dosya geçici dizine kaydedildi: {temp_path}")
        return temp_path
    
    def extract_text_from_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Dosyadan metin ve metadata çıkarır.
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Tuple[str, Dict[str, Any]]: (içerik, metadata)
            
        Raises:
            UnsupportedFormatError: Desteklenmeyen dosya formatı
        """
        _, ext = os.path.splitext(file_path)
        metadata = {}
        
        if not self.is_supported_format(ext):
            raise UnsupportedFormatError(f"Desteklenmeyen dosya formatı: {ext}")
        
        # PDF dosyaları
        if ext.lower() == ".pdf":
            return self._extract_from_pdf(file_path)
        
        # Word belgeleri
        elif ext.lower() in [".docx", ".doc"]:
            loader = UnstructuredWordDocumentLoader(file_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            return text, metadata
        
        # Excel dosyaları
        elif ext.lower() in [".xlsx", ".xls"]:
            loader = UnstructuredExcelLoader(file_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            return text, metadata
        
        # CSV dosyaları
        elif ext.lower() == ".csv":
            loader = CSVLoader(file_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            return text, metadata
        
        # Markdown dosyaları
        elif ext.lower() == ".md":
            loader = UnstructuredMarkdownLoader(file_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            return text, metadata
        
        # HTML dosyaları
        elif ext.lower() in [".html", ".htm"]:
            loader = UnstructuredHTMLLoader(file_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            return text, metadata
        
        # Metin dosyaları
        elif ext.lower() == ".txt":
            loader = TextLoader(file_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            return text, metadata
        
        # Hiçbiri değilse (buraya hiç ulaşılmamalı)
        raise UnsupportedFormatError(f"Desteklenmeyen dosya formatı: {ext}")
    
    def _extract_from_pdf(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        PDF'den metin ve metadata çıkarır.
        
        Args:
            file_path: PDF dosya yolu
            
        Returns:
            Tuple[str, Dict[str, Any]]: (içerik, metadata)
        """
        metadata = {}
        
        try:
            # PyPDF2 ile metadata çıkar
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                if pdf_reader.metadata:
                    info = pdf_reader.metadata
                    metadata = {
                        "title": info.get("/Title", ""),
                        "author": info.get("/Author", ""),
                        "creator": info.get("/Creator", ""),
                        "producer": info.get("/Producer", ""),
                        "subject": info.get("/Subject", ""),
                        "creation_date": info.get("/CreationDate", ""),
                        "total_pages": len(pdf_reader.pages)
                    }
            
            # LangChain loader ile metin çıkar
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"PDF işleme hatası: {str(e)}")
            # Hata durumunda boş metin dön, ama hata fırlatma
            return "", metadata
    
    def process_document(
        self, 
        file: BinaryIO, 
        filename: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Belgeyi işler ve bir Document nesnesi döndürür.
        
        Args:
            file: Dosya objesi
            filename: Dosya adı
            user_id: Kullanıcı ID
            metadata: Ek metadata
            
        Returns:
            Document: İşlenmiş belge
            
        Raises:
            UnsupportedFormatError: Desteklenmeyen dosya formatı
        """
        # Dosya uzantısını kontrol et
        _, ext = os.path.splitext(filename)
        if not self.is_supported_format(ext):
            raise UnsupportedFormatError(f"Desteklenmeyen dosya formatı: {ext}")
        
        # Dosyayı geçici dizine kaydet
        temp_path = self.save_uploaded_file(file, filename)
        
        try:
            # Metni ve metadata'yı çıkar
            content, file_metadata = self.extract_text_from_file(temp_path)
            
            # Temiz metin elde et
            clean_content = clean_text(content)
            
            # Metin boşsa uyarı ver
            if not clean_content.strip():
                logger.warning(f"Dosyadan metin çıkarılamadı: {filename}")
                clean_content = "Dosyadan metin çıkarılamadı."
            
            # Dil tespiti yap
            language = self.detect_language(clean_content)
            
            # Kullanıcı metadata'sını birleştir
            combined_metadata = {
                "filename": filename,
                "mime_type": self.get_mime_type(ext),
                "language": language,
                "file_size": os.path.getsize(temp_path),
                "uploaded_by": user_id,
                "upload_date": datetime.utcnow().isoformat(),
                **file_metadata
            }
            
            # Kullanıcının ek metadata'sını ekle
            if metadata:
                combined_metadata.update(metadata)
            
            # Belge nesnesini oluştur
            document_id = str(uuid.uuid4())
            document = Document(
                id=document_id,
                filename=filename,
                content=clean_content,
                metadata=DocumentMetadata(**combined_metadata),
                user_id=user_id,
                chunks=[]  # Parçalama işlemi sonrası doldurulacak
            )
            
            # Metni parçala
            self.split_document(document)
            
            logger.info(f"Belge başarıyla işlendi: {filename} ({document.id})")
            return document
            
        finally:
            # Geçici dosyayı temizle
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                logger.error(f"Geçici dosya temizleme hatası: {str(e)}")
    
    def split_document(self, document: Document) -> Document:
        """
        Belgeyi parçalara ayırır ve belge nesnesini günceller.
        
        Args:
            document: Belge nesnesi
            
        Returns:
            Document: Parçalanmış belge
        """
        # Metin boşsa parçalamaya gerek yok
        if not document.content.strip():
            return document
        
        # Metni parçala
        chunks = self.text_splitter.split_text(document.content)
        
        # Her bir parça için bir DocumentChunk nesnesi oluştur
        document_chunks = []
        
        for i, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                content=chunk_text,
                order=i,
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "language": document.metadata.language
                }
            )
            document_chunks.append(chunk)
        
        # Belge nesnesini güncelle
        document.chunks = document_chunks
        document.metadata.chunk_count = len(chunks)
        
        logger.debug(f"Belge {len(chunks)} parçaya ayrıldı: {document.id}")
        return document