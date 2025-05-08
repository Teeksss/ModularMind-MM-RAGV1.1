"""
Veri Kaynak Ajanları zamanlama işlemleri.
"""

import logging
import re
import schedule

logger = logging.getLogger(__name__)

def schedule_agent(manager, config):
    """
    Ajanı zamanlar.
    
    Args:
        manager: SourceAgentManager nesnesi
        config: Ajan yapılandırması
    """
    if not config.schedule:
        return
    
    # Mevcut zamanlamayı kaldır
    remove_agent_schedule(config.agent_id)
    
    # Zamanlama tipini analiz et
    if config.schedule.startswith("interval:"):
        # Aralık zamanlama (örn: "interval:10m")
        interval_str = config.schedule.split(":", 1)[1].strip()
        
        # Birimi ve değeri ayır
        match = re.match(r"(\d+)([smhd])", interval_str)
        
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            # Saniye olarak aralığı hesapla
            if unit == "s":
                seconds = value
            elif unit == "m":
                seconds = value * 60
            elif unit == "h":
                seconds = value * 60 * 60
            elif unit == "d":
                seconds = value * 60 * 60 * 24
            else:
                logger.error(f"Geçersiz aralık birimi: {unit}")
                return
            
            # Her X saniyede bir çalıştır
            schedule.every(seconds).seconds.do(manager._scheduled_run, agent_id=config.agent_id).tag(config.agent_id)
            
    elif config.schedule.startswith("cron:"):
        # Cron zamanlama (örn: "cron:0 9 * * *")
        cron_str = config.schedule.split(":", 1)[1].strip()
        
        # Cron ifadesini parçala
        parts = cron_str.split()
        
        if len(parts) != 5:
            logger.error(f"Geçersiz cron ifadesi: {cron_str}")
            return
        
        minute, hour, day, month, day_of_week = parts
        
        # Schedule yapılandırması
        job = schedule.every()
        
        # Gün ayarla
        if day != "*":
            job = job.day(int(day))
        
        # Ay ayarla
        if month != "*":
            logger.warning("Aylık zamanlama desteklenmiyor, görmezden geliniyor")
        
        # Haftanın günü ayarla
        if day_of_week != "*":
            days = {
                "0": "sunday",
                "1": "monday",
                "2": "tuesday",
                "3": "wednesday",
                "4": "thursday",
                "5": "friday",
                "6": "saturday"
            }
            if day_of_week in days:
                job = getattr(job, days[day_of_week])
        
        # Saat ve dakika ayarla
        if hour != "*":
            job = job.at(f"{hour.zfill(2)}:{minute.zfill(2)}")
        else:
            # Her saatte, dakika belirt
            if minute != "*":
                job = job.minute(int(minute))
        
        # İşi ekle
        job.do(manager._scheduled_run, agent_id=config.agent_id).tag(config.agent_id)
        
    elif config.schedule.startswith("daily:"):
        # Günlük zamanlama (örn: "daily:09:00")
        time_str = config.schedule.split(":", 1)[1].strip()
        
        # Her gün belirtilen saatte çalıştır
        schedule.every().day.at(time_str).do(manager._scheduled_run, agent_id=config.agent_id).tag(config.agent_id)
        
    else:
        logger.error(f"Desteklenmeyen zamanlama formatı: {config.schedule}")

def remove_agent_schedule(agent_id: str) -> None:
    """
    Ajan zamanlamasını kaldırır.
    
    Args:
        agent_id: Ajan ID
    """
    # Etiketlenen işleri kaldır
    schedule.clear(agent_id)