"""
İşlemci ve bellek kaynaklarını yöneten modül.
Uygulamanın yüksek yük altında da kararlı çalışmasını sağlar.
"""

import os
import platform
import time
import logging
import psutil
import threading
import asyncio
from typing import Dict, Any, Optional, Callable, List, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

class ResourceManager:
    """
    CPU ve bellek kaynaklarının kullanımını izleyen ve yöneten sınıf.
    Uygulamanın kararlı çalışmasını sağlamak için kaynak kısıtlamaları uygular.
    """
    
    # Singleton örnek
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Yapılandırma
        self.max_cpu_percent = float(os.getenv("MAX_CPU_PERCENT", "80"))
        self.max_memory_percent = float(os.getenv("MAX_MEMORY_PERCENT", "85"))
        self.check_interval = int(os.getenv("RESOURCE_CHECK_INTERVAL", "10"))  # saniye
        
        # İzleme değişkenleri
        self.current_cpu_percent = 0
        self.current_memory_percent = 0
        self.high_load_mode = False
        self.process = psutil.Process()
        
        # İzleme iş parçacığı
        self.monitoring_thread = None
        self.monitoring_active = False
        
        # Yüksek yük altında kısıtlanacak işlevler
        self.throttled_functions: List[Callable] = []
        
        # Kaynakların yükseldiği bildirilecek call back'ler
        self.resource_callbacks: Dict[str, List[Tuple[Callable, Dict[str, Any]]]] = {
            "high_cpu": [],
            "high_memory": [],
            "normal": []
        }
        
        # İzleme iş parçacığını başlat
        self.start_monitoring()
        
        self._initialized = True
        logger.info(f"Kaynak yöneticisi başlatıldı: CPU sınırı={self.max_cpu_percent}%, Bellek sınırı={self.max_memory_percent}%")
    
    def start_monitoring(self):
        """
        Kaynak izleme iş parçacığını başlatır.
        """
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitoring_thread.start()
        logger.debug("Kaynak izleme başlatıldı")
    
    def stop_monitoring(self):
        """
        Kaynak izleme iş parçacığını durdurur.
        """
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1)
            self.monitoring_thread = None
            logger.debug("Kaynak izleme durduruldu")
    
    def _monitor_resources(self):
        """
        Sistem ve uygulama kaynaklarını periyodik olarak izler.
        Yüksek yük durumunda kısıtlamalar uygular ve bildirimleri tetikler.
        """
        last_notification_time = 0
        notification_threshold = 60  # 1 dakika
        
        while self.monitoring_active:
            try:
                # CPU kullanımını al
                self.current_cpu_percent = psutil.cpu_percent(interval=1)
                
                # Bellek kullanımını al
                self.current_memory_percent = psutil.virtual_memory().percent
                
                # Uygulama sürecinin bellek ve CPU kullanımı
                process_info = self.process.as_dict(attrs=['cpu_percent', 'memory_percent'])
                
                cpu_high = self.current_cpu_percent > self.max_cpu_percent
                memory_high = self.current_memory_percent > self.max_memory_percent
                
                # Yüksek yük durumunu kontrol et
                new_high_load_mode = cpu_high or memory_high
                
                # Yüksek yük durumu değiştiyse
                if new_high_load_mode != self.high_load_mode:
                    self.high_load_mode = new_high_load_mode
                    
                    # Bildirimler
                    current_time = time.time()
                    if current_time - last_notification_time > notification_threshold:
                        last_notification_time = current_time
                        
                        if self.high_load_mode:
                            logger.warning(
                                f"Yüksek kaynak kullanımı tespit edildi! "
                                f"CPU: {self.current_cpu_percent:.1f}%, "
                                f"Bellek: {self.current_memory_percent:.1f}%. "
                                f"Performans kısıtlamaları uygulanıyor."
                            )
                            
                            # CPU yüksekse callback'leri çağır
                            if cpu_high:
                                self._notify_callbacks("high_cpu")
                            
                            # Bellek yüksekse callback'leri çağır
                            if memory_high:
                                self._notify_callbacks("high_memory")
                        else:
                            logger.info(
                                f"Kaynak kullanımı normal seviyeye döndü. "
                                f"CPU: {self.current_cpu_percent:.1f}%, "
                                f"Bellek: {self.current_memory_percent:.1f}%."
                            )
                            
                            # Normal moda döndüğünde callback'leri çağır
                            self._notify_callbacks("normal")
                
                # Bekle
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Kaynak izleme hatası: {str(e)}")
                time.sleep(self.check_interval)
    
    def _notify_callbacks(self, event_type: str):
        """
        Belirli olay türü için kayıtlı callback'leri çağırır.
        
        Args:
            event_type: Olay türü ('high_cpu', 'high_memory', 'normal')
        """
        for callback, kwargs in self.resource_callbacks.get(event_type, []):
            try:
                callback(**kwargs)
            except Exception as e:
                logger.error(f"Kaynak callback hatası: {str(e)}")
    
    def register_callback(self, event_type: str, callback: Callable, **kwargs):
        """
        Kaynak olayları için callback kaydeder.
        
        Args:
            event_type: Olay türü ('high_cpu', 'high_memory', 'normal')
            callback: Çağrılacak fonksiyon
            **kwargs: Callback'e geçirilecek argümanlar
        """
        if event_type in self.resource_callbacks:
            self.resource_callbacks[event_type].append((callback, kwargs))
            logger.debug(f"'{event_type}' olayı için callback kaydedildi")
    
    def get_system_resources(self) -> Dict[str, Any]:
        """
        Sistem kaynaklarının anlık görüntüsünü döndürür.
        
        Returns:
            Dict[str, Any]: Sistem kaynakları bilgisi
        """
        # CPU bilgisi
        cpu_info = {
            "percent": self.current_cpu_percent,
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False)
        }
        
        # Bellek bilgisi
        memory = psutil.virtual_memory()
        memory_info = {
            "percent": memory.percent,
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "used_gb": round(memory.used / (1024 ** 3), 2)
        }
        
        # Disk bilgisi
        disk = psutil.disk_usage('/')
        disk_info = {
            "percent": disk.percent,
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2)
        }
        
        # Süreç bilgisi
        proc_info = {
            "cpu_percent": self.process.cpu_percent(),
            "memory_percent": self.process.memory_percent(),
            "threads": len(self.process.threads()),
            "open_files": len(self.process.open_files()),
        }
        
        # Sistem bilgisi
        sys_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "high_load_mode": self.high_load_mode
        }
        
        return {
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "process": proc_info,
            "system": sys_info,
            "timestamp": time.time()
        }

