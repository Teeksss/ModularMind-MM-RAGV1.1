"""
Sorgu İşleme Modülü.
Sorgu genişletme, yeniden yazma ve ayrıştırma işlevlerini sağlar.
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional, Union
from enum import Enum

from ModularMind.API.services.llm_service import LLMService
from ModularMind.API.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

class QueryType(str, Enum):
    """Sorgu tipleri."""
    FACTUAL = "factual"         # Gerçek sorgulama (ne, nerede, ne zaman)
    ANALYTICAL = "analytical"   # Analitik sorgulama (neden, nasıl)
    EXPLORATORY = "exploratory" # Keşif sorguları (X hakkında bilgi ver)
    COMPARATIVE = "comparative" # Karşılaştırmalı (X ve Y arasındaki fark nedir)
    PROCEDURAL = "procedural"   # Prosedürel (X nasıl yapılır)
    DEFINITIONAL = "definitional" # Tanımsal (X nedir)
    CAUSAL = "causal"          # Nedensel (X'in nedeni nedir)
    HYPOTHETICAL = "hypothetical" # Hipotetik (Eğer X olursa ne olur)

class QueryProcessor:
    """
    Sorgu işleme ana sınıfı.
    """
    
    def __init__(
        self, 
        embedding_service: Optional[EmbeddingService] = None,
        llm_service: Optional[LLMService] = None
    ):
        """
        Args:
            embedding_service: Gömme servisi
            llm_service: LLM servisi
        """
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        
        # Sorgu önişleme pattern'leri
        self.preprocessing_patterns = [
            (r'\s+', ' '),  # Birden fazla boşluğu tek boşluğa indirgeme
            (r'^\s+|\s+$', ''),  # Başlangıç ve sondaki boşlukları kaldırma
            (r'[,;:\-\'"]', ' ')  # Bazı noktalama işaretlerini boşluğa çevirme
        ]
    
    def preprocess_query(self, query: str) -> str:
        """
        Sorguyu önişler.
        
        Args:
            query: Sorgu metni
            
        Returns:
            str: Önişlenmiş sorgu
        """
        processed_query = query
        
        # Pattern'leri uygula
        for pattern, replacement in self.preprocessing_patterns:
            processed_query = re.sub(pattern, replacement, processed_query)
        
        # Stop kelimeleri kaldırma (opsiyonel)
        # processed_query = self._remove_stop_words(processed_query)
        
        return processed_query
    
    def expand_query(self, query: str) -> str:
        """
        Sorguyu genişletir.
        
        Args:
            query: Sorgu metni
            
        Returns:
            str: Genişletilmiş sorgu
        """
        # Önişleme yap
        processed_query = self.preprocess_query(query)
        
        # LLM varsa sorgu genişletme yap
        if self.llm_service:
            try:
                expanded_query = self._expand_with_llm(processed_query)
                if expanded_query and expanded_query != processed_query:
                    return expanded_query
            except Exception as e:
                logger.error(f"LLM sorgu genişletme hatası: {str(e)}")
        
        # LLM yoksa/başarısız olursa, basit anahtar kelime eklemeyi dene
        expanded_query = self._expand_with_synonyms(processed_query)
        
        return expanded_query or processed_query
    
    def rewrite_query(self, query: str, context: Optional[str] = None) -> str:
        """
        Sorguyu yeniden yazar.
        
        Args:
            query: Sorgu metni
            context: Bağlam metni (opsiyonel)
            
        Returns:
            str: Yeniden yazılmış sorgu
        """
        # LLM yoksa, orijinal sorguyu döndür
        if not self.llm_service:
            return query
        
        try:
            # Sorgu tipini belirle
            query_type = self._classify_query(query)
            
            # Sorgu tipine göre yeniden yazma stratejisini belirle
            if query_type == QueryType.FACTUAL:
                prompt_template = "Şu sorguyu, gerçek bilgi arayan ve daha spesifik terimler içeren bir sorguya dönüştür: '{query}'"
            
            elif query_type == QueryType.ANALYTICAL:
                prompt_template = "Şu analitik sorguyu, kavramlar arasındaki ilişkileri daha iyi açığa çıkaracak şekilde yeniden yaz: '{query}'"
            
            elif query_type == QueryType.EXPLORATORY:
                prompt_template = "Şu keşif sorgusunu, aranabilir anahtar terimleri daha iyi vurgulayacak şekilde yeniden yaz: '{query}'"
            
            elif query_type == QueryType.COMPARATIVE:
                prompt_template = "Şu karşılaştırmalı sorguyu, karşılaştırılan öğeleri ve karşılaştırma boyutlarını daha net belirtecek şekilde yeniden yaz: '{query}'"
            
            elif query_type == QueryType.PROCEDURAL:
                prompt_template = "Şu prosedürel sorguyu, aradığı talimatları ve adımları daha net belirtecek şekilde yeniden yaz: '{query}'"
            
            else:
                prompt_template = "Şu sorguyu, vektör arama için daha etkili olacak şekilde yeniden yaz, önemli anahtar terimleri vurgula: '{query}'"
            
            # Eğer bağlam varsa, daha spesifik bir yeniden yazma talimatı kullan
            if context:
                prompt_template = f"""
                Verilen bağlamı dikkate alarak, şu sorguyu yeniden yaz: '{query}'
                
                Bağlam:
                {context}
                
                Sorguyu, bağlamdaki bilgilerle daha iyi eşleşecek şekilde yeniden düzenle ve genişlet.
                Yeniden yazılmış sorgu, orijinal sorgudaki ana hedefi korumalı, ancak daha açık ve kapsamlı olmalıdır.
                Sadece yeniden yazılmış sorguyu döndür, başka açıklama ekleme.
                """
            else:
                prompt_template = prompt_template.format(query=query) + "\n\nSadece yeniden yazılmış sorguyu döndür, başka açıklama ekleme."
            
            # LLM ile sorguyu yeniden yaz
            rewritten_query = self.llm_service.generate_text(
                prompt=prompt_template,
                max_tokens=100
            )
            
            # Metni temizle
            rewritten_query = rewritten_query.strip()
            
            # Tırnak işaretlerini kaldır
            if rewritten_query.startswith('"') and rewritten_query.endswith('"'):
                rewritten_query = rewritten_query[1:-1]
            
            return rewritten_query or query
            
        except Exception as e:
            logger.error(f"Sorgu yeniden yazma hatası: {str(e)}")
            return query
    
    def decompose_query(self, query: str) -> List[str]:
        """
        Karmaşık sorguyu alt sorgu parçalarına ayırır.
        
        Args:
            query: Sorgu metni
            
        Returns:
            List[str]: Alt sorgular
        """
        # LLM yoksa, orijinal sorguyu tek eleman olarak döndür
        if not self.llm_service:
            return [query]
        
        try:
            # Sorgu uzunluğunu kontrol et
            if len(query) < 20:  # Çok kısa sorgular için ayrıştırma yapma
                return [query]
            
            # Sorgunun karmaşıklığını değerlendir
            complexity_score = self._assess_query_complexity(query)
            
            # Karmaşıklık skoru düşükse, ayrıştırma yapma
            if complexity_score < 0.5:
                return [query]
            
            # Prompt oluştur
            prompt = f"""
            Aşağıdaki karmaşık sorguyu daha basit alt sorgu parçalarına ayır:
            
            Sorgu: {query}
            
            Bu sorguyu 2-4 adet alt sorguya ayrıştır. Her alt sorgu, orijinal sorgudaki farklı bir yönü veya kısmı ele almalı.
            Alt sorgular bir arada, orijinal sorgudaki tüm bilgileri kapsamalı.
            
            Alt sorguları JSON dizisi olarak döndür:
            ["Alt sorgu 1", "Alt sorgu 2", ...]
            
            Sadece JSON dizisini döndür, başka açıklama ekleme.
            """
            
            # LLM ile sorguyu ayrıştır
            response = self.llm_service.generate_text(prompt, max_tokens=200)
            
            # JSON yanıtı ayrıştır
            response = response.strip()
            
            # Yanıt JSON formatında değilse, JSON kısmını çıkar
            if not response.startswith("["):
                json_start = response.find("[")
                json_end = response.rfind("]") + 1
                
                if json_start >= 0 and json_end > json_start:
                    response = response[json_start:json_end]
                else:
                    # JSON formatı bulunamadı
                    return [query]
            
            sub_queries = json.loads(response)
            
            # Alt sorguları kontrol et
            if not sub_queries or len(sub_queries) <= 1:
                return [query]
            
            # Alt sorguları döndür
            return sub_queries
            
        except Exception as e:
            logger.error(f"Sorgu ayrıştırma hatası: {str(e)}")
            return [query]
    
    def _remove_stop_words(self, query: str) -> str:
        """
        Sorgudan stop kelimeleri kaldırır.
        
        Args:
            query: Sorgu metni
            
        Returns:
            str: Stop kelimeleri kaldırılmış sorgu
        """
        # Basit Türkçe ve İngilizce stop kelimeler
        stop_words = {
            've', 'veya', 'ile', 'de', 'da', 'ki', 'bu', 'şu', 'o', 'bir', 'için',
            'and', 'or', 'the', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'at', 'is', 'are'
        }
        
        # Sorguyu kelimelere ayır
        words = query.lower().split()
        
        # Stop kelimeleri filtrele
        filtered_words = [word for word in words if word not in stop_words]
        
        # Kelimelerden sorguyu yeniden oluştur
        return ' '.join(filtered_words)
    
    def _expand_with_llm(self, query: str) -> str:
        """
        LLM kullanarak sorguyu genişletir.
        
        Args:
            query: Sorgu metni
            
        Returns:
            str: Genişletilmiş sorgu
        """
        prompt = f"""
        Aşağıdaki arama sorgusunu, vektör arama için daha etkili olacak şekilde genişlet:
        
        Orijinal Sorgu: {query}
        
        Genişletilmiş bir sorgu oluştur:
        1. Anahtar kavramları koru
        2. Eş anlamlı sözcükler ve ilgili kavramlar ekle
        3. Var olan bir "ne, neden, nasıl" sorusunu açıkla
        4. Sorgu açık bir soru içermiyorsa soru formuna getirme
        
        Sadece genişletilmiş sorguyu döndür, başka açıklama ekleme.
        """
        
        expanded_query = self.llm_service.generate_text(prompt, max_tokens=150)
        return expanded_query.strip()
    
    def _expand_with_synonyms(self, query: str) -> str:
        """
        Basit sözlük tabanlı eş anlamlılarla sorguyu genişletir.
        
        Args:
            query: Sorgu metni
            
        Returns:
            str: Genişletilmiş sorgu
        """
        # Basit eş anlamlılar sözlüğü
        synonyms = {
            # Türkçe
            "nasıl": ["ne şekilde", "hangi yöntemle", "ne biçimde"],
            "neden": ["niçin", "hangi sebeple", "niye"],
            "ne zaman": ["hangi tarihte", "ne vakit", "hangi zamanda"],
            "nerede": ["hangi yerde", "hangi konumda", "nereye"],
            "kim": ["hangi kişi", "hangi şahıs"],
            "bilgi": ["malumat", "veri", "enformasyon"],
            "özellik": ["nitelik", "vasıf", "karakter"],
            "örnek": ["misal", "numune", "model"],
            "fayda": ["yarar", "kazanç", "avantaj"],
            "sorun": ["problem", "mesele", "zorluk"],
            
            # İngilizce
            "how": ["in what way", "by what means", "method"],
            "why": ["for what reason", "what is the cause", "purpose"],
            "when": ["at what time", "on which date", "during what period"],
            "where": ["at what location", "in which place", "position"],
            "who": ["which person", "what individual"],
            "information": ["data", "facts", "knowledge"],
            "feature": ["characteristic", "attribute", "property"],
            "example": ["instance", "sample", "illustration"],
            "benefit": ["advantage", "gain", "value"],
            "problem": ["issue", "difficulty", "challenge"]
        }
        
        # Sorguyu kelimelere ayır
        words = query.lower().split()
        
        # Yeni sorgular için kelime setleri
        expanded_words = [words]
        
        # Her bir kelime için eş anlamlılar varsa, yeni sorgular oluştur
        for i, word in enumerate(words):
            if word in synonyms:
                # Eş anlamlı kelimeler ile yeni sorgular oluştur
                for synonym in synonyms[word][:2]:  # En fazla 2 eş anlamlı kelime kullan
                    new_words = words.copy()
                    new_words[i] = synonym
                    expanded_words.append(new_words)
        
        # Benzersiz sorguları oluştur
        expanded_queries = [' '.join(word_list) for word_list in expanded_words]
        
        # Tüm sorguları birleştir
        return ' OR '.join([f'({q})' for q in expanded_queries])
    
    def _classify_query(self, query: str) -> QueryType:
        """
        Sorgu tipini belirler.
        
        Args:
            query: Sorgu metni
            
        Returns:
            QueryType: Sorgu tipi
        """
        # LLM varsa, daha doğru sınıflandırma yap
        if self.llm_service:
            try:
                return self._classify_with_llm(query)
            except Exception as e:
                logger.error(f"LLM ile sorgu sınıflandırma hatası: {str(e)}")
        
        # Basit kural tabanlı sınıflandırma
        query_lower = query.lower()
        
        # Soru tiplerini belirlemek için pattern'ler
        patterns = [
            # Türkçe
            (r'\bnasıl\b', QueryType.PROCEDURAL),
            (r'\bnedir\b', QueryType.DEFINITIONAL),
            (r'\bneden\b|\bniçin\b|\bniye\b', QueryType.CAUSAL),
            (r'\bne zaman\b|\bhangi tarihte\b', QueryType.FACTUAL),
            (r'\bnerede\b|\bhangi yerde\b', QueryType.FACTUAL),
            (r'\bkim\b|\bkimler\b|\bhangi kişi\b', QueryType.FACTUAL),
            (r'\bargıları\b|\bfarklılık\b|\bbenzerlik\b|\bkarşılaştır\b', QueryType.COMPARATIVE),
            (r'\bhakkında\b|\bbilgi\b|\bnedir\b|\btanım\b', QueryType.EXPLORATORY),
            (r'\beğer\b|\bolsaydı\b|\bse\b|\bmümkün\b', QueryType.HYPOTHETICAL),
            
            # İngilizce
            (r'\bhow\b', QueryType.PROCEDURAL),
            (r'\bwhat is\b|\bdefinition\b', QueryType.DEFINITIONAL),
            (r'\bwhy\b|\bcause\b|\breason\b', QueryType.CAUSAL),
            (r'\bwhen\b|\bdate\b|\btime\b', QueryType.FACTUAL),
            (r'\bwhere\b|\blocation\b|\bplace\b', QueryType.FACTUAL),
            (r'\bwho\b|\bperson\b|\bpeople\b', QueryType.FACTUAL),
            (r'\bcompare\b|\bdifference\b|\bsimilarity\b', QueryType.COMPARATIVE),
            (r'\babout\b|\binformation\b|\bexplain\b', QueryType.EXPLORATORY),
            (r'\bif\b|\bcould\b|\bwould\b|\bpossible\b', QueryType.HYPOTHETICAL),
        ]
        
        # Her pattern'i kontrol et
        for pattern, query_type in patterns:
            if re.search(pattern, query_lower):
                return query_type
        
        # Varsayılan tip
        return QueryType.EXPLORATORY
    
    def _classify_with_llm(self, query: str) -> QueryType:
        """
        LLM kullanarak sorgu tipini belirler.
        
        Args:
            query: Sorgu metni
            
        Returns:
            QueryType: Sorgu tipi
        """
        prompt = f"""
        Aşağıdaki sorgu metnini analiz et ve en uygun sorgu tipini belirle.
        
        Sorgu: {query}
        
        Sorgu tipleri:
        - FACTUAL: Gerçek bilgi sorgulama (ne, nerede, ne zaman)
        - ANALYTICAL: Analitik sorgulama (neden, nasıl)
        - EXPLORATORY: Keşif sorguları (X hakkında bilgi ver)
        - COMPARATIVE: Karşılaştırmalı (X ve Y arasındaki fark nedir)
        - PROCEDURAL: Prosedürel (X nasıl yapılır)
        - DEFINITIONAL: Tanımsal (X nedir)
        - CAUSAL: Nedensel (X'in nedeni nedir)
        - HYPOTHETICAL: Hipotetik (Eğer X olursa ne olur)
        
        Sadece sorgu tipini döndür, başka açıklama ekleme.
        """
        
        response = self.llm_service.generate_text(prompt, max_tokens=20)
        response = response.strip().upper()
        
        # Yanıtta query type varsa çıkar
        for query_type in QueryType:
            if query_type.name