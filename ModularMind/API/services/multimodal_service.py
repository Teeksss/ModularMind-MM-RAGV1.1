"""
Multimodal içerik işleme servisi.
Görüntü, video ve ses içeriklerinin işlenmesi, analizi ve saklanması için fonksiyonlar sağlar.
"""

import os
import time
import logging
import json
import uuid
import shutil
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio

# Görüntü işleme kütüphaneleri
import numpy as np
from PIL import Image
import cv2

# ML kütüphaneleri
try:
    import torch
    from transformers import CLIPProcessor, CLIPModel, AutoFeatureExtractor, AutoModelForImageClassification
    import whisper
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Veritabanı bağlantısı
from ModularMind.API.db.base import DatabaseManager

logger = logging.getLogger(__name__)

class ContentType(str, Enum):
    """İçerik türleri."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

class MultimodalProcessor:
    """
    Multimodal içerik işleme sınıfı.
    """
    
    def __init__(self):
        """Initialize the multimodal processor."""
        # Veritabanı bağlantısı
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.get_database()
        
        # Koleksiyonlar
        self.content_collection = self.db["multimodal_contents"]
        self.embedding_collection = self.db["multimodal_embeddings"]
        
        # Depolama yolları
        self.storage_root = os.getenv("MULTIMODAL_STORAGE_PATH", "multimodal_data")
        self.image_dir = os.path.join(self.storage_root, "images")
        self.video_dir = os.path.join(self.storage_root, "videos")
        self.audio_dir = os.path.join(self.storage_root, "audios")
        self.preview_dir = os.path.join(self.storage_root, "previews")
        
        # Dizinleri oluştur
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.preview_dir, exist_ok=True)
        
        # ML modelleri
        self.models = {}
        
        # İndeksler oluştur
        self._create_indexes()
    
    def _create_indexes(self):
        """Veritabanı indekslerini oluştur."""
        try:
            # İçerik koleksiyonu indeksleri
            self.content_collection.create_index("user_id")
            self.content_collection.create_index("content_type")
            self.content_collection.create_index([("user_id", 1), ("content_type", 1)])
            self.content_collection.create_index("created_at")
            
            # Embedding koleksiyonu indeksleri
            self.embedding_collection.create_index("content_id")
            self.embedding_collection.create_index("user_id")
            
            logger.info("Multimodal veritabanı indeksleri başarıyla oluşturuldu")
        except Exception as e:
            logger.error(f"Veritabanı indeksleri oluşturulurken hata: {str(e)}")
    
    def _load_image_model(self, model_type="clip"):
        """
        Görüntü işleme modelini yükle.
        
        Args:
            model_type: Model türü (clip, classification)
            
        Returns:
            tuple: Model ve işleyici
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch ve Transformers kütüphaneleri bulunamadı. Görüntü modeli yüklenemiyor.")
            return None, None
        
        if model_type == "clip" and "clip" not in self.models:
            try:
                model_name = "openai/clip-vit-base-patch32"
                processor = CLIPProcessor.from_pretrained(model_name)
                model = CLIPModel.from_pretrained(model_name)
                self.models["clip"] = (model, processor)
                logger.info(f"CLIP modeli yüklendi: {model_name}")
            except Exception as e:
                logger.error(f"CLIP modeli yüklenirken hata: {str(e)}")
                return None, None
        
        elif model_type == "classification" and "classification" not in self.models:
            try:
                model_name = "google/vit-base-patch16-224"
                processor = AutoFeatureExtractor.from_pretrained(model_name)
                model = AutoModelForImageClassification.from_pretrained(model_name)
                self.models["classification"] = (model, processor)
                logger.info(f"Sınıflandırma modeli yüklendi: {model_name}")
            except Exception as e:
                logger.error(f"Sınıflandırma modeli yüklenirken hata: {str(e)}")
                return None, None
        
        return self.models.get(model_type, (None, None))
    
    def _load_audio_model(self):
        """
        Ses işleme modelini yükle.
        
        Returns:
            whisper.Model: Whisper modeli
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch ve Whisper kütüphaneleri bulunamadı. Ses modeli yüklenemiyor.")
            return None
        
        if "whisper" not in self.models:
            try:
                model = whisper.load_model("base")
                self.models["whisper"] = model
                logger.info("Whisper ses modeli yüklendi")
                return model
            except Exception as e:
                logger.error(f"Whisper modeli yüklenirken hata: {str(e)}")
                return None
        
        return self.models.get("whisper")
    
    def process_and_store(self, file_path: str, content_type: ContentType, user_id: str, metadata: Dict[str, Any]) -> str:
        """
        İçeriği işle ve veritabanına kaydet.
        
        Args:
            file_path: Dosya yolu
            content_type: İçerik türü
            user_id: Kullanıcı ID'si
            metadata: Meta veriler
            
        Returns:
            str: İçerik ID'si
        """
        try:
            # İçerik ID'si oluştur
            content_id = str(uuid.uuid4())
            
            # Dosya adını al
            filename = os.path.basename(file_path)
            
            # Hedef dizini belirle
            if content_type == ContentType.IMAGE:
                target_dir = self.image_dir
            elif content_type == ContentType.VIDEO:
                target_dir = self.video_dir
            elif content_type == ContentType.AUDIO:
                target_dir = self.audio_dir
            else:
                raise ValueError(f"Desteklenmeyen içerik türü: {content_type}")
            
            # Benzersiz bir dosya adı oluştur
            ext = filename.split('.')[-1] if '.' in filename else ''
            unique_filename = f"{content_id}.{ext}"
            target_path = os.path.join(target_dir, unique_filename)
            
            # Dosyayı hedef dizine kopyala
            shutil.copy2(file_path, target_path)
            
            # Önizleme oluştur
            preview_path = None
            if content_type == ContentType.IMAGE:
                preview_path = self._create_image_preview(target_path, content_id)
            elif content_type == ContentType.VIDEO:
                preview_path = self._create_video_preview(target_path, content_id)
            
            # Veritabanına kaydet
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            content_data = {
                "id": content_id,
                "user_id": user_id,
                "content_type": content_type.value,
                "filename": filename,
                "storage_path": target_path,
                "preview_path": preview_path,
                "metadata": metadata,
                "status": "pending",  # pending, analyzed, failed
                "created_at": current_time,
                "updated_at": current_time,
                "analysis_result": None,
                "caption": None,
                "tags": metadata.get("tags", [])
            }
            
            self.content_collection.insert_one(content_data)
            logger.info(f"İçerik başarıyla kaydedildi: {content_id}")
            
            return content_id
            
        except Exception as e:
            logger.error(f"İçerik işleme hatası: {str(e)}")
            raise e
    
    def _create_image_preview(self, image_path: str, content_id: str) -> Optional[str]:
        """
        Görüntü için önizleme oluştur.
        
        Args:
            image_path: Görüntü dosyası yolu
            content_id: İçerik ID'si
            
        Returns:
            Optional[str]: Önizleme dosyasının yolu
        """
        try:
            # Görüntüyü aç
            img = Image.open(image_path)
            
            # Boyutları hesapla
            max_size = 300
            width, height = img.size
            
            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            
            # Yeniden boyutlandır
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Önizleme dosyası yolu
            preview_filename = f"{content_id}_preview.jpg"
            preview_path = os.path.join(self.preview_dir, preview_filename)
            
            # JPEG olarak kaydet
            img.convert("RGB").save(preview_path, "JPEG", quality=80)
            
            return preview_path
        except Exception as e:
            logger.error(f"Görüntü önizleme oluşturma hatası: {str(e)}")
            return None
    
    def _create_video_preview(self, video_path: str, content_id: str) -> Optional[str]:
        """
        Video için önizleme (thumbnail) oluştur.
        
        Args:
            video_path: Video dosyası yolu
            content_id: İçerik ID'si
            
        Returns:
            Optional[str]: Önizleme dosyasının yolu
        """
        try:
            # OpenCV ile videoyu aç
            cap = cv2.VideoCapture(video_path)
            
            # Başarılı bir şekilde açıldı mı kontrol et
            if not cap.isOpened():
                logger.error(f"Video açılamadı: {video_path}")
                return None
            
            # Video özelliklerini al
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Ortadaki kareyi al
            middle_frame_idx = frame_count // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                logger.error(f"Video karesi okunamadı: {video_path}")
                cap.release()
                return None
            
            # Kareyi boyutlandır
            max_size = 300
            height, width = frame.shape[:2]
            
            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Önizleme dosyası yolu
            preview_filename = f"{content_id}_preview.jpg"
            preview_path = os.path.join(self.preview_dir, preview_filename)
            
            # JPEG olarak kaydet
            cv2.imwrite(preview_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Kaynakları serbest bırak
            cap.release()
            
            return preview_path
        except Exception as e:
            logger.error(f"Video önizleme oluşturma hatası: {str(e)}")
            return None
    
    def analyze_content(self, content_id: str, content_type: ContentType, force: bool = False) -> Dict[str, Any]:
        """
        İçeriği analiz et.
        
        Args:
            content_id: İçerik ID'si
            content_type: İçerik türü
            force: Mevcut analizi geçersiz kılarak yeniden analiz et
            
        Returns:
            Dict[str, Any]: Analiz sonuçları
        """
        try:
            # İçeriği getir
            content = self.content_collection.find_one({"id": content_id})
            
            if not content:
                logger.error(f"İçerik bulunamadı: {content_id}")
                return {"error": "İçerik bulunamadı"}
            
            # Zaten analiz edilmiş ve force = False ise analizi atla
            if content.get("status") == "analyzed" and not force:
                logger.info(f"İçerik zaten analiz edilmiş: {content_id}")
                return content.get("analysis_result", {})
            
            # Dosya yolunu al
            file_path = content.get("storage_path")
            
            if not file_path or not os.path.exists(file_path):
                logger.error(f"İçerik dosyası bulunamadı: {file_path}")
                return {"error": "İçerik dosyası bulunamadı"}
            
            # İçerik türüne göre analiz et
            analysis_result = {}
            caption = None
            
            if content_type == ContentType.IMAGE:
                analysis_result, caption = self._analyze_image(file_path)
            elif content_type == ContentType.VIDEO:
                analysis_result, caption = self._analyze_video(file_path)
            elif content_type == ContentType.AUDIO:
                analysis_result, caption = self._analyze_audio(file_path)
            
            # Analiz sonuçlarını veritabanına kaydet
            update_data = {
                "status": "analyzed",
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "analysis_result": analysis_result,
                "caption": caption
            }
            
            self.content_collection.update_one(
                {"id": content_id},
                {"$set": update_data}
            )
            
            logger.info(f"İçerik analizi tamamlandı: {content_id}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"İçerik analiz hatası: {str(e)}")
            
            # Hata durumunu veritabanına kaydet
            try:
                self.content_collection.update_one(
                    {"id": content_id},
                    {"$set": {
                        "status": "failed",
                        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "analysis_result": {"error": str(e)}
                    }}
                )
            except Exception as db_error:
                logger.error(f"Veritabanı güncelleme hatası: {str(db_error)}")
            
            raise e
    
    def _analyze_image(self, image_path: str) -> Tuple[Dict[str, Any], str]:
        """
        Görüntüyü analiz et.
        
        Args:
            image_path: Görüntü dosyası yolu
            
        Returns:
            Tuple[Dict[str, Any], str]: Analiz sonuçları ve başlık
        """
        try:
            # CLIP modelini yükle
            model, processor = self._load_image_model("clip")
            
            if not model or not processor:
                return {"error": "CLIP modeli yüklenemedi"}, None
            
            # Görüntüyü yükle
            image = Image.open(image_path).convert("RGB")
            
            # CLIP ile görüntüyü işle
            inputs = processor(
                text=["a photo of a landscape", "a photo of a person", "a photo of an object", "a photo of an animal", "a photo of food"],
                images=image, 
                return_tensors="pt", 
                padding=True
            )
            
            # CLIP model çıktısını al
            with torch.no_grad():
                outputs = model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Kategorileri ve olasılıkları al
            categories = ["landscape", "person", "object", "animal", "food"]
            probabilities = probs[0].tolist()
            
            # Temel analiz sonuçları
            analysis_result = {
                "categories": [
                    {"name": category, "probability": prob}
                    for category, prob in zip(categories, probabilities)
                ],
                "dominant_category": categories[probabilities.index(max(probabilities))],
                "confidence": max(probabilities)
            }
            
            # Görüntü özelliklerini çıkar
            image_features = self._extract_image_features(image, model, processor)
            analysis_result["features"] = image_features
            
            # Başlık oluştur
            caption = f"A {analysis_result['dominant_category']} with {analysis_result['confidence']:.2f} confidence"
            
            return analysis_result, caption
            
        except Exception as e:
            logger.error(f"Görüntü analiz hatası: {str(e)}")
            return {"error": str(e)}, None
    
    def _extract_image_features(self, image: Image.Image, model, processor) -> Dict[str, Any]:
        """
        Görüntü özelliklerini çıkar.
        
        Args:
            image: PIL görüntüsü
            model: Model nesnesi
            processor: İşlemci nesnesi
            
        Returns:
            Dict[str, Any]: Görüntü özellikleri
        """
        # Temel görüntü özellikleri
        width, height = image.size
        aspect_ratio = width / height
        
        # Renk analizi
        try:
            # Ortalama renk
            rgb_img = image.convert('RGB')
            rgb_data = np.array(rgb_img)
            avg_color = rgb_data.mean(axis=(0, 1)).astype(int).tolist()
            
            # Histogram
            hist_r, _ = np.histogram(rgb_data[:, :, 0].flatten(), bins=8, range=(0, 256))
            hist_g, _ = np.histogram(rgb_data[:, :, 1].flatten(), bins=8, range=(0, 256))
            hist_b, _ = np.histogram(rgb_data[:, :, 2].flatten(), bins=8, range=(0, 256))
            
            color_features = {
                "average_color": avg_color,
                "histogram": {
                    "r": hist_r.tolist(),
                    "g": hist_g.tolist(),
                    "b": hist_b.tolist()
                }
            }
        except Exception as e:
            logger.error(f"Renk analizi hatası: {str(e)}")
            color_features = {"error": str(e)}
        
        # Görüntü embedding'i
        try:
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = model.get_image_features(**inputs)
                embedding = outputs.detach().numpy().mean(axis=0).tolist()
        except Exception as e:
            logger.error(f"Embedding çıkarma hatası: {str(e)}")
            embedding = []
        
        return {
            "dimensions": {"width": width, "height": height},
            "aspect_ratio": aspect_ratio,
            "color": color_features,
            "embedding_size": len(embedding),
            "embedding_sample": embedding[:10] if embedding else []  # Tam embedding çok büyük olabilir
        }
    
    def _analyze_video(self, video_path: str) -> Tuple[Dict[str, Any], str]:
        """
        Videoyu analiz et.
        
        Args:
            video_path: Video dosyası yolu
            
        Returns:
            Tuple[Dict[str, Any], str]: Analiz sonuçları ve başlık
        """
        try:
            # OpenCV ile videoyu aç
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {"error": "Video açılamadı"}, None
            
            # Video özelliklerini al
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Anahtar kareleri al
            keyframes = []
            keyframe_features = []
            
            model, processor = self._load_image_model("clip")
            
            if model and processor:
                # 10 anahtar kare veya toplam kare sayısı daha azsa tüm kareler
                num_keyframes = min(10, frame_count)
                if num_keyframes > 0:
                    keyframe_indices = [int(i * (frame_count - 1) / (num_keyframes - 1)) for i in range(num_keyframes)]
                    
                    for idx in keyframe_indices:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                        ret, frame = cap.read()
                        
                        if ret:
                            # OpenCV BGR'dan PIL RGB'ye dönüştür
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            pil_frame = Image.fromarray(frame_rgb)
                            
                            # Kareyi analiz et
                            try:
                                # CLIP ile görüntüyü işle
                                inputs = processor(
                                    text=["a video of a landscape", "a video of a person", "a video of an object", "a video of an animal", "a video of an activity"],
                                    images=pil_frame, 
                                    return_tensors="pt", 
                                    padding=True
                                )
                                
                                with torch.no_grad():
                                    outputs = model(**inputs)
                                    logits_per_image = outputs.logits_per_image
                                    probs = logits_per_image.softmax(dim=1)
                                
                                # Kategorileri ve olasılıkları al
                                categories = ["landscape", "person", "object", "animal", "activity"]
                                probabilities = probs[0].tolist()
                                
                                keyframe_features.append({
                                    "frame_index": idx,
                                    "timestamp": idx / fps,
                                    "dominant_category": categories[probabilities.index(max(probabilities))],
                                    "confidence": max(probabilities)
                                })
                                
                                keyframes.append(idx)
                            except Exception as e:
                                logger.error(f"Kare analiz hatası: {str(e)}")
            
            # Analiz sonuçları
            analysis_result = {
                "video_properties": {
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "frame_count": frame_count,
                    "duration_seconds": duration
                },
                "keyframes": keyframe_features
            }
            
            # Baskın içerik türünü belirle
            if keyframe_features:
                category_counts = {}
                for kf in keyframe_features:
                    cat = kf["dominant_category"]
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                
                dominant_category = max(category_counts.items(), key=lambda x: x[1])[0]
                analysis_result["dominant_category"] = dominant_category
            else:
                analysis_result["dominant_category"] = "unknown"
            
            # Kaynakları serbest bırak
            cap.release()
            
            # Başlık oluştur
            duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
            caption = f"A {analysis_result['dominant_category']} video ({duration_str})"
            
            return analysis_result, caption
            
        except Exception as e:
            logger.error(f"Video analiz hatası: {str(e)}")
            return {"error": str(e)}, None
    
    def _analyze_audio(self, audio_path: str) -> Tuple[Dict[str, Any], str]:
        """
        Ses dosyasını analiz et.
        
        Args:
            audio_path: Ses dosyası yolu
            
        Returns:
            Tuple[Dict[str, Any], str]: Analiz sonuçları ve başlık
        """
        try:
            # Whisper modelini yükle
            model = self._load_audio_model()
            
            if not model:
                return {"error": "Whisper modeli yüklenemedi"}, None
            
            # Ses tanıma
            result = model.transcribe(audio_path)
            
            transcript = result["text"]
            language = result.get("language", "unknown")
            segments = result.get("segments", [])
            
            # Segment bilgilerini çıkar
            processed_segments = []
            for segment in segments:
                processed_segments.append({
                    "id": segment.get("id", 0),
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", ""),
                    "confidence": segment.get("confidence", 0)
                })
            
            # Analiz sonuçları
            analysis_result = {
                "transcript": transcript,
                "language": language,
                "segments": processed_segments,
                "duration_seconds": segments[-1]["end"] if segments else 0
            }
            
            # Başlık oluştur
            if transcript:
                # Kısa bir başlık
                caption = transcript[:100] + ("..." if len(transcript) > 100 else "")
            else:
                caption = f"Audio in {language}"
            
            return analysis_result, caption
            
        except Exception as e:
            logger.error(f"Ses analiz hatası: {str(e)}")
            return {"error": str(e)}, None
    
    def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        İçerik detaylarını getir.
        
        Args:
            content_id: İçerik ID'si
            
        Returns:
            Optional[Dict[str, Any]]: İçerik detayları
        """
        try:
            content = self.content_collection.find_one({"id": content_id})
            
            if not content:
                return None
            
            # MongoDB _id alanını kaldır
            if "_id" in content:
                del content["_id"]
            
            # Önizleme URL'sini ekle
            if content.get("preview_path"):
                preview_filename = os.path.basename(content["preview_path"])
                content["preview"] = f"/api/v1/multimodal/preview/{preview_filename}"
            
            return content
            
        except Exception as e:
            logger.error(f"İçerik getirme hatası: {str(e)}")
            return None
    
    def list_contents(self, content_type: ContentType, user_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Kullanıcının içeriklerini listele.
        
        Args:
            content_type: İçerik türü
            user_id: Kullanıcı ID'si
            page: Sayfa numarası
            page_size: Sayfa başına öğe sayısı
            
        Returns:
            Dict[str, Any]: İçerik listesi ve meta veriler
        """
        try:
            # Filtreleme
            filter_query = {
                "user_id": user_id,
                "content_type": content_type.value
            }
            
            # Toplam sayıyı hesapla
            total_count = self.content_collection.count_documents(filter_query)
            
            # Sayfalama
            skip = (page - 1) * page_size
            
            # Sorgu
            contents = list(self.content_collection.find(
                filter_query,
                sort=[("created_at", -1)],
                skip=skip,
                limit=page_size
            ))
            
            # MongoDB _id alanını kaldır ve önizleme URL'sini ekle
            processed_contents = []
            for content in contents:
                if "_id" in content:
                    del content["_id"]
                
                # Önizleme URL'sini ekle
                if content.get("preview_path"):
                    preview_filename = os.path.basename(content["preview_path"])
                    content["preview"] = f"/api/v1/multimodal/preview/{preview_filename}"
                
                processed_contents.append(content)
            
            return {
                "contents": processed_contents,
                "meta": {
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
            
        except Exception as e:
            logger.error(f"İçerik listeleme hatası: {str(e)}")
            return {
                "contents": [],
                "meta": {
                    "total_count": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "error": str(e)
                }
            }
    
    def delete_content(self, content_id: str) -> bool:
        """
        İçeriği sil.
        
        Args:
            content_id: İçerik ID'si
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            # İçeriği getir
            content = self.content_collection.find_one({"id": content_id})
            
            if not content:
                logger.error(f"Silinecek içerik bulunamadı: {content_id}")
                return False
            
            # Dosya yollarını al
            storage_path = content.get("storage_path")
            preview_path = content.get("preview_path")
            
            # Dosyaları sil
            file_paths = [storage_path, preview_path]
            for path in file_paths:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        logger.error(f"Dosya silme hatası: {path}, {str(e)}")
            
            # Veritabanından kaydı sil
            self.content_collection.delete_one({"id": content_id})
            
            # Embedding'leri sil (varsa)
            self.embedding_collection.delete_many({"content_id": content_id})
            
            logger.info(f"İçerik başarıyla silindi: {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"İçerik silme hatası: {str(e)}")
            return False
    
    def search_by_text(self, query_text: str, user_id: str, limit: int = 20, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Metin sorgusuyla içerik ara.
        
        Args:
            query_text: Sorgu metni
            user_id: Kullanıcı ID'si
            limit: Maksimum sonuç sayısı
            filter_dict: Filtreleme seçenekleri
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        try:
            # CLIP modelini yükle
            model, processor = self._load_image_model("clip")
            
            if not model or not processor:
                return []
            
            # Sorgu metnini embed et
            inputs = processor(text=[query_text], return_tensors="pt", padding=True)
            
            with torch.no_grad():
                text_features = model.get_text_features(**inputs)
                text_embedding = text_features.detach().numpy()[0]
            
            # Filtreleri oluştur
            filters = {"user_id": user_id}
            if filter_dict:
                for key, value in filter_dict.items():
                    filters[key] = value
            
            # Embedding koleksiyonundaki tüm öğeleri al (basit bir yaklaşım)
            # Not: Gerçek uygulamalarda vektör veritabanı kullanılmalıdır
            all_embeddings = list(self.embedding_collection.find(filters))
            
            # Benzerlik hesapla ve sırala
            results = []
            for embedding_doc in all_embeddings:
                content_embedding = embedding_doc.get("embedding", [])
                
                if not content_embedding:
                    continue
                
                # Kosinüs benzerliği hesapla
                similarity = self._cosine_similarity(text_embedding, content_embedding)
                
                content_id = embedding_doc.get("content_id")
                content = self.get_content(content_id)
                
                if content:
                    results.append({
                        **content,
                        "similarity": float(similarity)
                    })
            
            # Benzerliğe göre sırala ve limitle
            sorted_results = sorted(results, key=lambda x: x["similarity"], reverse=True)
            return sorted_results[:limit]
            
        except Exception as e:
            logger.error(f"Metin araması hatası: {str(e)}")
            return []
    
    def search_by_image(self, image_id: str, user_id: str, limit: int = 20, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Görüntü sorgusuyla içerik ara.
        
        Args:
            image_id: Sorgu görüntüsünün ID'si
            user_id: Kullanıcı ID'si
            limit: Maksimum sonuç sayısı
            filter_dict: Filtreleme seçenekleri
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        try:
            # Sorgu görüntüsünü getir
            query_content = self.get_content(image_id)
            
            if not query_content or query_content.get("content_type") != ContentType.IMAGE.value:
                logger.error(f"Geçerli bir sorgu görüntüsü bulunamadı: {image_id}")
                return []
            
            # Görüntünün embedding'ini getir
            query_embedding_doc = self.embedding_collection.find_one({"content_id": image_id})
            
            if not query_embedding_doc or "embedding" not in query_embedding_doc:
                logger.error(f"Sorgu görüntüsü için embedding bulunamadı: {image_id}")
                return []
            
            query_embedding = query_embedding_doc["embedding"]
            
            # Filtreleri oluştur
            filters = {"user_id": user_id}
            if filter_dict:
                for key, value in filter_dict.items():
                    filters[key] = value
            
            # Embedding koleksiyonundaki tüm öğeleri al
            all_embeddings = list(self.embedding_collection.find(filters))
            
            # Benzerlik hesapla ve sırala
            results = []
            for embedding_doc in all_embeddings:
                content_embedding = embedding_doc.get("embedding", [])
                content_id = embedding_doc.get("content_id")
                
                if not content_embedding or content_id == image_id:
                    continue
                
                # Kosinüs benzerliği hesapla
                similarity = self._cosine_similarity(query_embedding, content_embedding)
                
                content = self.get_content(content_id)
                
                if content:
                    results.append({
                        **content,
                        "similarity": float(similarity)
                    })
            
            # Benzerliğe göre sırala ve limitle
            sorted_results = sorted(results, key=lambda x: x["similarity"], reverse=True)
            return sorted_results[:limit]
            
        except Exception as e:
            logger.error(f"Görüntü araması hatası: {str(e)}")
            return []
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        İki vektör arasındaki kosinüs benzerliğini hesapla.
        
        Args:
            a: İlk vektör
            b: İkinci vektör
            
        Returns:
            float: Kosinüs benzerliği (0-1 arasında)
        """
        if not a or not b or len(a) != len(b):
            return 0.0
        
        a = np.array(a)
        b = np.array(b)
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        similarity = dot_product / (norm_a * norm_b)
        
        # -1 ile 1 arasındaki değeri 0 ile 1 arasına normalize et
        return float((similarity + 1) / 2)