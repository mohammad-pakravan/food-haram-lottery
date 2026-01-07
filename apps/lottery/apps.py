from django.apps import AppConfig


class LotteryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.lottery'
    verbose_name = 'Lottery'
    
    def ready(self):
        """
        Start scheduler when app is ready
        Only in production or when explicitly enabled
        """
        import os
        from django.conf import settings
        
        # Only start scheduler if enabled
        if os.getenv('ENABLE_LOTTERY_SCHEDULER', 'False') == 'True':
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                # Log error but don't fail app startup
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to start lottery scheduler: {str(e)}")


