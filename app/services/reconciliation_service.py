"""
Reconciliation Service - Compare WeOrder vs Marketplace data
Detects missing orders and sync issues
"""
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.order import OrderHeader
from app.models.master import SalesChannel
from app.core.config import settings

import logging
logger = logging.getLogger(__name__)


class ReconciliationService:
    """
    Service to reconcile orders between WeOrder and Marketplace APIs
    """
    
    PLATFORMS = ['tiktok', 'shopee', 'lazada']
    
    @staticmethod
    def get_daily_summary(db: Session, target_date: date) -> Dict[str, Any]:
        """
        Get order counts from WeOrder database for a given date
        """
        start_dt = datetime.combine(target_date, time.min)
        end_dt = datetime.combine(target_date, time.max)
        
        # Count orders by platform and status
        result = db.query(
            OrderHeader.channel_code,
            OrderHeader.status_normalized,
            func.count(OrderHeader.id).label('count')
        ).filter(
            OrderHeader.order_datetime >= start_dt,
            OrderHeader.order_datetime <= end_dt
        ).group_by(
            OrderHeader.channel_code,
            OrderHeader.status_normalized
        ).all()
        
        summary = {}
        for channel, status, count in result:
            if channel not in summary:
                summary[channel] = {'total': 0, 'by_status': {}}
            summary[channel]['total'] += count
            summary[channel]['by_status'][status] = count
            
        return summary
    
    @staticmethod
    def get_sync_status(db: Session) -> Dict[str, Any]:
        """
        Get last sync time for each platform
        """
        sync_status = {}
        
        for platform in ReconciliationService.PLATFORMS:
            # Get most recent order for this platform
            last_order = db.query(OrderHeader).filter(
                OrderHeader.channel_code == platform
            ).order_by(OrderHeader.created_at.desc()).first()
            
            if last_order:
                sync_status[platform] = {
                    'last_order_synced': last_order.created_at.isoformat() if last_order.created_at else None,
                    'last_order_id': str(last_order.id),
                    'external_id': last_order.external_order_id,
                    'status': 'ok'
                }
                
                # Check if sync is stale (> 30 mins since last order in active hours)
                if last_order.created_at:
                    hours_ago = (datetime.now() - last_order.created_at.replace(tzinfo=None)).total_seconds() / 3600
                    if hours_ago > 0.5:  # 30 mins
                        sync_status[platform]['status'] = 'stale'
                    if hours_ago > 2:
                        sync_status[platform]['status'] = 'warning'
            else:
                sync_status[platform] = {
                    'last_order_synced': None,
                    'last_order_id': None,
                    'status': 'no_data'
                }
                
        return sync_status
    
    @staticmethod
    async def compare_with_marketplace(
        db: Session, 
        platform: str, 
        target_date: date
    ) -> Dict[str, Any]:
        """
        Compare WeOrder orders with Marketplace API for a given date
        Returns differences and missing orders
        """
        from app.integrations.tiktok import TikTokClient
        from app.integrations.shopee import ShopeeClient
        from app.integrations.lazada import LazadaClient
        
        start_dt = datetime.combine(target_date, time.min)
        end_dt = datetime.combine(target_date, time.max)
        
        # Get WeOrder orders
        weorder_orders = db.query(OrderHeader).filter(
            OrderHeader.channel_code == platform,
            OrderHeader.order_datetime >= start_dt,
            OrderHeader.order_datetime <= end_dt
        ).all()
        
        weorder_ids = {o.external_order_id for o in weorder_orders}
        
        # Get channel config
        channel = db.query(ChannelConfig).filter(
            ChannelConfig.platform == platform,
            ChannelConfig.is_active == True
        ).first()
        
        if not channel:
            return {
                'platform': platform,
                'date': target_date.isoformat(),
                'error': f'No active channel config for {platform}',
                'weorder_count': len(weorder_ids),
                'marketplace_count': 0,
                'missing': []
            }
        
        # Initialize client and fetch orders from marketplace
        marketplace_ids = set()
        missing_orders = []
        
        try:
            if platform == 'tiktok':
                client = TikTokClient(channel)
                # Fetch orders from TikTok for this date range
                orders = await client.get_orders(
                    start_time=int(start_dt.timestamp()),
                    end_time=int(end_dt.timestamp())
                )
                marketplace_ids = {o.get('order_id') for o in orders}
                
            elif platform == 'shopee':
                client = ShopeeClient(channel)
                orders = await client.get_orders(
                    start_time=int(start_dt.timestamp()),
                    end_time=int(end_dt.timestamp())
                )
                marketplace_ids = {o.get('order_sn') for o in orders}
                
            elif platform == 'lazada':
                client = LazadaClient(channel)
                orders = await client.get_orders(
                    start_time=start_dt.isoformat(),
                    end_time=end_dt.isoformat()
                )
                marketplace_ids = {str(o.get('order_id')) for o in orders}
            
            # Find missing orders (in marketplace but not in WeOrder)
            missing_ids = marketplace_ids - weorder_ids
            
            return {
                'platform': platform,
                'date': target_date.isoformat(),
                'weorder_count': len(weorder_ids),
                'marketplace_count': len(marketplace_ids),
                'missing_count': len(missing_ids),
                'missing_ids': list(missing_ids)[:50],  # Limit to 50
                'match_rate': round(len(weorder_ids) / max(len(marketplace_ids), 1) * 100, 1),
                'status': 'ok' if len(missing_ids) == 0 else 'warning'
            }
            
        except Exception as e:
            logger.error(f"Reconciliation error for {platform}: {e}")
            return {
                'platform': platform,
                'date': target_date.isoformat(),
                'error': str(e),
                'weorder_count': len(weorder_ids),
                'marketplace_count': 0,
                'missing': []
            }
    
    @staticmethod
    def get_recent_gaps(db: Session, days: int = 7) -> Dict[str, Any]:
        """
        Check for date gaps or anomalies in order data over last N days
        """
        today = date.today()
        gaps = []
        
        for i in range(days):
            check_date = today - timedelta(days=i)
            daily = ReconciliationService.get_daily_summary(db, check_date)
            
            for platform in ReconciliationService.PLATFORMS:
                if platform in daily:
                    count = daily[platform]['total']
                    # Flag if count is unusually low (< 10% of average)
                    # This is a simple heuristic - can be improved
                    if count == 0:
                        gaps.append({
                            'date': check_date.isoformat(),
                            'platform': platform,
                            'count': count,
                            'issue': 'no_orders'
                        })
                        
        return {
            'checked_days': days,
            'gaps_found': len(gaps),
            'gaps': gaps
        }
    
    @staticmethod
    def get_health_dashboard(db: Session) -> Dict[str, Any]:
        """
        Get overall sync health for dashboard widget
        """
        sync_status = ReconciliationService.get_sync_status(db)
        today_summary = ReconciliationService.get_daily_summary(db, date.today())
        gaps = ReconciliationService.get_recent_gaps(db, days=3)
        
        # Calculate overall health
        issues = []
        for platform, status in sync_status.items():
            if status['status'] != 'ok':
                issues.append(f"{platform}: {status['status']}")
        
        if gaps['gaps_found'] > 0:
            issues.append(f"Found {gaps['gaps_found']} data gaps in last 3 days")
        
        overall_status = 'healthy' if not issues else ('warning' if len(issues) < 3 else 'critical')
        
        return {
            'overall_status': overall_status,
            'sync_status': sync_status,
            'today_summary': today_summary,
            'issues': issues,
            'checked_at': datetime.now().isoformat()
        }
