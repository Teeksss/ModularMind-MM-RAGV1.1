"""
Context yönetimi modülü.
Uzun dokümanlarla çalışma, dinamik context penceresi ve ilgililik optimizasyonlarını içerir.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
from datetime import datetime

from ModularMind.API.services.retrieval.models import Chunk
from ModularMind.API.services.llm_service import LLMService
from ModularMind.API.core.token_counter import count_tokens

logger = logging.getLogger(__name__)

@dataclass
class ContextConfig:
    """Context yönetimi yapılandırması."""
    max_tokens: int = 4000  # Maksimum context uzunluğu (token)
    trim_strategy: str = "relevance"  # relevance, document-relevance, hierarchical
    preserve_order: bool = False  # Chunk'ları skor yerine doküman sırasına göre al
    add_references: bool = True  # Context içine referans bilgisi ekle
    chunk_separator: str = "\n\n"  # Chunk'lar arası ayırıcı
    recursive_retriever: bool = False  # Recursive retrieval aktif mi
    title_boost: float = 1.2  # Başlık içeren chunk'lar için çarpan
    recency_boost: bool = False  # Güncel içerikleri boost et
    optimize_for_llm: bool = True  # LLM için optimize et

class ContextManager:
    """
    Context yönetimi işlemlerini gerçekleştiren sınıf.
    """
    
    def __init__(self, config: ContextConfig, llm_service: Optional[LLMService] = None):
        """
        Args:
            config: Context yönetimi yapılandırması
            llm_service: LLM servisi (isteğe bağlı)
        """
        self.config = config
        self.llm_service = llm_service
        
        # Başlık tespiti için regex kalıpları
        self.title_patterns = [
            r"^#+\s+.+$",  # Markdown başlıkları
            r"^Title:\s+.+$",  # Title: ile başlayan satırlar
            r"<h[1-6]>.*?</h[1-6]>",  # HTML başlık etiketleri
        ]
    
    def generate_context(self, chunks: List[Chunk], query: str = None) -> str:
        """
        Verilen chunk'lardan context oluşturur.
        
        Args:
            chunks: Context oluşturulacak chunk'lar
            query: İsteğe bağlı sorgu (ilgililik hesaplamaları için)
            
        Returns:
            str: Oluşturulan context
        """
        if not chunks:
            return ""
        
        # Chunk'ları ilk işleme
        processed_chunks = self._preprocess_chunks(chunks, query)
        
        # Sıralama
        if self.config.trim_strategy == "relevance":
            # Skor tabanlı sıralama
            processed_chunks.sort(key=lambda x: x["score"], reverse=True)
        elif self.config.trim_strategy == "document-relevance":
            # Önce doküman ilgililiğine göre sırala
            self._rerank_by_document_relevance(processed_chunks)
        elif self.config.trim_strategy == "hierarchical":
            # Hiyerarşik sıralama
            self._rerank_hierarchically(processed_chunks)
        
        # Doküman sırasını koru
        if self.config.preserve_order:
            processed_chunks = self._preserve_document_order(processed_chunks)
        
        # Context'e sığdırılacak maksimum token hesabı
        context_tokens = self._trim_to_max_tokens(processed_chunks)
        
        # Context metnini oluştur
        context = self._format_context(context_tokens)
        
        logger.info(f"Context oluşturuldu: {len(context_tokens)} chunk, {count_tokens(context)} token")
        return context
    
    def _preprocess_chunks(self, chunks: List[Chunk], query: str = None) -> List[Dict[str, Any]]:
        """
        Chunk'ları işler ve ek metadata ekler.
        
        Args:
            chunks: İşlenecek chunk'lar
            query: İsteğe bağlı sorgu
            
        Returns:
            List[Dict[str, Any]]: İşlenmiş chunk'lar
        """
        processed_chunks = []
        
        # Zaten aynı belgeden gelen chunk'ları grupla
        doc_id_map = {}
        
        for chunk in chunks:
            # Temel bilgileri çıkar
            doc_id = chunk.metadata.get("doc_id", "unknown")
            score = getattr(chunk, "score", 0.0)
            
            # Doküman bilgilerini güncelle
            if doc_id not in doc_id_map:
                doc_id_map[doc_id] = {
                    "chunks": [],
                    "total_score": 0.0,
                    "avg_score": 0.0,
                    "max_score": 0.0
                }
            
            doc_id_map[doc_id]["chunks"].append(chunk)
            doc_id_map[doc_id]["total_score"] += score
            doc_id_map[doc_id]["max_score"] = max(doc_id_map[doc_id]["max_score"], score)
        
        # Doküman ortalama skorlarını hesapla
        for doc_id, doc_data in doc_id_map.items():
            doc_data["avg_score"] = doc_data["total_score"] / len(doc_data["chunks"])
        
        # Her chunk için işleme
        for i, chunk in enumerate(chunks):
            # Temel bilgileri çıkar
            doc_id = chunk.metadata.get("doc_id", "unknown")
            source = chunk.metadata.get("source", "unknown")
            score = getattr(chunk, "score", 0.0)
            
            # Başlık içerip içermediğini kontrol et
            has_title = any(re.search(pattern, chunk.text, re.MULTILINE) for pattern in self.title_patterns)
            
            # Chunk'ın tokenleri
            chunk_tokens = count_tokens(chunk.text)
            
            # Başlık boost faktörünü uygula
            if has_title and self.config.title_boost > 1.0:
                adjusted_score = score * self.config.title_boost
            else:
                adjusted_score = score
            
            # Yenilik boost faktörünü uygula
            if self.config.recency_boost and "created_at" in chunk.metadata:
                # Yenilik faktörünü hesapla (0.0-1.0 arası)
                recency_factor = self._calculate_recency_factor(chunk.metadata.get("created_at"))
                # Skoru güncelle (maksimum %20 artış)
                adjusted_score = adjusted_score * (1.0 + (recency_factor * 0.2))
            
            # İşlenmiş chunk'ı ekle
            processed_chunks.append({
                "chunk": chunk,
                "doc_id": doc_id,
                "source": source,
                "score": adjusted_score,
                "orig_score": score,
                "has_title": has_title,
                "token_count": chunk_tokens,
                "doc_avg_score": doc_id_map[doc_id]["avg_score"],
                "doc_max_score": doc_id_map[doc_id]["max_score"],
                "index": i  # Orijinal sırayı koru
            })
        
        return processed_chunks
    
    def _rerank_by_document_relevance(self, processed_chunks: List[Dict[str, Any]]) -> None:
        """
        Chunk'ları doküman ilgililiğine göre yeniden sıralar.
        
        Args:
            processed_chunks: İşlenmiş chunk'lar
        """
        # Doküman ID'ye göre gruplandır
        doc_groups = {}
        for chunk_data in processed_chunks:
            doc_id = chunk_data["doc_id"]
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(chunk_data)
        
        # Her doküman için en yüksek skorlu chunk'ı bul
        doc_max_scores = {}
        for doc_id, chunks in doc_groups.items():
            doc_max_scores[doc_id] = max(c["score"] for c in chunks)
        
        # Dokümanları skorlarına göre sırala
        sorted_docs = sorted(doc_max_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Yeni sıralamayı oluştur
        reranked_chunks = []
        for doc_id, _ in sorted_docs:
            # Her dokümanın kendi chunk'larını skorlarına göre sırala
            doc_chunks = sorted(doc_groups[doc_id], key=lambda x: x["score"], reverse=True)
            reranked_chunks.extend(doc_chunks)
        
        # Orijinal listeyi güncelle
        processed_chunks.clear()
        processed_chunks.extend(reranked_chunks)
    
    def _rerank_hierarchically(self, processed_chunks: List[Dict[str, Any]]) -> None:
        """
        Chunk'ları hiyerarşik ilişkilerine göre yeniden sıralar.
        
        Args:
            processed_chunks: İşlenmiş chunk'lar
        """
        # Heading level bilgisine sahip chunk'ları tespit et
        has_hierarchy = any("heading_level" in c["chunk"].metadata for c in processed_chunks)
        
        if not has_hierarchy:
            # Hiyerarşik bilgi yoksa döküman ilgililiğini kullan
            self._rerank_by_document_relevance(processed_chunks)
            return
        
        # Doküman ID'ye göre gruplandır
        doc_groups = {}
        for chunk_data in processed_chunks:
            doc_id = chunk_data["doc_id"]
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(chunk_data)
        
        # Her doküman için en yüksek skorlu chunk'ı bul
        doc_max_scores = {}
        for doc_id, chunks in doc_groups.items():
            doc_max_scores[doc_id] = max(c["score"] for c in chunks)
        
        # Dokümanları skorlarına göre sırala
        sorted_docs = sorted(doc_max_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Yeni sıralamayı oluştur
        reranked_chunks = []
        for doc_id, _ in sorted_docs:
            doc_chunks = doc_groups[doc_id]
            
            # Heading level bilgisine göre, önce üst başlıklar
            doc_chunks_with_level = []
            doc_chunks_without_level = []
            
            for chunk_data in doc_chunks:
                heading_level = chunk_data["chunk"].metadata.get("heading_level")
                if heading_level is not None:
                    # Başlık seviyesini tut
                    chunk_data["heading_level"] = heading_level
                    doc_chunks_with_level.append(chunk_data)
                else:
                    doc_chunks_without_level.append(chunk_data)
            
            # Başlık seviyesine göre sırala (küçük seviye önce, aynı seviyede skor öncelikli)
            if doc_chunks_with_level:
                doc_chunks_with_level.sort(key=lambda x: (x["heading_level"], -x["score"]))
                reranked_chunks.extend(doc_chunks_with_level)
            
            # Sonra başlık seviyesi olmayan chunk'ları ekle
            if doc_chunks_without_level:
                # Başlık içeren chunk'ları öne al, sonra skora göre sırala
                doc_chunks_without_level.sort(key=lambda x: (-int(x["has_title"]), -x["score"]))
                reranked_chunks.extend(doc_chunks_without_level)
        
        # Orijinal listeyi güncelle
        processed_chunks.clear()
        processed_chunks.extend(reranked_chunks)
    
    def _preserve_document_order(self, processed_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk'ları doküman içindeki orijinal sıralarına göre düzenler.
        
        Args:
            processed_chunks: İşlenmiş chunk'lar
            
        Returns:
            List[Dict[str, Any]]: Doküman sırasına göre düzenlenmiş chunk'lar
        """
        # Doküman ID'ye göre gruplandır
        doc_groups = {}
        for chunk_data in processed_chunks:
            doc_id = chunk_data["doc_id"]
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(chunk_data)
        
        # Dokümanları ortalama skorlarına göre sırala
        doc_avg_scores = {}
        for doc_id, chunks in doc_groups.items():
            doc_avg_scores[doc_id] = sum(c["score"] for c in chunks) / len(chunks)
        
        sorted_docs = sorted(doc_avg_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Yeni sıralamayı oluştur
        reordered_chunks = []
        for doc_id, _ in sorted_docs:
            # Her dokümanın kendi chunk'larını belge içindeki orijinal sıralarına göre sırala
            doc_chunks = sorted(doc_groups[doc_id], key=lambda x: (
                x["chunk"].metadata.get("start_char", 0),
                x["chunk"].metadata.get("chunk_index", x["index"])
            ))
            reordered_chunks.extend(doc_chunks)
        
        return reordered_chunks
    
    def _trim_to_max_tokens(self, processed_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk'ları maksimum token sayısına sığacak şekilde kırpar.
        
        Args:
            processed_chunks: İşlenmiş chunk'lar
            
        Returns:
            List[Dict[str, Any]]: Token limitine göre kırpılmış chunk'lar
        """
        if not processed_chunks:
            return []
        
        max_tokens = self.config.max_tokens
        current_tokens = 0
        selected_chunks = []
        
        # Ayırıcı token sayısı
        separator_tokens = count_tokens(self.config.chunk_separator)
        
        # Referans formatı için ek tokenler
        reference_tokens = 0
        if self.config.add_references:
            # "[Source: doc_name]" formatı için yaklaşık token sayısı
            reference_tokens = 10
        
        # Her chunk'ı eklemeden önce kontrol et
        for chunk_data in processed_chunks:
            # Bu chunk'ın eklenirse kaç token kullanılacağını hesapla
            chunk_token_count = chunk_data["token_count"]
            
            if self.config.add_references:
                chunk_token_count += reference_tokens
            
            # İlk chunk veya ayırıcı tokenlerini ekle
            if selected_chunks:
                chunk_token_count += separator_tokens
            
            # Bu chunk eklenirse limit aşılacak mı?
            if current_tokens + chunk_token_count > max_tokens:
                # Sınıra yaklaşıldı, chunk'ı ekle ve döngüden çık
                break
            
            # Chunk'ı ekle ve token sayacını güncelle
            selected_chunks.append(chunk_data)
            current_tokens += chunk_token_count
        
        logger.info(f"Token limiti: {max_tokens}, kullanılan: {current_tokens}, seçilen chunk sayısı: {len(selected_chunks)}")
        return selected_chunks
    
    def _format_context(self, processed_chunks: List[Dict[str, Any]]) -> str:
        """
        Seçilen chunk'lardan formatlı context metni oluşturur.
        
        Args:
            processed_chunks: İşlenmiş ve seçilmiş chunk'lar
            
        Returns:
            str: Formatlı context metni
        """
        if not processed_chunks:
            return ""
        
        # Context metnini oluştur
        context_parts = []
        
        for chunk_data in processed_chunks:
            chunk = chunk_data["chunk"]
            chunk_text = chunk.text
            
            # Referans ekle
            if self.config.add_references:
                source = chunk_data.get("source", chunk.metadata.get("source", "unknown"))
                doc_id = chunk_data.get("doc_id", chunk.metadata.get("doc_id", "unknown"))
                
                # Okumayı kolaylaştırmak için kaynak adını kısalt
                source_name = source
                if len(source_name) > 50:
                    source_name = source_name[:47] + "..."
                
                # Referans formatını ekle
                if self.config.optimize_for_llm:
                    # LLM için optimize edilmiş format
                    chunk_text += f"\n[Source: {source_name}]"
                else:
                    # Standart format
                    chunk_text += f"\n(Source: {source_name}, ID: {doc_id})"
            
            context_parts.append(chunk_text)
        
        # Chunk'ları birleştir
        context = self.config.chunk_separator.join(context_parts)
        
        return context
    
    def _calculate_recency_factor(self, date_str: str) -> float:
        """
        Tarih bilgisinden yenilik faktörünü hesaplar (0-1 arası).
        
        Args:
            date_str: Tarih string'i (çeşitli formatlarda olabilir)
            
        Returns:
            float: Yenilik faktörü (0-1 arası, 1 en yeni)
        """
        try:
            # Tarih formatını tespit et ve parse et
            date_obj = None
            
            # ISO format (2025-01-01T12:30:45)
            if 'T' in date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str)
                except ValueError:
                    pass
            
            # Simple date (2025-01-01)
            if not date_obj and '-' in date_str and len(date_str) >= 10:
                try:
                    date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except ValueError:
                    pass
            
            # Formatted date (January 1, 2025)
            if not date_obj:
                try:
                    date_obj = datetime.strptime(date_str, "%B %d, %Y")
                except ValueError:
                    pass
            
            if not date_obj:
                return 0.5  # Tarih ayrıştırılamadı, orta değeri kullan
            
            # Bugünden ne kadar eski?
            now = datetime.now()
            days_old = (now - date_obj).days
            
            # 2 yıldan eski mi?
            if days_old > 730:
                return 0.0
            
            # 0-1 arası yenilik faktörü (2 yıl içinde lineer azalan)
            recency = 1.0 - (days_old / 730)
            return max(0.0, min(1.0, recency))
            
        except Exception as e:
            logger.warning(f"Yenilik faktörü hesaplanamadı: {str(e)}")
            return 0.5  # Hata durumunda orta değeri kullan
    
    def recursive_retrieve(self, initial_chunks: List[Chunk], query: str) -> List[Chunk]:
        """
        İlk retrieval sonuçlarından yinelemeli olarak daha fazla ilgili chunk getirir.
        
        Args:
            initial_chunks: İlk retrieval sonuçları
            query: Kullanıcı sorgusu
            
        Returns:
            List[Chunk]: Genişletilmiş chunk listesi
        """
        if not self.config.recursive_retriever or not self.llm_service:
            return initial_chunks
        
        logger.info(f"Yinelemeli retrieval başlatılıyor: {len(initial_chunks)} başlangıç chunk'ı")
        
        # LLM için sorguyu ve ilk chunk'ları işle
        recursive_prompt = """
        ### Talimat
        Aşağıdaki kullanıcı sorusunu ve ilgili içerikleri inceleyerek, sorunun tam olarak cevaplanması için 
        HANGI EK BILGILERE ihtiyaç var? İçerikler arasındaki boşlukları tespit edin ve eksik bilgileri 
        belirtin. Sadece soruda eksik kalan ve içeriklerde bulunmayan bilgilere odaklanın.
        
        ### Kullanıcı Sorusu
        {query}
        
        ### İçerikler
        {content}
        
        ### Eksik Bilgiler
        Soruyu tam olarak cevaplamak için şu ek bilgilere ihtiyaç var:
        """
        
        # İlk chunk'lardan context oluştur (maksimum 2000 token)
        temp_config = ContextConfig(max_tokens=2000, add_references=False)
        temp_manager = ContextManager(temp_config)
        initial_context = temp_manager.generate_context(initial_chunks, query)
        
        # LLM ile eksik bilgileri tespit et
        try:
            prompt = recursive_prompt.format(query=query, content=initial_context)
            response = self.llm_service.generate_text(prompt, max_tokens=300, temperature=0.3)
            
            # Eksik bilgileri ayrıştır
            missing_info = response.strip()
            
            # Eksik bilgilerden alt sorgular oluştur
            follow_up_query = f"{query} {missing_info}"
            
            # Alt sorgularla ilgili yeni chunk'lar getir
            # Bu kısım, mevcut retrieval pipeline'a bağlı olmalı
            # Şimdilik sadece ilk sonuçları döndürüyoruz
            # TODO: Gerçek recursive retrieval implementasyonu
            logger.info(f"Yinelemeli sorgu oluşturuldu: {follow_up_query[:100]}...")
            
            # Recursive retrieval sonuçlarını original sonuçlarla birleştir
            return initial_chunks
            
        except Exception as e:
            logger.error(f"Yinelemeli retrieval hatası: {str(e)}")
            return initial_chunks