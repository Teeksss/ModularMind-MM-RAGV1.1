"""
Vektör veritabanı bakım işlemleri
"""

import os
import logging
import time
import json
import gc
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np
import threading

logger = logging.getLogger(__name__)

class MaintenanceManager:
    """
    Vektör veritabanı bakım işlemlerini yönetir.
    
    Bu sınıf indekslerin optimize edilmesi, yeniden oluşturulması,
    ve düzenli bakım görevlerinin planlanması işlemlerini sağlar.
    """
    
    def __init__(self, vector_store):
        """
        Bakım yöneticisini başlatır
        
        Args:
            vector_store: Bakımı yapılacak vektör deposu
        """
        self.vector_store = vector_store
        self.maintenance_lock = threading.Lock()
        self.maintenance_in_progress = False
        self.last_maintenance_time = 0
        self.scheduled_tasks = []
    
    def optimize_index(self, model_id: Optional[str] = None) -> bool:
        """
        Vektör indeksini optimize eder
        
        Args:
            model_id: Optimize edilecek model kimliği (None ise tüm modeller)
            
        Returns:
            bool: İşlem başarılı mı
        """
        if self.maintenance_in_progress:
            logger.warning("Başka bir bakım işlemi devam ediyor")
            return False
        
        try:
            with self.maintenance_lock:
                self.maintenance_in_progress = True
                
                start_time = time.time()
                logger.info(f"İndeks optimizasyonu başlıyor: {model_id or 'tüm modeller'}")
                
                # İndeksi optimize et (model belirtilmişse sadece o model için)
                if model_id:
                    if model_id not in self.vector_store.embedding_indexes:
                        logger.error(f"Model bulunamadı: {model_id}")
                        return False
                    
                    # Belirli bir model için optimize et
                    index_manager = self.vector_store.embedding_indexes[model_id]
                    if hasattr(index_manager, "optimize"):
                        index_manager.optimize()
                        logger.info(f"{model_id} indeksi optimize edildi")
                else:
                    # Tüm modeller için optimize et
                    for model_id, index_manager in self.vector_store.embedding_indexes.items():
                        if hasattr(index_manager, "optimize"):
                            index_manager.optimize()
                            logger.info(f"{model_id} indeksi optimize edildi")
                
                # Çöp toplayıcıyı çalıştır
                gc.collect()
                
                elapsed_time = time.time() - start_time
                logger.info(f"İndeks optimizasyonu tamamlandı, süre: {elapsed_time:.2f} saniye")
                
                self.last_maintenance_time = time.time()
                return True
        except Exception as e:
            logger.error(f"İndeks optimizasyonu hatası: {str(e)}")
            return False
        finally:
            self.maintenance_in_progress = False
    
    def rebuild_index(self, model_id: Optional[str] = None) -> bool:
        """
        Vektör indeksini yeniden oluşturur
        
        Args:
            model_id: Yeniden oluşturulacak model kimliği (None ise tüm modeller)
            
        Returns:
            bool: İşlem başarılı mı
        """
        if self.maintenance_in_progress:
            logger.warning("Başka bir bakım işlemi devam ediyor")
            return False
        
        try:
            with self.maintenance_lock:
                self.maintenance_in_progress = True
                
                start_time = time.time()
                logger.info(f"İndeks yeniden oluşturma başlıyor: {model_id or 'tüm modeller'}")
                
                # Silinmiş vektörleri temizle
                deleted_count = self.vector_store.cleanup_deleted_vectors(model_id)
                logger.info(f"Silinen vektörler temizlendi: {deleted_count}")
                
                # Belge listesini al
                documents = self.vector_store.list_documents(limit=100000)["documents"]
                
                # Belge sayısını kontrol et
                if not documents:
                    logger.warning("Yeniden oluşturulacak belge bulunamadı")
                    return False
                
                # Model listesini al
                if model_id:
                    models_to_rebuild = [model_id]
                else:
                    models_to_rebuild = list(self.vector_store.embedding_indexes.keys())
                
                # Her model için işlem yap
                for model in models_to_rebuild:
                    if model not in self.vector_store.embedding_indexes:
                        logger.error(f"Model bulunamadı: {model}")
                        continue
                    
                    # İndeksi sil ve yeniden oluştur
                    logger.info(f"{model} indeksi yeniden oluşturuluyor...")
                    
                    # Geçici indeks oluştur
                    temp_index_path = f"{self.vector_store.storage_path}/rebuild_temp_{model}"
                    os.makedirs(temp_index_path, exist_ok=True)
                    
                    # Yeni indeksi başlat
                    index_manager = self.vector_store.create_index_manager(model)
                    
                    # Her belge için embedding yeniden oluştur
                    for doc in documents:
                        doc_id = doc["id"]
                        chunks = self.vector_store.get_document_chunks(doc_id)
                        
                        # Her parça için embedding oluştur
                        for chunk in chunks:
                            chunk_id = chunk["id"]
                            text = chunk["text"]
                            
                            # Embedding oluştur
                            embedding = self.vector_store.create_embedding(text, model)
                            if embedding:
                                # Yeni indekse ekle
                                index_manager.add_item(embedding, chunk_id)
                    
                    # İndeksi kaydet
                    index_manager.save(temp_index_path)
                    
                    # Eski indeksi yedekle
                    old_index_path = f"{self.vector_store.storage_path}/{model}"
                    backup_index_path = f"{self.vector_store.storage_path}/backup_{model}_{int(time.time())}"
                    
                    if os.path.exists(old_index_path):
                        os.rename(old_index_path, backup_index_path)
                    
                    # Yeni indeksi aktif et
                    os.rename(temp_index_path, old_index_path)
                    
                    # İndeksi yükle
                    self.vector_store.embedding_indexes[model] = index_manager
                    logger.info(f"{model} indeksi yeniden oluşturuldu")
                
                # İndeksler yeniden yapılandırıldı, değişiklikleri kaydet
                self.vector_store.save()
                
                # Çöp toplayıcıyı çalıştır
                gc.collect()
                
                elapsed_time = time.time() - start_time
                logger.info(f"İndeks yeniden oluşturma tamamlandı, süre: {elapsed_time:.2f} saniye")
                
                self.last_maintenance_time = time.time()
                return True
        except Exception as e:
            logger.error(f"İndeks yeniden oluşturma hatası: {str(e)}")
            return False
        finally:
            self.maintenance_in_progress = False
    
    def compact_storage(self) -> bool:
        """
        Vektör deposunu sıkıştırır
        
        Returns:
            bool: İşlem başarılı mı
        """
        if self.maintenance_in_progress:
            logger.warning("Başka bir bakım işlemi devam ediyor")
            return False
        
        try:
            with self.maintenance_lock:
                self.maintenance_in_progress = True
                
                start_time = time.time()
                logger.info("Depo sıkıştırma başlıyor")
                
                # Meta verileri sıkıştır
                metadata_path = f"{self.vector_store.storage_path}/metadata.json"
                if os.path.exists(metadata_path):
                    # Yedek oluştur
                    backup_path = f"{metadata_path}.bak"
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    
                    # Meta verileri sıkıştır
                    with open(backup_path, "w") as f:
                        json.dump(metadata, f)
                    
                    # Sıkıştırılmış meta verileri kaydet
                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f, separators=(',', ':'))
                
                # Metadata temizliği
                removed_count = self.vector_store.cleanup_orphaned_metadata()
                logger.info(f"Sahipsiz meta veriler temizlendi: {removed_count}")
                
                # İndeksleri optimize et
                for model_id, index_manager in self.vector_store.embedding_indexes.items():
                    if hasattr(index_manager, "compact"):
                        index_manager.compact()
                        logger.info(f"{model_id} indeksi sıkıştırıldı")
                
                # Depo boyutunu hesapla
                total_size = 0
                for root, dirs, files in os.walk(self.vector_store.storage_path):
                    for file in files:
                        total_size += os.path.getsize(os.path.join(root, file))
                
                elapsed_time = time.time() - start_time
                logger.info(f"Depo sıkıştırma tamamlandı, süre: {elapsed_time:.2f} saniye")
                logger.info(f"Toplam depo boyutu: {total_size / (1024*1024):.2f} MB")
                
                self.last_maintenance_time = time.time()
                return True
        except Exception as e:
            logger.error(f"Depo sıkıştırma hatası: {str(e)}")
            return False
        finally:
            self.maintenance_in_progress = False
    
    def schedule_maintenance(
        self,
        task_type: str,
        interval_hours: int = 24,
        model_id: Optional[str] = None
    ) -> bool:
        """
        Düzenli bakım görevi planlar
        
        Args:
            task_type: Görev tipi (optimize, rebuild, compact)
            interval_hours: Tekrarlama aralığı (saat)
            model_id: İşlem yapılacak model kimliği
            
        Returns:
            bool: Planlama başarılı mı
        """
        try:
            # Görev tanımını oluştur
            task = {
                "type": task_type,
                "interval_hours": interval_hours,
                "model_id": model_id,
                "next_run": time.time() + (interval_hours * 3600)
            }
            
            # Görevi ekle
            self.scheduled_tasks.append(task)
            
            logger.info(f"Bakım görevi planlandı: {task_type}, {interval_hours} saat aralıkla")
            return True
        except Exception as e:
            logger.error(f"Bakım planlama hatası: {str(e)}")
            return False
    
    def check_scheduled_tasks(self) -> None:
        """Planlanmış görevleri kontrol eder ve zamanı gelenleri çalıştırır"""
        current_time = time.time()
        
        tasks_to_run = []
        
        # Çalıştırılacak görevleri belirle
        for task in self.scheduled_tasks:
            if current_time >= task["next_run"]:
                tasks_to_run.append(task)
        
        # Görevleri çalıştır
        for task in tasks_to_run:
            try:
                task_type = task["type"]
                model_id = task["model_id"]
                interval_hours = task["interval_hours"]
                
                # Görev tipine göre işlem yap
                if task_type == "optimize":
                    self.optimize_index(model_id)
                elif task_type == "rebuild":
                    self.rebuild_index(model_id)
                elif task_type == "compact":
                    self.compact_storage()
                
                # Bir sonraki çalışma zamanını ayarla
                task["next_run"] = current_time + (interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Planlı görev çalıştırma hatası: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Bakım istatistiklerini alır
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        return {
            "last_maintenance_time": self.last_maintenance_time,
            "maintenance_in_progress": self.maintenance_in_progress,
            "scheduled_tasks_count": len(self.scheduled_tasks),
            "next_maintenance": min([task["next_run"] for task in self.scheduled_tasks]) if self.scheduled_tasks else None
        }