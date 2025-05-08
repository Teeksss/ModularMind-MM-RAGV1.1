import os
import re
import sys
import time
import logging
import importlib
from glob import glob
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ModularMind.API.db.base import DatabaseManager

logger = logging.getLogger(__name__)

class Migration:
    """Veritabanı migrasyon sınıfı."""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.created_at = datetime.utcnow()
    
    def up(self) -> None:
        """
        Migrasyon uygulama adımları.
        Alt sınıflar tarafından uygulanmalıdır.
        """
        raise NotImplementedError("up metodu uygulanmalıdır.")
    
    def down(self) -> None:
        """
        Migrasyon geri alma adımları.
        Alt sınıflar tarafından uygulanmalıdır.
        """
        raise NotImplementedError("down metodu uygulanmalıdır.")


class MigrationManager:
    """
    Veritabanı migrasyon yöneticisi.
    Migrasyon dosyalarını bulur, sıralar ve uygular.
    """
    
    MIGRATION_COLLECTION = "migrations"
    MIGRATION_PATH = "ModularMind/API/db/migrations"
    MIGRATION_PATTERN = r"^V(\d+)__(.+)\.py$"
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.migrations_collection = self.db_manager.get_collection(self.MIGRATION_COLLECTION)
        self._ensure_migration_collection()
    
    def _ensure_migration_collection(self) -> None:
        """Migrasyon koleksiyonunu ve indekslerini oluşturur."""
        if self.MIGRATION_COLLECTION not in self.db_manager.get_database().list_collection_names():
            self.db_manager.create_indexes(
                self.MIGRATION_COLLECTION,
                [{"keys": [("version", 1)], "unique": True}]
            )
            logger.info(f"{self.MIGRATION_COLLECTION} koleksiyonu oluşturuldu")
    
    def get_applied_migrations(self) -> Dict[str, Dict[str, Any]]:
        """
        Uygulanmış migrasyonları veritabanından getirir.
        
        Returns:
            Dict[str, Dict[str, Any]]: Uygulanmış migrasyonlar {version: data}
        """
        applied = {}
        for migration in self.migrations_collection.find().sort("version", 1):
            applied[migration["version"]] = migration
        return applied
    
    def get_available_migrations(self) -> List[Dict[str, Any]]:
        """
        Klasörde bulunan tüm migrasyon dosyalarını bulur.
        
        Returns:
            List[Dict[str, Any]]: Kullanılabilir migrasyonlar listesi
        """
        available = []
        
        # Migrasyon klasörü yoksa oluştur
        if not os.path.exists(self.MIGRATION_PATH):
            os.makedirs(self.MIGRATION_PATH)
            logger.info(f"Migrasyon klasörü oluşturuldu: {self.MIGRATION_PATH}")
        
        # Migrasyon dosyalarını bul
        migration_files = glob(f"{self.MIGRATION_PATH}/V*__.*.py")
        
        for file_path in migration_files:
            file_name = os.path.basename(file_path)
            match = re.match(self.MIGRATION_PATTERN, file_name)
            
            if match:
                version, description = match.groups()
                description = description.replace("_", " ")
                
                available.append({
                    "version": version,
                    "description": description,
                    "file_name": file_name,
                    "file_path": file_path
                })
        
        # Versiyon numarasına göre sırala
        return sorted(available, key=lambda x: x["version"])
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """
        Henüz uygulanmamış migrasyonları bulur.
        
        Returns:
            List[Dict[str, Any]]: Bekleyen migrasyonlar listesi
        """
        applied = self.get_applied_migrations()
        available = self.get_available_migrations()
        
        pending = []
        for migration in available:
            if migration["version"] not in applied:
                pending.append(migration)
        
        return pending
    
    def create_migration(self, description: str) -> str:
        """
        Yeni bir migrasyon dosyası oluşturur.
        
        Args:
            description: Migrasyon açıklaması
            
        Returns:
            str: Oluşturulan migrasyon dosyasının yolu
        """
        # En son versiyonu bul
        available = self.get_available_migrations()
        last_version = int(available[-1]["version"]) if available else 0
        new_version = str(last_version + 1).zfill(4)
        
        # Dosya adı formatla
        slug = description.lower().replace(" ", "_")
        file_name = f"V{new_version}__{slug}.py"
        file_path = os.path.join(self.MIGRATION_PATH, file_name)
        
        # Şablon içeriği
        template = f'''from ModularMind.API.db.migration import Migration

class {slug.title().replace("_", "")}Migration(Migration):
    """
    {description}
    """
    
    def __init__(self):
        super().__init__(version="{new_version}", description="{description}")
    
    def up(self):
        """Migrate up."""
        # TODO: Migrasyon kodunu buraya yaz
        pass
    
    def down(self):
        """Migrate down."""
        # TODO: Geri alma kodunu buraya yaz
        pass

# Migrasyon sınıfını oluştur
migration = {slug.title().replace("_", "")}Migration()
'''
        
        # Dosyayı oluştur
        with open(file_path, "w") as f:
            f.write(template)
        
        logger.info(f"Yeni migrasyon oluşturuldu: {file_path}")
        return file_path
    
    def apply_migration(self, migration_data: Dict[str, Any]) -> bool:
        """
        Belirtilen migrasyonu uygular.
        
        Args:
            migration_data: Migrasyon verileri
            
        Returns:
            bool: Başarılı mı
        """
        file_path = migration_data["file_path"]
        version = migration_data["version"]
        description = migration_data["description"]
        
        logger.info(f"Migrasyon uygulanıyor: V{version} - {description}")
        
        try:
            # Migrasyon modülünü dinamik olarak yükle
            spec = importlib.util.spec_from_file_location(
                f"migration_{version}",
                file_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Migrasyon nesnesini al
            migration = getattr(module, "migration")
            
            # up metodunu çağır
            migration.up()
            
            # Veritabanına kaydet
            self.migrations_collection.insert_one({
                "version": version,
                "description": description,
                "executed_at": datetime.utcnow()
            })
            
            logger.info(f"Migrasyon başarıyla uygulandı: V{version}")
            return True
            
        except Exception as e:
            logger.error(f"Migrasyon hatası (V{version}): {str(e)}")
            return False
    
    def apply_all_pending(self) -> Dict[str, Any]:
        """
        Tüm bekleyen migrasyonları uygular.
        
        Returns:
            Dict[str, Any]: Sonuç istatistikleri
        """
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("Bekleyen migrasyon yok")
            return {"applied": 0, "failed": 0, "total": 0}
        
        logger.info(f"{len(pending)} migrasyon uygulanacak")
        
        applied = 0
        failed = 0
        
        for migration in pending:
            if self.apply_migration(migration):
                applied += 1
            else:
                failed += 1
                # Hata durumunda işlemi durdur
                break
        
        return {
            "applied": applied,
            "failed": failed,
            "total": len(pending),
            "remaining": len(pending) - applied - failed
        }
    
    def rollback_last(self) -> bool:
        """
        En son uygulanan migrasyonu geri alır.
        
        Returns:
            bool: Başarılı mı
        """
        # En son uygulanan migrasyonu bul
        last_migration = self.migrations_collection.find_one(
            sort=[("version", -1)]
        )
        
        if not last_migration:
            logger.info("Geri alınacak migrasyon yok")
            return False
        
        version = last_migration["version"]
        
        # Migrasyon dosyasını bul
        available = self.get_available_migrations()
        migration_data = None
        
        for migration in available:
            if migration["version"] == version:
                migration_data = migration
                break
        
        if not migration_data:
            logger.error(f"V{version} için migrasyon dosyası bulunamadı")
            return False
        
        logger.info(f"Migrasyon geri alınıyor: V{version} - {migration_data['description']}")
        
        try:
            # Migrasyon modülünü dinamik olarak yükle
            spec = importlib.util.spec_from_file_location(
                f"migration_{version}",
                migration_data["file_path"]
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Migrasyon nesnesini al
            migration = getattr(module, "migration")
            
            # down metodunu çağır
            migration.down()
            
            # Veritabanından çıkar
            self.migrations_collection.delete_one({"version": version})
            
            logger.info(f"Migrasyon başarıyla geri alındı: V{version}")
            return True
            
        except Exception as e:
            logger.error(f"Migrasyon geri alma hatası (V{version}): {str(e)}")
            return False