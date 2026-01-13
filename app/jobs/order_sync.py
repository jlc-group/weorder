"""
Order Sync Scheduler - Periodic polling for orders from marketplace platforms
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services import integration_service, sync_service
from app.models.integration import PlatformConfig

logger = logging.getLogger(__name__)

# Global scheduler instance
# Global scheduler instance
_scheduler = None


class OrderSyncScheduler:
    """
    Manages scheduled order synchronization from marketplace platforms
    """
    
    def __init__(self):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Order sync scheduler started")
            
            # Schedule initial sync jobs (Run as a job to not block startup)
            from datetime import datetime
            self.scheduler.add_job(
                func=self._schedule_platform_syncs,
                trigger='date',
                run_date=datetime.now(),
                id='init_platform_syncs',
                name='Initialize Platform Syncs',
                replace_existing=True
            )
    
    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Order sync scheduler stopped")
    
    def _schedule_platform_syncs(self):
        """Schedule sync jobs for all active platforms"""
        db = SessionLocal()
        try:
            configs = integration_service.get_platform_configs(db, is_active=True)
            
            for config in configs:
                if config.sync_enabled:
                    self._add_sync_job(config)
            
            logger.info(f"Scheduled {len(configs)} platform sync jobs")
            
        finally:
            db.close()
    
    def _add_sync_job(self, config: PlatformConfig):
        """Add a sync job for a specific platform config"""
        job_id = f"sync_{config.platform}_{config.shop_id}"
        
        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Add new job with configured interval
        from apscheduler.triggers.interval import IntervalTrigger
        self.scheduler.add_job(
            func=self._run_sync,
            trigger=IntervalTrigger(minutes=config.sync_interval_minutes),
            id=job_id,
            name=f"Sync {config.platform}/{config.shop_name}",
            kwargs={"config_id": str(config.id)},
            replace_existing=True,
            max_instances=1,  # Prevent overlapping syncs
        )
        
        logger.info(
            f"Scheduled sync job: {config.platform}/{config.shop_name} "
            f"every {config.sync_interval_minutes} minutes"
        )
    
    async def _run_sync(self, config_id: str):
        """Execute sync for a specific platform"""
        db = SessionLocal()
        try:
            config = integration_service.get_platform_config(db, config_id)
            if not config:
                logger.warning(f"Platform config not found: {config_id}")
                return
            
            if not config.is_active or not config.sync_enabled:
                logger.info(f"Sync disabled for {config.platform}/{config.shop_name}")
                return
            
            logger.info(f"Starting scheduled sync: {config.platform}/{config.shop_name}")
            
            # Sync last 2 hours of orders
            time_from = datetime.utcnow() - timedelta(hours=2)
            
            stats = await sync_service.sync_single_platform(db, config_id, time_from)
            
            logger.info(
                f"Scheduled sync completed: {config.platform}/{config.shop_name} - "
                f"fetched={stats.get('fetched', 0)}, "
                f"created={stats.get('created', 0)}, "
                f"updated={stats.get('updated', 0)}"
            )
            
        except Exception as e:
            logger.error(f"Scheduled sync failed for config {config_id}: {e}")
            
        finally:
            db.close()
    
    def refresh_schedules(self):
        """Refresh all sync schedules from database"""
        # Remove all existing sync jobs
        for job in self.scheduler.get_jobs():
            if job.id.startswith("sync_"):
                self.scheduler.remove_job(job.id)
        
        # Re-schedule from database
        self._schedule_platform_syncs()
    
    def trigger_sync_now(self, config_id: str):
        """Trigger immediate sync for a platform"""
        job_id = f"sync_immediate_{config_id}"
        
        self.scheduler.add_job(
            func=self._run_sync,
            trigger="date",
            run_date=datetime.now(),
            id=job_id,
            kwargs={"config_id": config_id},
            replace_existing=True,
        )
        
        logger.info(f"Triggered immediate sync for config: {config_id}")


# ========== Global Functions ==========

def get_scheduler() -> "OrderSyncScheduler":
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = OrderSyncScheduler()
    return _scheduler


def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


# ========== Sync All Platforms (One-time) ==========

async def sync_all_now():
    """
    Run sync for all active platforms immediately (one-time)
    """
    db = SessionLocal()
    try:
        results = await sync_service.sync_all_platforms(db)
        
        for key, result in results.items():
            if result.get("status") == "success":
                logger.info(
                    f"[{key}] Sync success: fetched={result.get('fetched', 0)}, "
                    f"created={result.get('created', 0)}"
                )
            else:
                logger.error(f"[{key}] Sync failed: {result.get('error')}")
        
        return results
        
    finally:
        db.close()


# ========== CLI Commands ==========

if __name__ == "__main__":
    """
    Run scheduler standalone for testing:
    python -m app.jobs.order_sync
    """
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        # Run one-time sync
        asyncio.run(sync_all_now())
    else:
        # Start scheduler
        print("Starting order sync scheduler...")
        print("Press Ctrl+C to stop")
        
        try:
            start_scheduler()
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            stop_scheduler()
            print("Scheduler stopped")
