"""Time range utilities for ES-CLI."""
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict


class TimeRange:
    """Handles time range selection and conversion."""
    
    PRESETS = {
        'Last 15 minutes': timedelta(minutes=15),
        'Last 30 minutes': timedelta(minutes=30),
        'Last 1 hour': timedelta(hours=1),
        'Last 3 hours': timedelta(hours=3),
        'Last 6 hours': timedelta(hours=6),
        'Last 12 hours': timedelta(hours=12),
        'Last 24 hours': timedelta(hours=24),
        'Last 7 days': timedelta(days=7),
        'Last 30 days': timedelta(days=30),
    }
    
    DEFAULT_PRESET = 'Last 15 minutes'
    
    @staticmethod
    def get_time_range(preset: str = DEFAULT_PRESET) -> Tuple[datetime, datetime]:
        """Get time range from preset.
        
        Args:
            preset: Preset name (e.g., 'Last 6 hours')
            
        Returns:
            Tuple of (start_time, end_time)
        """
        if preset not in TimeRange.PRESETS:
            preset = TimeRange.DEFAULT_PRESET
        
        delta = TimeRange.PRESETS[preset]
        end_time = datetime.utcnow()
        start_time = end_time - delta
        
        return (start_time, end_time)
    
    @staticmethod
    def to_elasticsearch_format(start_time: datetime, end_time: datetime) -> Dict[str, str]:
        """Convert datetime objects to Elasticsearch format.
        
        Args:
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            Dict with 'gte' and 'lte' in ISO format
        """
        return {
            'gte': start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'lte': end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        }
