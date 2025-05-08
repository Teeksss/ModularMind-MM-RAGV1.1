"""
Vektör deposu test modülü.
"""

import unittest
import tempfile
import os
import shutil

from ModularMind.API.services.retrieval.models import (
    VectorStore, 
    VectorStoreConfig, 
    Document, 
    DocumentChunk, 
    DocumentMetadata,
    IndexType
)

class TestVectorStore(unittest.TestCase):
    """Vektör deposu test sınıfı."""
    
    def setUp(self):
        """Test ortamını hazırla."""
        # Geçici dizin oluştur
        self.temp_dir = tempfile.mkdtemp()
        
        # Vektör deposu yapılandırması oluştur
        self.config = VectorStoreConfig(
            index_type=IndexType.HNSW,
            dimensions=4,  # Test için küçük boyut
            metric="cosine",
            storage_path=self.temp_dir
        )
        
        # Vektör deposu oluştur
        self.vector_store = VectorStore(self.config)
        
        # Test belgeleri oluştur
        self.create_test_documents()
    
    def tearDown(self):
        """Test ortamını temizle."""
        # Geçici dizini kaldır
        shutil.rmtree(self.temp_dir)
    
    def create_test_documents(self):
        """Test belgeleri oluştur."""
        # Belge 1
        metadata1 = DocumentMetadata(
            title="Test Document 1",
            source="test",
            source_type="text"
        )
        
        chunk1_1 = DocumentChunk(
            id="chunk1_1",
            text="This is the first chunk of document 1.",
            document_id="doc1",
            metadata=metadata1,
            embedding=[0.1, 0.2, 0.3, 0.4]
        )
        
        chunk1_2 = DocumentChunk(
            id="chunk1_2",
            text="This is the second chunk of document 1.",
            document_id="doc1",
            metadata=metadata1,
            embedding=[0.2, 0.3, 0.4, 0.5]
        )
        
        self.document1 = Document(
            id="doc1",
            text="This is test document 1.",
            metadata=metadata1,
            chunks=[chunk1_1, chunk1_2]
        )
        
        # Belge 2
        metadata2 = DocumentMetadata(
            title="Test Document 2",
            source="test",
            source_type="text"
        )
        
        chunk2_1 = DocumentChunk(
            id="chunk2_1",
            text="This is the first chunk of document 2.",
            document_id="doc2",
            metadata=metadata2,
            embedding=[0.5, 0.6, 0.7, 0.8]
        )
        
        chunk2_2 = DocumentChunk(
            id="chunk2_2",
            text="This is the second chunk of document 2.",
            document_id="doc2",
            metadata=metadata2,
            embedding=[0.6, 0.7, 0.8, 0.9]
        )
        
        self.document2 = Document(
            id="doc2",
            text="This is test document 2.",
            metadata=metadata2,
            chunks=[chunk2_1, chunk2_2]
        )
    
    def test_add_document(self):
        """Belge ekleme testleri."""
        # Belge ekle
        self.assertTrue(self.vector_store.add_document(self.document1))
        
        # Belgenin eklendiğini doğrula
        self.assertEqual(len(self.vector_store.documents), 1)
        self.assertEqual(len(self.vector_store.document_chunks), 2)
        
        # Belgeyi getir
        doc = self.vector_store.get_document("doc1")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.id, "doc1")
        
        # Chunk'ı getir
        chunk = self.vector_store.get_document_chunk("chunk1_1")
        self.assertIsNotNone(chunk)
        self.assertEqual(chunk.id, "chunk1_1")
    
    def test_add_documents(self):
        """Çoklu belge ekleme testleri."""
        # Belgeleri ekle
        self.assertTrue(self.vector_store.add_documents([self.document1, self.document2]))
        
        # Belgelerin eklendiğini doğrula
        self.assertEqual(len(self.vector_store.documents), 2)
        self.assertEqual(len(self.vector_store.document_chunks), 4)
    
    def test_delete_document(self):
        """Belge silme testleri."""
        # Belgeleri ekle
        self.vector_store.add_documents([self.document1, self.document2])
        
        # Belge sil
        self.assertTrue(self.vector_store.delete_document("doc1"))
        
        # Belgenin silindiğini doğrula
        self.assertEqual(len(self.vector_store.documents), 1)
        self.assertEqual(len(self.vector_store.document_chunks), 2)
        
        # Silinmeyen belgenin durumunu doğrula
        self.assertIsNone(self.vector_store.get_document("doc1"))
        self.assertIsNotNone(self.vector_store.get_document("doc2"))
    
    def test_build_index(self):
        """İndeks oluşturma testleri."""
        # Belgeleri ekle
        self.vector_store.add_documents([self.document1, self.document2])
        
        # İndeks oluştur (hnswlib yüklü ise çalışır)
        try:
            import hnswlib
            self.assertTrue(self.vector_store.build_index())
            self.assertIsNotNone(self.vector_store.index)
        except ImportError:
            print("hnswlib yüklü değil, indeks testi atlanıyor")
    
    def test_save_load(self):
        """Kaydetme ve yükleme testleri."""
        # Belgeleri ekle
        self.vector_store.add_documents([self.document1, self.document2])
        
        # Kaydet
        self.assertTrue(self.vector_store.save())
        
        # Yeni vektör deposu oluştur
        new_store = VectorStore(self.config)
        
        # Yükle
        self.assertTrue(new_store.load())
        
        # Yüklenen verileri doğrula
        self.assertEqual(len(new_store.documents), 2)
        self.assertEqual(len(new_store.document_chunks), 4)
        
        # Belge içeriğini doğrula
        doc = new_store.get_document("doc1")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.text, "This is test document 1.")

if __name__ == "__main__":
    unittest.main()