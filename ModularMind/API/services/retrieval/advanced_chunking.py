"""
Gelişmiş Parçalama (Chunking) Servisi.
Semantik ve hiyerarşik belge parçalama işlevlerini sağlar.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Union, Set, Tuple
import uuid
import hashlib
import numpy as np
from dataclasses import dataclass

from ModularMind.API.services.retrieval.models import Document, Chunk
from ModularMind.API.services.llm_service import LLMService

logger = logging.getLogger(__name__)

@dataclass
class ChunkingConfig:
    """Chunking yapılandırması."""
    
    # Chunk boyutu (karakterler, yaklaşık token sayısı)
    chunk_size: int = 500
    
    # Chunk örtüşme miktarı (karakterler)
    chunk_overlap: int = 50
    
    # Semantik chunking kullan
    use_semantic_chunking: bool = True
    
    # Hiyerarşik yapıyı koru
    preserve_hierarchy: bool = True
    
    # Bölüm türleri ve önemlilik ağırlıkları
    section_markers: Dict[str, float] = None
    
    # Örtüşme stratejisi (fixed, proportional)
    overlap_strategy: str = "fixed"
    
    # Örtüşme oranı (proportional stratejisi için)
    overlap_ratio: float = 0.1
    
    # Minimum chunk boyutu
    min_chunk_size: int = 100
    
    # Maksimum chunk boyutu
    max_chunk_size: int = 1500
    
    # Her chunkta etiket ve başlık bilgisi tut
    keep_metadata: bool = True

class BasicChunker:
    """
    Temel belge parçalama sınıfı.
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Args:
            config: Chunking yapılandırması
        """
        self.config = config or ChunkingConfig()
    
    def create_chunks(
        self, 
        text: str, 
        chunk_size: Optional[int] = None, 
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Metni parçalara ayırır.
        
        Args:
            text: Parçalanacak metin
            chunk_size: Chunk boyutu
            chunk_overlap: Chunk örtüşmesi
            metadata: Belge meta verileri
            
        Returns:
            List[Chunk]: Oluşturulan chunk'lar
        """
        # Parametreleri ayarla
        chunk_size = chunk_size or self.config.chunk_size
        chunk_overlap = chunk_overlap or self.config.chunk_overlap
        metadata = metadata or {}
        
        # Boş metin kontrolü
        if not text or not text.strip():
            return []
        
        # Metni ayır
        chunks = []
        start = 0
        chunk_index = 0
        
        # Paragraf sınırlarını bul
        paragraph_breaks = [m.start() for m in re.finditer(r'\n\s*\n', text)]
        
        while start < len(text):
            # Son pozisyonu hesapla
            end = min(start + chunk_size, len(text))
            
            # Paragraf sınırında bitirmeye çalış
            if end < len(text):
                # Mevcut son pozisyonun ilerisindeki en yakın paragraf sonu bul
                next_break = next((pb for pb in paragraph_breaks if pb > start and pb < end), None)
                
                # Paragraf sonu varsa ve çok uzakta değilse orada kes
                if next_break and (next_break - start) >= self.config.min_chunk_size:
                    end = next_break
                else:
                    # Paragraf sonu yoksa, cümle sınırında bitirmeye çalış
                    sentence_end = text.rfind('.', start, end)
                    if sentence_end > start + self.config.min_chunk_size:
                        end = sentence_end + 1
            
            # Chunk içeriğini al
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                # Metadata oluştur
                chunk_metadata = metadata.copy() if metadata else {}
                
                # Chunk bilgilerini ekle
                chunk_metadata["chunk_index"] = chunk_index
                chunk_metadata["chunk_start"] = start
                chunk_metadata["chunk_end"] = end
                
                # Chunk ID'si oluştur
                chunk_id = self._generate_chunk_id(chunk_text, chunk_metadata)
                
                # Chunk nesnesi oluştur
                chunk = Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    metadata=chunk_metadata,
                    document_id=metadata.get("document_id") or metadata.get("id"),
                    chunk_index=chunk_index
                )
                
                chunks.append(chunk)
                chunk_index += 1
            
            # Bir sonraki başlangıç pozisyonunu güncelle
            start = end - chunk_overlap
            
            # Negatif ilerlemeyi önle
            if start <= 0 or start >= len(text):
                break
        
        return chunks
    
    def _generate_chunk_id(self, text: str, metadata: Dict[str, Any]) -> str:
        """
        Chunk için benzersiz ID oluşturur.
        
        Args:
            text: Chunk metni
            metadata: Chunk meta verileri
            
        Returns:
            str: Chunk ID
        """
        # Belge ID'si ve chunk indeksi varsa bunları kullan
        doc_id = metadata.get("document_id", "") or metadata.get("id", "")
        chunk_index = metadata.get("chunk_index", "")
        
        if doc_id and chunk_index is not None:
            return f"{doc_id}_{chunk_index}"
        
        # Yoksa hash oluştur
        content_hash = hashlib.md5((text[:100] + str(metadata.get("chunk_start", ""))).encode()).hexdigest()
        return f"chunk_{content_hash}"

