import os
from celery import Celery

# Cambiamos 'nombre_de_tu_proyecto' por 'core'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Carga la configuración desde tu settings.py usando el prefijo 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()