from django.apps import AppConfig


class JobPipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.job_pipeline'
    verbose_name = 'Job Pipeline'
    
    def ready(self):
        import apps.job_pipeline.signals