# CPU yoğun işlemler için süreç bazlı kaynak sınırlayıcı dekoratör
def limit_cpu(max_processes: int = 4, queue_timeout: int = 300):
    """
    CPU yoğun işlemleri sınırlamak için kullanılan dekoratör.
    En fazla belirtilen sayıda eşzamanlı işleme izin verir.
    
    Args:
        max_processes: İzin verilen maksimum eşzamanlı işlem sayısı
        queue_timeout: Sıra bekleme süresi (saniye)
    """
    # Eşzamanlı işlemleri sınırlayacak semaphore
    semaphore = asyncio.Semaphore(max_processes)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Semaphore beklemesi için timeout
            try:
                async with asyncio.timeout(queue_timeout):
                    async with semaphore:
                        # İşlevi çağır
                        return await func(*args, **kwargs)
            except TimeoutError:
                logger.error(f"CPU sınırı zaman aşımı: {func.__name__} {queue_timeout} saniye boyunca çalıştırılamadı")
                raise Exception(f"İşlem yoğunluğu nedeniyle zaman aşımı - lütfen daha sonra tekrar deneyin")
        return wrapper
    return decorator

# Kaynak kullanım durumuna göre kısıtlama uygulayan dekoratör
def resource_aware(throttle_on_high_load: bool = True):
    """
    Yüksek kaynak kullanımında işlevin davranışını değiştirmek için kullanılan dekoratör.
    
    Args:
        throttle_on_high_load: Yüksek yük durumunda işlevi kısıtla
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            resource_manager = ResourceManager()
            
            # Yüksek yük durumunda kısıtlama uygula
            if throttle_on_high_load and resource_manager.high_load_mode:
                # Gecikme ekle
                await asyncio.sleep(0.5)
                
                # Daha basit bir yanıt dönebilir veya işlemi reddedebilir
                if kwargs.get('simplify_on_high_load', False):
                    kwargs['simplified'] = True
            
            # İşlevi çağır
            return await func(*args, **kwargs)
        return wrapper
    return decorator