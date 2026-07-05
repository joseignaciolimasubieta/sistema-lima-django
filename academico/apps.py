from django.apps import AppConfig
import os

class AcademicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'academico'

    def ready(self):
        # Esta condición evita que el reloj se inicie dos veces cuando haces pruebas
        if os.environ.get('RUN_MAIN') == 'true':
            from . import tareas_programadas
            tareas_programadas.iniciar_programador()