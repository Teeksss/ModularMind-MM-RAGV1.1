"""
Prompt şablonu yönetim sistemi.
Yapılandırılabilir ve parametreli LLM promptları için merkezi bir yönetim sağlar.
"""

import logging
import time
import os
import json
from typing import List, Dict, Any, Optional, Union
import re
from enum import Enum
from dataclasses import dataclass
import jinja2

logger = logging.getLogger(__name__)

class PromptType(str, Enum):
    """Prompt türleri."""
    INSTRUCTION = "instruction"  # Yönerge promptu
    CHAT = "chat"                # Sohbet promptu
    RAG = "rag"                  # Retrieval-Augmented Generation promptu
    QA = "qa"                    # Soru-Cevap promptu
    SUMMARIZATION = "summarization"  # Özetleme promptu
    EXTRACTION = "extraction"    # Bilgi çıkarma promptu
    CLASSIFICATION = "classification"  # Sınıflandırma promptu
    CUSTOM = "custom"            # Özel prompt

@dataclass
class PromptTemplate:
    """Prompt şablonu."""
    id: str
    name: str
    description: str
    type: PromptType
    template: str
    default_parameters: Dict[str, Any]
    version: str
    tags: List[str]
    created_at: float
    updated_at: float
    created_by: str
    model_specific_versions: Optional[Dict[str, str]] = None
    examples: Optional[List[Dict[str, Any]]] = None
    is_active: bool = True