class SemanticChunker(BasicChunker):
    """
    Semantik belge parçalama sınıfı.
    Anlamlı bölümlere göre belgeyi daha akıllıca parçalar.
    """
    
    def __init__(
        self, 
        llm_service: Optional[LLMService] = None,
        config: Optional[ChunkingConfig] = None
    ):
        """
        Args:
            llm_service: LLM servisi
            config: Chunking yapılandırması
        """
        super().__init__(config)
        self.llm_service = llm_service
        
        # Varsayılan bölüm işaretleyicileri
        if not self.config.section_markers:
            self.config.section_markers = {
                r'^#+\s+': 2.0,           # Markdown başlık
                r'^Title:': 2.0,          # Başlık
                r'^Chapter\s+\d+:': 2.0,  # Bölüm
                r'^\d+\.\s+': 1.5,        # Numaralı liste
                r'^\*\s+': 1.0,           # Madde işareti
                r'^\-\s+': 1.0,           # Tire
                r'^[A-Z][A-Z\s]+:': 1.5,  # BÜYÜK HARFLERLE YAZILMIŞ BAŞLIKLAR
                r'^\d+\.\d+\.\s+': 1.5    # Alt bölüm (1.1., 1.2., vs.)
            }
    
    def create_chunks(
        self, 
        text: str, 
        chunk_size: Optional[int] = None, 
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Metni semantik parçalara ayırır.
        
        Args:
            text: Parçalanacak metin
            chunk_size: Chunk boyutu
            chunk_overlap: Chunk örtüşmesi
            metadata: Belge meta verileri
            
        Returns:
            List[Chunk]: Oluşturulan chunk'lar
        """
        # Parametreleri ayarla
        chunk_size = chunk_size or self.config.chunk_size
        chunk_overlap = chunk_overlap or self.config.chunk_overlap
        metadata = metadata or {}
        
        # Boş metin kontrolü
        if not text or not text.strip():
            return []
        
        # Eğer semantik chunking devre dışıysa, temel chunking kullan
        if not self.config.use_semantic_chunking:
            return super().create_chunks(text, chunk_size, chunk_overlap, metadata)
        
        # Semantik bölümleri bul
        semantic_sections = self._identify_semantic_sections(text)
        
        # LLM varsa ve semantik bölüm sayısı fazla değilse, LLM ile semantik anlama iyileştir
        if self.llm_service and len(semantic_sections) < 20:
            semantic_sections = self._refine_sections_with_llm(semantic_sections)
        
        # Bölümlerden chunk'lar oluştur
        chunks = []
        chunk_index = 0
        current_chunk_text = ""
        current_chunk_sections = []
        
        for section in semantic_sections:
            section_text = section["text"]
            section_level = section.get("level", 0)
            
            # Şu anki bölümü eklemek, chunk'ı aşacak mı kontrol et
            if len(current_chunk_text) + len(section_text) > chunk_size and current_chunk_text:
                # Mevcut chunk'ı oluştur
                chunk_text = current_chunk_text.strip()
                
                if chunk_text:
                    # Metadata oluştur
                    chunk_metadata = metadata.copy() if metadata else {}
                    
                    # Chunk bilgilerini ekle
                    chunk_metadata["chunk_index"] = chunk_index
                    
                    # Eğer içindeki bölümler hakkında bilgi tutmak istenirse
                    if self.config.keep_metadata:
                        chunk_metadata["sections"] = [s.get("title", "") for s in current_chunk_sections if "title" in s]
                        chunk_metadata["section_levels"] = [s.get("level", 0) for s in current_chunk_sections]
                        
                        # En üst seviye başlığı tut
                        top_level_sections = [s.get("title", "") for s in current_chunk_sections if s.get("level", 999) == min([s.get("level", 999) for s in current_chunk_sections])]
                        if top_level_sections:
                            chunk_metadata["top_level_section"] = top_level_sections[0]
                    
                    # Chunk ID'si oluştur
                    chunk_id = self._generate_chunk_id(chunk_text, chunk_metadata)
                    
                    # Chunk nesnesi oluştur
                    chunk = Chunk(
                        id=chunk_id,
                        text=chunk_text,
                        metadata=chunk_metadata,
                        document_id=metadata.get("document_id") or metadata.get("id"),
                        chunk_index=chunk_index
                    )
                    
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Yeni chunk başlat
                current_chunk_text = section_text
                current_chunk_sections = [section]
            else:
                # Bölümü mevcut chunk'a ekle
                current_chunk_text += "\n\n" + section_text if current_chunk_text else section_text
                current_chunk_sections.append(section)
        
        # Son chunk'ı ekle
        if current_chunk_text.strip():
            # Metadata oluştur
            chunk_metadata = metadata.copy() if metadata else {}
            
            # Chunk bilgilerini ekle
            chunk_metadata["chunk_index"] = chunk_index
            
            # Eğer içindeki bölümler hakkında bilgi tutmak istenirse
            if self.config.keep_metadata:
                chunk_metadata["sections"] = [s.get("title", "") for s in current_chunk_sections if "title" in s]
                chunk_metadata["section_levels"] = [s.get("level", 0) for s in current_chunk_sections]
                
                # En üst seviye başlığı tut
                top_level_sections = [s.get("title", "") for s in current_chunk_sections if s.get("level", 999) == min([s.get("level", 999) for s in current_chunk_sections])]
                if top_level_sections:
                    chunk_metadata["top_level_section"] = top_level_sections[0]
            
            # Chunk ID'si oluştur
            chunk_id = self._generate_chunk_id(current_chunk_text.strip(), chunk_metadata)
            
            # Chunk nesnesi oluştur
            chunk = Chunk(
                id=chunk_id,
                text=current_chunk_text.strip(),
                metadata=chunk_metadata,
                document_id=metadata.get("document_id") or metadata.get("id"),
                chunk_index=chunk_index
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _identify_semantic_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Metindeki semantik bölümleri tanımlar.
        
        Args:
            text: Metin
            
        Returns:
            List[Dict[str, Any]]: Semantik bölümler
        """
        # Metin boş ise boş liste döndür
        if not text.strip():
            return []
        
        # Önce satır satır ayır
        lines = text.split('\n')
        
        # Daha sonraki aşamada birleştirilecek bölümleri tut
        sections = []
        current_section = {"text": "", "level": 0, "title": ""}
        current_level = 0
        
        for line in lines:
            line_text = line.strip()
            
            # Boş satırları atla
            if not line_text:
                if current_section["text"]:
                    current_section["text"] += "\n"
                continue
            
            # Başlık veya bölüm işaretçisi mi kontrol et
            is_section_marker = False
            section_level = 0
            title = ""
            
            for marker_pattern, level_weight in self.config.section_markers.items():
                if re.match(marker_pattern, line_text):
                    is_section_marker = True
                    section_level = level_weight
                    
                    # Başlık metnini çıkar
                    title_match = re.match(marker_pattern + r'(.*)', line_text)
                    if title_match:
                        title = title_match.group(1).strip()
                    break
            
            # Semantik bölüm sınırı bulunduysa
            if is_section_marker:
                # Önceki bölümü kaydet (içeriği varsa)
                if current_section["text"].strip():
                    sections.append(current_section)
                
                # Yeni bölüm başlat
                current_section = {
                    "text": line_text,
                    "level": section_level,
                    "title": title
                }
                current_level = section_level
            else:
                # Mevcut bölüme ekle
                current_section["text"] += ("\n" + line_text if current_section["text"] else line_text)
        
        # Son bölümü ekle
        if current_section["text"].strip():
            sections.append(current_section)
        
        # Eğer hiç bölüm bulunamazsa, tüm metni tek bölüm olarak işle
        if not sections:
            sections = [{"text": text.strip(), "level": 0, "title": ""}]
        
        # Paragraf tabanlı bölümleme yap (şu anda sezgisel olarak parçaladığımız bölümler çok büyükse)
        refined_sections = []
        for section in sections:
            section_text = section["text"]
            
            # Bölüm chunking limitini aşıyorsa, paragraf yapısına göre tekrar böl
            if len(section_text) > self.config.max_chunk_size * 1.5:
                paragraphs = re.split(r'\n\s*\n', section_text)
                
                # Her paragrafı ayrı bölüm yap, ana bölümün seviyesini koru
                for i, para in enumerate(paragraphs):
                    if para.strip():
                        para_section = {
                            "text": para.strip(),
                            "level": section["level"],
                            "title": section["title"] if i == 0 else ""
                        }
                        refined_sections.append(para_section)
            else:
                refined_sections.append(section)
        
        return refined_sections
    
    def _refine_sections_with_llm(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        LLM kullanarak semantik bölümleri iyileştirir.
        
        Args:
            sections: Semantik bölümler
            
        Returns:
            List[Dict[str, Any]]: İyileştirilmiş semantik bölümler
        """
        if not self.llm_service:
            return sections
        
        try:
            # Kısa metinler için LLM ile analiz yapma
            total_length = sum(len(section["text"]) for section in sections)
            if total_length < 500 or len(sections) <= 1:
                return sections
            
            # Bölümleri özetle ve daha anlamlı isimler ver
            sections_text = []
            for i, section in enumerate(sections):
                title = section.get("title", "")
                level = section.get("level", 0)
                text_preview = section["text"][:100] + ("..." if len(section["text"]) > 100 else "")
                
                sections_text.append(f"Section {i+1}. Level: {level}, Title: {title}\nPreview: {text_preview}")
            
            # LLM prompt oluştur
            prompt = f"""
            Aşağıdaki belge bölümlerini incele ve her bölüm için daha açıklayıcı başlıklar öner.
            Bölümler hiyerarşik olabilir ve bazıları zaten başlıklara sahip olabilir.
            
            Mevcut bölümler:
            
            {"\n\n".join(sections_text)}
            
            Her bölüm için yanıtını şu formatta JSON dizisi olarak ver:
            [
                {{"section_index": 0, "suggested_title": "Önerilen Başlık 1"}},
                {{"section_index": 1, "suggested_title": "Önerilen Başlık 2"}},
                ...
            ]
            
            Sadece JSON döndür, başka açıklama ekleme.
            """
            
            # LLM ile analiz yap
            response = self.llm_service.generate_text(prompt, max_tokens=500)
            
            # JSON yanıtı ayrıştır
            import json
            try:
                response = response.strip()
                
                # Yanıt JSON formatında değilse, JSON kısmını çıkar
                if not response.startswith("["):
                    json_start = response.find("[")
                    json_end = response.rfind("]") + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        response = response[json_start:json_end]
                    else:
                        # JSON formatı bulunamadı
                        return sections
                
                suggested_titles = json.loads(response)
                
                # Önerilen başlıkları uygula
                for suggestion in suggested_titles:
                    section_index = suggestion.get("section_index")
                    title = suggestion.get("suggested_title")
                    
                    if section_index is not None and title and 0 <= section_index < len(sections):
                        # Eğer zaten bir başlık yoksa veya önerilen başlık daha iyi ise uygula
                        if not sections[section_index].get("title") or len(sections[section_index].get("title", "")) < 3:
                            sections[section_index]["title"] = title
                            
                return sections
                
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning(f"LLM yanıtı ayrıştırma hatası: {str(e)}")
                return sections
                
        except Exception as e:
            logger.error(f"LLM ile bölüm iyileştirme hatası: {str(e)}")
            return sections

class HierarchicalChunker(SemanticChunker):
    """
    Hiyerarşik belge parçalama sınıfı.
    Belge yapısını koruyarak hiyerarşik parçalama yapar.
    """
    
    def __init__(
        self, 
        llm_service: Optional[LLMService] = None,
        config: Optional[ChunkingConfig] = None
    ):
        """
        Args:
            llm_service: LLM servisi
            config: Chunking yapılandırması
        """
        super().__init__(llm_service, config)
        
        # Hiyerarşik yapıyı koruma özelliğini aktifleştir
        if not self.config:
            self.config = ChunkingConfig()
        self.config.preserve_hierarchy = True
    
    def create_chunks(
        self, 
        text: str, 
        chunk_size: Optional[int] = None, 
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Metni hiyerarşik parçalara ayırır.
        
        Args:
            text: Parçalanacak metin
            chunk_size: Chunk boyutu
            chunk_overlap: Chunk örtüşmesi
            metadata: Belge meta verileri
            
        Returns:
            List[Chunk]: Oluşturulan chunk'lar
        """
        # Parametreleri ayarla
        chunk_size = chunk_size or self.config.chunk_size
        chunk_overlap = chunk_overlap or self.config.chunk_overlap
        metadata = metadata or {}
        
        # Boş metin kontrolü
        if not text or not text.strip():
            return []
        
        # Hiyerarşik yapıyı koru özelliği kapalıysa, semantik chunking kullan
        if not self.config.preserve_hierarchy:
            return super().create_chunks(text, chunk_size, chunk_overlap, metadata)
        
        # Belge yapısını analiz et
        document_structure = self._analyze_document_structure(text)
        
        # Hiyerarşik bölümleri bul
        hierarchical_sections = self._identify_hierarchical_sections(text, document_structure)
        
        # Bölümlerden chunk'lar oluştur
        chunks = []
        chunk_index = 0
        
        # Her ana bölüm için
        for section in hierarchical_sections:
            section_title = section.get("title", "")
            section_level = section.get("level", 0)
            section_text = section["text"]
            section_children = section.get("children", [])
            
            # Bölüm metni chunk boyutuna sığıyorsa, tek chunk olarak ekle
            if len(section_text) <= chunk_size:
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata["chunk_index"] = chunk_index
                chunk_metadata["section_title"] = section_title
                chunk_metadata["section_level"] = section_level
                
                # Tam hiyerarşik yolu ekle
                if section.get("path"):
                    chunk_metadata["section_path"] = section["path"]
                
                chunk_id = self._generate_chunk_id(section_text, chunk_metadata)
                
                chunk = Chunk(
                    id=chunk_id,
                    text=section_text,
                    metadata=chunk_metadata,
                    document_id=metadata.get("document_id") or metadata.get("id"),
                    chunk_index=chunk_index
                )
                
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Bölüm büyükse, alt bölümleri kontrol et
                if section_children:
                    # Alt bölümleri ayrı ayrı parçala
                    for child in section_children:
                        child_text = child["text"]
                        child_title = child.get("title", "")
                        child_level = child.get("level", section_level + 1)
                        
                        # Alt bölüm chunk'larını oluştur
                        child_chunks = self._chunk_section(
                            child_text, 
                            chunk_size, 
                            chunk_overlap,
                            {
                                **metadata,
                                "section_title": child_title,
                                "section_level": child_level,
                                "parent_section": section_title,
                                "section_path": child.get("path", [section_title, child_title])
                            },
                            chunk_index
                        )
                        
                        chunks.extend(child_chunks)
                        chunk_index += len(child_chunks)
                else:
                    # Alt bölüm yoksa, ana bölümü parçala
                    section_chunks = self._chunk_section(
                        section_text, 
                        chunk_size, 
                        chunk_overlap,
                        {
                            **metadata,
                            "section_title": section_title,
                            "section_level": section_level,
                            "section_path": section.get("path", [section_title])
                        },
                        chunk_index
                    )
                    
                    chunks.extend(section_chunks)
                    chunk_index += len(section_chunks)
        
        return chunks
    
    def _analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """
        Belge yapısını analiz eder.
        
        Args:
            text: Metin
            
        Returns:
            Dict[str, Any]: Belge yapısı analizi
        """
        structure = {
            "has_headers": False,
            "header_levels": set(),
            "header_pattern": None,
            "has_bullets": False,
            "bullet_pattern": None,
            "has_numbered_lists": False,
            "numbered_list_pattern": None,
            "avg_paragraph_length": 0,
            "max_paragraph_length": 0
        }
        
        # Markdown başlıkları kontrol et
        markdown_headers = re.findall(r'^(#+)\s+(.+)$', text, re.MULTILINE)
        if markdown_headers:
            structure["has_headers"] = True
            structure["header_levels"] = set(len(h[0]) for h in markdown_headers)
            structure["header_pattern"] = r'^(#+)\s+(.+)$'
        
        # HTML başlıkları kontrol et
        html_headers = re.findall(r'<h([1-6])>(.*?)</h\1>', text, re.DOTALL)
        if html_headers:
            structure["has_headers"] = True
            structure["header_levels"].update(int(h[0]) for h in html_headers)
            structure["header_pattern"] = r'<h([1-6])>(.*?)</h\1>'
        
        # Madde işaretleri kontrol et
        bullets = re.findall(r'^\s*[\*\-\+]\s+(.+)$', text, re.MULTILINE)
        if bullets:
            structure["has_bullets"] = True
            structure["bullet_pattern"] = r'^\s*[\*\-\+]\s+(.+)$'
        
        # Numaralı listeler kontrol et
        numbered_lists = re.findall(r'^\s*\d+\.\s+(.+)$', text, re.MULTILINE)
        if numbered_lists:
            structure["has_numbered_lists"] = True
            structure["numbered_list_pattern"] = r'^\s*\d+\.\s+(.+)$'
        
        # Paragraf uzunluklarını analiz et
        paragraphs = re.split(r'\n\s*\n', text)
        if paragraphs:
            paragraph_lengths = [len(p.strip()) for p in paragraphs if p.strip()]
            if paragraph_lengths:
                structure["avg_paragraph_length"] = sum(paragraph_lengths) / len(paragraph_lengths)
                structure["max_paragraph_length"] = max(paragraph_lengths)
        
        return structure
    
    def _identify_hierarchical_sections(
        self, 
        text: str, 
        structure: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Metindeki hiyerarşik bölümleri belirler.
        
        Args:
            text: Metin
            structure: Belge yapısı analizi
            
        Returns:
            List[Dict[str, Any]]: Hiyerarşik bölümler
        """
        # Önce semantik bölümleri bul
        semantic_sections = self._identify_semantic_sections(text)
        
        # Bölüm hiyerarşisini oluştur
        hierarchical_sections = []
        section_stack = []
        current_path = []
        
        for section in semantic_sections:
            section_level = section.get("level", 0)
            section_title = section.get("title", "")
            
            # Yol bilgisini ekle
            if section_title:
                while len(current_path) > 0 and len(current_path) >= section_level:
                    current_path.pop()
                current_path.append(section_title)
            
            section["path"] = current_path.copy()
            
            # Hiyerarşi oluştur
            while section_stack and section_stack[-1]["level"] >= section_level:
                section_stack.pop()
            
            if not section_stack:
                # Ana bölüm
                section["children"] = []
                hierarchical_sections.append(section)
                section_stack.append(section)
            else:
                # Alt bölüm
                parent = section_stack[-1]
                section["children"] = []
                parent["children"].append(section)
                section_stack.append(section)
        
        return hierarchical_sections
    
    def _chunk_section(
        self, 
        text: str, 
        chunk_size: int, 
        chunk_overlap: int,
        section_metadata: Dict[str, Any],
        start_index: int
    ) -> List[Chunk]:
        """
        Bir bölümü parçalara ayırır.
        
        Args:
            text: Bölüm metni
            chunk_size: Chunk boyutu
            chunk_overlap: Chunk örtüşmesi
            section_metadata: Bölüm meta verileri
            start_index: Başlangıç chunk indeksi
            
        Returns:
            List[Chunk]: Oluşturulan chunk'lar
        """
        # Metin uzunluğu chunk boyutundan küçükse, tek chunk olarak döndür
        if len(text) <= chunk_size:
            chunk_metadata = section_metadata.copy()
            chunk_metadata["chunk_index"] = start_index
            
            chunk_id = self._generate_chunk_id(text, chunk_metadata)
            
            chunk = Chunk(
                id=chunk_id,
                text=text,
                metadata=chunk_metadata,
                document_id=section_metadata.get("document_id") or section_metadata.get("id"),
                chunk_index=start_index
            )
            
            return [chunk]
        
        # Aksi halde, temel chunking algoritmasını kullan
        chunks = []
        start = 0
        chunk_index = start_index
        
        # Paragraf sınırlarını bul
        paragraph_breaks = [m.start() for m in re.finditer(r'\n\s*\n', text)]
        
        while start < len(text):
            # Son pozisyonu hesapla
            end = min(start + chunk_size, len(text))
            
            # Paragraf sınırında bitirmeye çalış
            if end < len(text):
                # Mevcut son pozisyonun ilerisindeki en yakın paragraf sonu bul
                next_break = next((pb for pb in paragraph_breaks if pb > start and pb < end), None)
                
                # Paragraf sonu varsa ve çok uzakta değilse orada kes
                if next_break and (next_break - start) >= self.config.min_chunk_size:
                    end = next_break
                else:
                    # Paragraf sonu yoksa, cümle sınırında bitirmeye çalış
                    sentence_end = text.rfind('.', start, end)
                    if sentence_end > start + self.config.min_chunk_size:
                        end = sentence_end + 1
            
            # Chunk içeriğini al
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                # Metadata oluştur
                chunk_metadata = section_metadata.copy()
                
                # Chunk bilgilerini ekle
                chunk_metadata["chunk_index"] = chunk_index
                chunk_metadata["chunk_start"] = start
                chunk_metadata["chunk_end"] = end
                
                # Bölüm başlığını her chunk'a ekle
                if not chunk_metadata.get("section_title") and section_metadata.get("section_title"):
                    chunk_metadata["section_title"] = section_metadata["section_title"]
                
                # Her chunk için, içerdiği bölüm yolunu da ekle (en üst düzey kontekstin korunması için)
                if "section_path" in section_metadata:
                    chunk_metadata["section_path"] = section_metadata["section_path"]
                
                # Chunk ID'si oluştur
                chunk_id = self._generate_chunk_id(chunk_text, chunk_metadata)
                
                # Chunk nesnesi oluştur
                chunk = Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    metadata=chunk_metadata,
                    document_id=section_metadata.get("document_id") or section_metadata.get("id"),
                    chunk_index=chunk_index
                )
                
                chunks.append(chunk)
                chunk_index += 1
            
            # Bir sonraki başlangıç pozisyonunu güncelle
            start = end - chunk_overlap
            
            # Negatif ilerlemeyi önle
            if start <= 0 or start >= len(text):
                break
        
        return chunks