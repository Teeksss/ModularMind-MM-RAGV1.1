"""
Log dosyalarını okuyan ve yöneten servis.
"""

import os
import re
import json
import time
import glob
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class LogService:
    """
    Log dosyalarını okuma ve yönetme servisi.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Args:
            log_dir: Log dosyalarının bulunduğu dizin
        """
        self.log_dir = log_dir
        
        # Log dizininin varlığını kontrol et
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
            logger.info(f"Log dizini oluşturuldu: {self.log_dir}")
    
    def get_log_files(self, environment: Optional[str] = None) -> List[str]:
        """
        Log dosyalarının listesini döndürür.
        
        Args:
            environment: Ortam adı (örn. production, development)
            
        Returns:
            List[str]: Log dosyalarının tam yolları
        """
        pattern = f"{self.log_dir}/*.log"
        if environment:
            pattern = f"{self.log_dir}/*_{environment}.log"
            
        return glob.glob(pattern)
    
    def get_json_log_files(self, environment: Optional[str] = None) -> List[str]:
        """
        JSON formatındaki log dosyalarının listesini döndürür.
        
        Args:
            environment: Ortam adı (örn. production, development)
            
        Returns:
            List[str]: JSON log dosyalarının tam yolları
        """
        pattern = f"{self.log_dir}/*.json"
        if environment:
            pattern = f"{self.log_dir}/*_{environment}.json"
            
        return glob.glob(pattern)
    
    def _parse_standard_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Standart log satırını ayrıştırır.
        
        Args:
            line: Log satırı
            
        Returns:
            Optional[Dict[str, Any]]: Ayrıştırılmış log veya None
        """
        # Standart log formatı: 2023-11-29 14:32:45,123 [INFO] module:123: Message
        pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\] ([^:]+):(\d+)(?: \[([^\]]+)\])?: (.+)"
        match = re.match(pattern, line)
        
        if match:
            timestamp_str, level, module, line_num, function, message = match.groups()
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            
            return {
                "timestamp": timestamp.isoformat(),
                "level": level,
                "module": module,
                "line": int(line_num),
                "function": function or "",
                "message": message
            }
        
        return None
    
    def get_logs(
        self, 
        level: str = "ERROR", 
        limit: int = 100,
        start_time: Optional[float] = None, 
        end_time: Optional[float] = None,
        module: Optional[str] = None,
        environment: Optional[str] = "production"
    ) -> List[Dict[str, Any]]:
        """
        Log kayıtlarını filtrelere göre döndürür.
        
        Args:
            level: Minimum log seviyesi
            limit: Maksimum döndürülecek log sayısı
            start_time: Başlangıç zamanı (Unix timestamp)
            end_time: Bitiş zamanı (Unix timestamp)
            module: Filtrelenecek modül adı
            environment: Ortam adı
            
        Returns:
            List[Dict[str, Any]]: Filtrelenmiş log kayıtları
        """
        logs = []
        level_priority = {
            "DEBUG": 0,
            "INFO": 1,
            "WARNING": 2,
            "ERROR": 3,
            "CRITICAL": 4
        }
        min_level_priority = level_priority.get(level, 0)
        
        # Start ve end time objelerini oluştur
        start_datetime = datetime.fromtimestamp(start_time) if start_time else None
        end_datetime = datetime.fromtimestamp(end_time) if end_time else None
        
        # Önce JSON log dosyalarını oku (daha yapılandırılmış)
        json_files = self.get_json_log_files(environment)
        for file_path in json_files:
            try:
                with open(file_path, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            log_entry = json.loads(line)
                            
                            # Seviye kontrolü
                            entry_level = log_entry.get("level", "INFO")
                            if level_priority.get(entry_level, 0) < min_level_priority:
                                continue
                                
                            # Zaman kontrolü
                            if "timestamp" in log_entry:
                                log_time = datetime.fromisoformat(log_entry["timestamp"].replace("Z", "+00:00"))
                                
                                if start_datetime and log_time < start_datetime:
                                    continue
                                    
                                if end_datetime and log_time > end_datetime:
                                    continue
                            
                            # Modül kontrolü
                            if module and log_entry.get("module") != module:
                                continue
                                
                            logs.append(log_entry)
                            
                            # Limit kontrolü
                            if len(logs) >= limit:
                                break
                        except json.JSONDecodeError:
                            continue
                        
                if len(logs) >= limit:
                    break
            except Exception as e:
                logger.error(f"JSON log dosyası okuma hatası: {file_path}, {str(e)}")
        
        # Gereken sayıda log alınamadıysa, standart log dosyalarını oku
        if len(logs) < limit:
            remaining = limit - len(logs)
            standard_files = self.get_log_files(environment)
            
            for file_path in standard_files:
                try:
                    with open(file_path, 'r') as file:
                        for line in file:
                            line = line.strip()
                            if not line:
                                continue
                                
                            log_entry = self._parse_standard_log_line(line)
                            if not log_entry:
                                continue
                                
                            # Seviye kontrolü
                            entry_level = log_entry.get("level", "INFO")
                            if level_priority.get(entry_level, 0) < min_level_priority:
                                continue
                                
                            # Zaman kontrolü
                            if "timestamp" in log_entry:
                                log_time = datetime.fromisoformat(log_entry["timestamp"])
                                
                                if start_datetime and log_time < start_datetime:
                                    continue
                                    
                                if end_datetime and log_time > end_datetime:
                                    continue
                            
                            # Modül kontrolü
                            if module and log_entry.get("module") != module:
                                continue
                                
                            logs.append(log_entry)
                            
                            # Limit kontrolü
                            if len(logs) >= limit:
                                break
                
                    if len(logs) >= limit:
                        break
                except Exception as e:
                    logger.error(f"Standart log dosyası okuma hatası: {file_path}, {str(e)}")
        
        # Zamana göre sırala (en yeniden en eskiye)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return logs[:limit]
    
    def get_error_summary(self, days: int = 7, environment: Optional[str] = "production") -> Dict[str, Any]:
        """
        Hata istatistiklerini döndürür.
        
        Args:
            days: Kaç günlük hataların özetleneceği
            environment: Ortam adı
            
        Returns:
            Dict[str, Any]: Hata istatistikleri
        """
        # Son X gün için zaman hesapla
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Hataları getir
        errors = self.get_logs(
            level="ERROR",
            limit=1000,  # Yeterince yüksek bir limit
            start_time=start_time.timestamp(),
            end_time=end_time.timestamp(),
            environment=environment
        )
        
        # Hataları modüllere göre grupla
        modules = {}
        for error in errors:
            module = error.get("module", "unknown")
            if module not in modules:
                modules[module] = 0
            modules[module] += 1
        
        # Hataları zamana göre grupla
        daily_counts = {}
        for error in errors:
            timestamp = error.get("timestamp", "")
            if timestamp:
                try:
                    date = datetime.fromisoformat(timestamp).date().isoformat()
                    if date not in daily_counts:
                        daily_counts[date] = 0
                    daily_counts[date] += 1
                except (ValueError, TypeError):
                    pass
        
        # Günlük sayıları sırala
        sorted_daily_counts = []
        for date in sorted(daily_counts.keys()):
            sorted_daily_counts.append({
                "date": date,
                "count": daily_counts[date]
            })
        
        return {
            "total_errors": len(errors),
            "period_days": days,
            "modules": [{"module": k, "count": v} for k, v in sorted(modules.items(), key=lambda x: x[1], reverse=True)],
            "daily_counts": sorted_daily_counts
        }
    
    def rotate_logs(self, max_size_mb: int = 10, max_files: int = 5) -> Dict[str, Any]:
        """
        Log dosyalarını döndürür (büyük olanları arşivler).
        
        Args:
            max_size_mb: Maksimum log dosyası boyutu (MB)
            max_files: Her log tipi için saklanacak maksimum arşiv sayısı
            
        Returns:
            Dict[str, Any]: Döndürme işlemi sonuçları
        """
        rotated = []
        deleted = []
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # Tüm log dosyalarını kontrol et
        all_logs = self.get_log_files() + self.get_json_log_files()
        
        for log_file in all_logs:
            try:
                file_size = os.path.getsize(log_file)
                
                # Dosya boyutu maksimumu aştıysa, döndür
                if file_size > max_size_bytes:
                    # Yeni dosya adı oluştur (timestamp ile)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    base_name, ext = os.path.splitext(log_file)
                    archive_file = f"{base_name}_{timestamp}{ext}"
                    
                    # Dosyayı yeniden adlandır
                    os.rename(log_file, archive_file)
                    
                    # Yeni boş dosya oluştur
                    open(log_file, 'a').close()
                    
                    rotated.append({
                        "original": log_file,
                        "archive": archive_file,
                        "size_mb": file_size / (1024 * 1024)
                    })
                    
                    # Eskimiş arşivleri kontrol et ve temizle
                    self._cleanup_old_archives(log_file, max_files, deleted)
            except Exception as e:
                logger.error(f"Log döndürme hatası: {log_file}, {str(e)}")
        
        return {
            "rotated_count": len(rotated),
            "rotated_files": rotated,
            "deleted_count": len(deleted),
            "deleted_files": deleted
        }
    
    def _cleanup_old_archives(self, log_file: str, max_files: int, deleted: List[Dict[str, Any]]) -> None:
        """
        Eski arşiv dosyalarını temizler.
        
        Args:
            log_file: Ana log dosyası yolu
            max_files: Saklanacak maksimum arşiv sayısı
            deleted: Silinen dosyaların ekleneceği liste
        """
        try:
            base_name, ext = os.path.splitext(log_file)
            
            # Bu log dosyasının tüm arşivlerini bul
            pattern = f"{base_name}_*{ext}"
            archives = glob.glob(pattern)
            
            # Tarihe göre sırala (en eskiden en yeniye)
            archives.sort(key=lambda x: os.path.getmtime(x))
            
            # Maksimum sayıdan fazlaysa, en eskileri sil
            if len(archives) > max_files:
                for archive in archives[:-max_files]:
                    size = os.path.getsize(archive) / (1024 * 1024)
                    os.remove(archive)
                    deleted.append({
                        "file": archive,
                        "size_mb": size
                    })
        except Exception as e:
            logger.error(f"Arşiv temizleme hatası: {log_file}, {str(e)}")