class PromptManager:
    """
    Prompt şablonu yönetim sistemi.
    """
    
    def __init__(self, db_manager=None, storage_path: str = None):
        """
        Args:
            db_manager: Veritabanı yöneticisi (isteğe bağlı)
            storage_path: Prompt depolama yolu (isteğe bağlı)
        """
        # Veritabanı bağlantısı
        if db_manager:
            self.db_manager = db_manager
            self.db = self.db_manager.get_database()
            self.prompt_collection = self.db["prompt_templates"]
            self.storage_mode = "database"
        elif storage_path:
            self.storage_path = storage_path
            os.makedirs(storage_path, exist_ok=True)
            self.storage_mode = "file"
        else:
            # Varsayılan olarak dosya depolaması
            self.storage_path = os.path.join(os.getcwd(), "prompts")
            os.makedirs(self.storage_path, exist_ok=True)
            self.storage_mode = "file"
        
        # Jinja2 ortamı
        self.env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Jinja2 filtrelerini ekle
        self._register_filters()
        
        # Prompt önbelleği
        self.prompt_cache = {}
        
        # İndeksleri oluştur
        if self.storage_mode == "database":
            self._create_indexes()
        
        logger.info(f"PromptManager başlatıldı: {self.storage_mode} modu")
    
    def _create_indexes(self):
        """Veritabanı indekslerini oluşturur."""
        if self.storage_mode != "database":
            return
        
        # İndeksler
        self.prompt_collection.create_index("id", unique=True)
        self.prompt_collection.create_index("name")
        self.prompt_collection.create_index("type")
        self.prompt_collection.create_index("tags")
        self.prompt_collection.create_index("created_by")
        self.prompt_collection.create_index("is_active")
    
    def _register_filters(self):
        """Jinja2 filtrelerini kaydeder."""
        # Metin formatlama
        self.env.filters['strip'] = lambda x: x.strip() if x else ''
        self.env.filters['title'] = lambda x: x.title() if x else ''
        self.env.filters['upper'] = lambda x: x.upper() if x else ''
        self.env.filters['lower'] = lambda x: x.lower() if x else ''
        self.env.filters['capitalize'] = lambda x: x.capitalize() if x else ''
        
        # Liste işlemleri
        self.env.filters['join'] = lambda x, sep: sep.join(x) if x else ''
        self.env.filters['first'] = lambda x: x[0] if x and len(x) > 0 else ''
        self.env.filters['last'] = lambda x: x[-1] if x and len(x) > 0 else ''
        
        # Özel filtreler
        self.env.filters['truncate'] = self._filter_truncate
        self.env.filters['format_json'] = self._filter_format_json
        self.env.filters['bullet_list'] = self._filter_bullet_list
    
    def _filter_truncate(self, text: str, length: int = 100, suffix: str = '...') -> str:
        """Metni belirli bir uzunlukta keser."""
        if not text:
            return ''
        if len(text) <= length:
            return text
        return text[:length].rstrip() + suffix
    
    def _filter_format_json(self, data: Any) -> str:
        """Veriyi JSON formatında döndürür."""
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except:
            return str(data)
    
    def _filter_bullet_list(self, items: List[str], bullet: str = '•') -> str:
        """Liste öğelerini madde işaretli liste olarak formatlar."""
        if not items:
            return ''
        return '\n'.join(f"{bullet} {item}" for item in items)
    
    def create_template(self, template: PromptTemplate) -> str:
        """
        Yeni bir prompt şablonu oluşturur.
        
        Args:
            template: Oluşturulacak şablon
            
        Returns:
            str: Oluşturulan şablonun ID'si
        """
        # ID kontrolü
        if not template.id:
            from uuid import uuid4
            template.id = str(uuid4())
        
        # Zaman damgaları
        current_time = time.time()
        template.created_at = current_time
        template.updated_at = current_time
        
        # Şablonu kaydet
        if self.storage_mode == "database":
            # MongoDB'ye kaydet
            template_dict = template.__dict__
            self.prompt_collection.insert_one(template_dict)
        else:
            # Dosya olarak kaydet
            file_path = os.path.join(self.storage_path, f"{template.id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template.__dict__, f, ensure_ascii=False, indent=2)
        
        # Önbelleğe ekle
        self.prompt_cache[template.id] = template
        
        logger.info(f"Prompt şablonu oluşturuldu: {template.id} - {template.name}")
        return template.id
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        Belirli bir prompt şablonunu getirir.
        
        Args:
            template_id: Şablon ID'si
            
        Returns:
            Optional[PromptTemplate]: Prompt şablonu veya bulunamazsa None
        """
        # Önbellekte kontrol et
        if template_id in self.prompt_cache:
            return self.prompt_cache[template_id]
        
        template_data = None
        
        # Şablonu getir
        if self.storage_mode == "database":
            # MongoDB'den getir
            doc = self.prompt_collection.find_one({"id": template_id})
            if doc:
                # _id alanını kaldır
                if '_id' in doc:
                    del doc['_id']
                template_data = doc
        else:
            # Dosyadan getir
            file_path = os.path.join(self.storage_path, f"{template_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
        
        if template_data:
            # PromptTemplate nesnesine dönüştür
            template = PromptTemplate(**template_data)
            
            # Önbelleğe ekle
            self.prompt_cache[template_id] = template
            
            return template
        
        return None
    
    def update_template(self, template: PromptTemplate) -> bool:
        """
        Prompt şablonunu günceller.
        
        Args:
            template: Güncellenecek şablon
            
        Returns:
            bool: Başarılı ise True
        """
        # Mevcut şablonu kontrol et
        existing = self.get_template(template.id)
        if not existing:
            logger.error(f"Güncellenecek şablon bulunamadı: {template.id}")
            return False
        
        # Değiştirilemeyen alanları koru
        template.created_at = existing.created_at
        template.created_by = existing.created_by
        
        # Güncelleme zamanını ayarla
        template.updated_at = time.time()
        
        # Şablonu güncelle
        if self.storage_mode == "database":
            # MongoDB'de güncelle
            template_dict = template.__dict__
            result = self.prompt_collection.replace_one({"id": template.id}, template_dict)
            success = result.modified_count > 0
        else:
            # Dosyayı güncelle
            file_path = os.path.join(self.storage_path, f"{template.id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template.__dict__, f, ensure_ascii=False, indent=2)
            success = True
        
        # Önbelleği güncelle
        if success:
            self.prompt_cache[template.id] = template
            logger.info(f"Prompt şablonu güncellendi: {template.id}")
        
        return success
    
    def delete_template(self, template_id: str) -> bool:
        """
        Prompt şablonunu siler.
        
        Args:
            template_id: Silinecek şablon ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        # Şablonu kontrol et
        if not self.get_template(template_id):
            logger.error(f"Silinecek şablon bulunamadı: {template_id}")
            return False
        
        # Şablonu sil
        if self.storage_mode == "database":
            # MongoDB'den sil
            result = self.prompt_collection.delete_one({"id": template_id})
            success = result.deleted_count > 0
        else:
            # Dosyayı sil
            file_path = os.path.join(self.storage_path, f"{template_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                success = True
            else:
                success = False
        
        # Önbellekten kaldır
        if success and template_id in self.prompt_cache:
            del self.prompt_cache[template_id]
            logger.info(f"Prompt şablonu silindi: {template_id}")
        
        return success
    
    def list_templates(
        self,
        type_filter: Optional[PromptType] = None,
        tag_filter: Optional[List[str]] = None,
        creator_filter: Optional[str] = None,
        active_only: bool = True
    ) -> List[PromptTemplate]:
        """
        Prompt şablonlarını listeler.
        
        Args:
            type_filter: Türe göre filtreleme
            tag_filter: Etiketlere göre filtreleme
            creator_filter: Oluşturan kişiye göre filtreleme
            active_only: Sadece aktif şablonlar
            
        Returns:
            List[PromptTemplate]: Şablonlar listesi
        """
        templates = []
        
        if self.storage_mode == "database":
            # MongoDB sorgusu
            query = {}
            
            if type_filter:
                query["type"] = type_filter.value if isinstance(type_filter, PromptType) else type_filter
            
            if tag_filter:
                query["tags"] = {"$all": tag_filter}
            
            if creator_filter:
                query["created_by"] = creator_filter
            
            if active_only:
                query["is_active"] = True
            
            # Sorguyu çalıştır
            cursor = self.prompt_collection.find(query).sort("name", 1)
            
            for doc in cursor:
                # _id alanını kaldır
                if '_id' in doc:
                    del doc['_id']
                
                # PromptTemplate nesnesine dönüştür
                template = PromptTemplate(**doc)
                templates.append(template)
        else:
            # Dosyalardan yükle
            for filename in os.listdir(self.storage_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.storage_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    # Filtreleme
                    if type_filter and template_data.get("type") != (type_filter.value if isinstance(type_filter, PromptType) else type_filter):
                        continue
                    
                    if tag_filter and not all(tag in template_data.get("tags", []) for tag in tag_filter):
                        continue
                    
                    if creator_filter and template_data.get("created_by") != creator_filter:
                        continue
                    
                    if active_only and not template_data.get("is_active", True):
                        continue
                    
                    # PromptTemplate nesnesine dönüştür
                    template = PromptTemplate(**template_data)
                    templates.append(template)
        
        # Ad sırasına göre sırala
        templates.sort(key=lambda t: t.name)
        
        return templates
    
    def render_prompt(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        model_name: Optional[str] = None
    ) -> str:
        """
        Parametre değerleriyle prompt şablonunu render eder.
        
        Args:
            template_id: Şablon ID'si
            parameters: Parametre değerleri
            model_name: Belirli bir model için özel şablon (isteğe bağlı)
            
        Returns:
            str: Render edilmiş prompt
        """
        # Şablonu getir
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Şablon bulunamadı: {template_id}")
        
        # Varsayılan parametreleri kullan ve özel parametrelerle güncelle
        context = template.default_parameters.copy()
        context.update(parameters)
        
        # Modele özgü şablon kontrol et
        template_text = template.template
        if model_name and template.model_specific_versions and model_name in template.model_specific_versions:
            template_text = template.model_specific_versions[model_name]
        
        # Jinja2 şablonunu render et
        try:
            jinja_template = self.env.from_string(template_text)
            result = jinja_template.render(**context)
            return result
        except Exception as e:
            logger.error(f"Prompt render hatası: {str(e)}")
            raise ValueError(f"Prompt render hatası: {str(e)}")
    
    def render_chat_prompt(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        model_name: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Sohbet formatında şablonu render eder.
        
        Args:
            template_id: Şablon ID'si
            parameters: Parametre değerleri
            model_name: Belirli bir model için özel şablon (isteğe bağlı)
            
        Returns:
            List[Dict[str, str]]: Sohbet mesajları formatında render edilmiş prompt
        """
        # Şablonu getir
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Şablon bulunamadı: {template_id}")
        
        # Sohbet şablonu kontrolü
        if template.type != PromptType.CHAT:
            raise ValueError(f"Şablon türü 'chat' olmalı, şu an: {template.type}")
        
        # Varsayılan parametreleri kullan ve özel parametrelerle güncelle
        context = template.default_parameters.copy()
        context.update(parameters)
        
        # Modele özgü şablon kontrol et
        template_text = template.template
        if model_name and template.model_specific_versions and model_name in template.model_specific_versions:
            template_text = template.model_specific_versions[model_name]
        
        try:
            # Jinja2 şablonunu render et
            jinja_template = self.env.from_string(template_text)
            result = jinja_template.render(**context)
            
            # JSON olarak parse et
            chat_messages = json.loads(result)
            
            # Format kontrolü
            if not isinstance(chat_messages, list):
                raise ValueError("Chat şablonu mesaj listesi döndürmelidir")
            
            for msg in chat_messages:
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    raise ValueError("Her mesaj 'role' ve 'content' alanları içermelidir")
            
            return chat_messages
            
        except json.JSONDecodeError:
            logger.error("Chat şablonu geçerli bir JSON formatında olmalıdır")
            raise ValueError("Chat şablonu geçerli bir JSON formatında olmalıdır")
        except Exception as e:
            logger.error(f"Chat prompt render hatası: {str(e)}")
            raise ValueError(f"Chat prompt render hatası: {str(e)}")
    
    def validate_template(self, template: PromptTemplate) -> Dict[str, List[str]]:
        """
        Prompt şablonunu doğrular.
        
        Args:
            template: Doğrulanacak şablon
            
        Returns:
            Dict[str, List[str]]: Doğrulama hataları (boş ise geçerli)
        """
        errors = {}
        
        # Zorunlu alanları kontrol et
        required_fields = ["id", "name", "template", "type"]
        for field in required_fields:
            value = getattr(template, field, None)
            if not value:
                if "required" not in errors:
                    errors["required"] = []
                errors["required"].append(f"'{field}' alanı zorunludur")
        
        # Şablon içinde parametre kullanımını kontrol et
        if hasattr(template, "template") and template.template:
            try:
                # Jinja2 şablonunu ayrıştır
                jinja_template = self.env.parse(template.template)
                
                # Şablonda kullanılan değişkenleri çıkar
                variables = self._extract_template_variables(jinja_template)
                
                # Varsayılan parametrelerde tanımlı olmayanları bul
                missing_params = []
                if variables:
                    for var in variables:
                        if not template.default_parameters or var not in template.default_parameters:
                            missing_params.append(var)
                
                if missing_params:
                    errors["parameters"] = [f"Şablonda kullanılan ancak varsayılan değeri olmayan parametreler: {', '.join(missing_params)}"]
                
            except jinja2.exceptions.TemplateSyntaxError as e:
                errors["syntax"] = [f"Şablon sözdizimi hatası: {str(e)}"]
        
        # Tür kontrolü
        if hasattr(template, "type") and template.type:
            try:
                template_type = template.type
                if isinstance(template_type, str):
                    PromptType(template_type)
            except ValueError:
                errors["type"] = [f"Geçersiz şablon türü: {template.type}. Geçerli türler: {', '.join([t.value for t in PromptType])}"]
        
        # Model specifik şablonların kontrolü
        if template.model_specific_versions:
            for model, model_template in template.model_specific_versions.items():
                try:
                    # Şablonu ayrıştır
                    self.env.parse(model_template)
                except jinja2.exceptions.TemplateSyntaxError as e:
                    if "syntax" not in errors:
                        errors["syntax"] = []
                    errors["syntax"].append(f"Model şablonu sözdizimi hatası ({model}): {str(e)}")
        
        # Chat türü için özel kontrol
        if template.type == PromptType.CHAT or template.type == "chat":
            try:
                # Örnek parametrelerle render edip JSON formatını kontrol et
                sample_context = template.default_parameters.copy()
                jinja_template = self.env.from_string(template.template)
                result = jinja_template.render(**sample_context)
                
                # JSON olarak parse et
                chat_messages = json.loads(result)
                
                # Format kontrolü
                if not isinstance(chat_messages, list):
                    if "format" not in errors:
                        errors["format"] = []
                    errors["format"].append("Chat şablonu mesaj listesi döndürmelidir")
                else:
                    for idx, msg in enumerate(chat_messages):
                        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                            if "format" not in errors:
                                errors["format"] = []
                            errors["format"].append(f"Mesaj {idx+1}: Her mesaj 'role' ve 'content' alanları içermelidir")
                
            except (json.JSONDecodeError, jinja2.exceptions.TemplateError):
                if "format" not in errors:
                    errors["format"] = []
                errors["format"].append("Chat şablonu geçerli bir JSON formatında olmalıdır")
            except Exception as e:
                if "format" not in errors:
                    errors["format"] = []
                errors["format"].append(f"Chat şablonu kontrol hatası: {str(e)}")
        
        return errors
    
    def _extract_template_variables(self, parsed_template) -> List[str]:
        """Jinja2 şablonundaki değişkenleri çıkarır."""
        variables = set()
        
        def visit_node(node):
            if isinstance(node, jinja2.nodes.Name):
                variables.add(node.name)
            elif isinstance(node, jinja2.nodes.Getattr):
                # x.y yapısındaki değişkenleri ele al
                current = node
                parts = []
                while isinstance(current, jinja2.nodes.Getattr):
                    parts.append(current.attr)
                    current = current.node
                if isinstance(current, jinja2.nodes.Name):
                    parts.append(current.name)
                    variables.add(parts[-1])  # Ana değişkeni ekle
            
            for child in node.iter_child_nodes():
                visit_node(child)
        
        visit_node(parsed_template)
        return list(variables)
    
    def export_templates(self, templates: List[PromptTemplate], format: str = "json") -> str:
        """
        Prompt şablonlarını dışa aktarır.
        
        Args:
            templates: Dışa aktarılacak şablonlar
            format: Dışa aktarma formatı ("json" veya "yaml")
            
        Returns:
            str: Dışa aktarılan veri
        """
        if format.lower() == "json":
            # JSON formatında dışa aktar
            export_data = []
            for template in templates:
                export_data.append(template.__dict__)
            
            return json.dumps(export_data, ensure_ascii=False, indent=2)
        
        elif format.lower() == "yaml":
            try:
                import yaml
                
                # YAML formatında dışa aktar
                export_data = []
                for template in templates:
                    export_data.append(template.__dict__)
                
                return yaml.dump(export_data, allow_unicode=True, sort_keys=False)
                
            except ImportError:
                logger.error("YAML dışa aktarımı için 'pyyaml' kütüphanesi gerekli")
                raise ImportError("YAML dışa aktarımı için 'pyyaml' kütüphanesi gerekli")
        
        else:
            raise ValueError(f"Desteklenmeyen format: {format}")
    
    def import_templates(self, data: str, format: str = "json", overwrite: bool = False) -> Dict[str, Any]:
        """
        Prompt şablonlarını içe aktarır.
        
        Args:
            data: İçe aktarılacak veri
            format: Veri formatı ("json" veya "yaml")
            overwrite: Mevcut şablonları üzerine yaz
            
        Returns:
            Dict[str, Any]: İçe aktarma sonuçları
        """
        templates = []
        
        try:
            if format.lower() == "json":
                # JSON formatından içe aktar
                templates_data = json.loads(data)
                
            elif format.lower() == "yaml":
                try:
                    import yaml
                    # YAML formatından içe aktar
                    templates_data = yaml.safe_load(data)
                except ImportError:
                    logger.error("YAML içe aktarımı için 'pyyaml' kütüphanesi gerekli")
                    raise ImportError("YAML içe aktarımı için 'pyyaml' kütüphanesi gerekli")
            else:
                raise ValueError(f"Desteklenmeyen format: {format}")
            
            # Geçerli bir liste kontrolü
            if not isinstance(templates_data, list):
                return {"success": False, "error": "Veri geçerli bir şablon listesi içermiyor"}
            
            # Her şablonu doğrula ve ekle
            results = {
                "total": len(templates_data),
                "imported": 0,
                "skipped": 0,
                "errors": []
            }
            
            for template_data in templates_data:
                try:
                    # PromptTemplate nesnesine dönüştür
                    template = PromptTemplate(**template_data)
                    
                    # Şablonu doğrula
                    validation_errors = self.validate_template(template)
                    
                    if validation_errors:
                        error_msg = f"Şablon doğrulama hatası ({template.id}): {validation_errors}"
                        results["errors"].append(error_msg)
                        results["skipped"] += 1
                        continue
                    
                    # Mevcut şablon kontrolü
                    existing = self.get_template(template.id)
                    
                    if existing and not overwrite:
                        results["skipped"] += 1
                        continue
                    
                    # Şablonu ekle veya güncelle
                    if existing:
                        self.update_template(template)
                    else:
                        self.create_template(template)
                    
                    results["imported"] += 1
                    
                except Exception as e:
                    error_msg = f"Şablon içe aktarma hatası: {str(e)}"
                    results["errors"].append(error_msg)
                    results["skipped"] += 1
            
            results["success"] = results["imported"] > 0
            return results
            
        except Exception as e:
            logger.error(f"Şablon içe aktarma hatası: {str(e)}")
            return {"success": False, "error": str(e)}