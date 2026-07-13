from django.contrib import admin
from .models import Docente, Curso, Participante, Inscripcion, CuentaCaja, MovimientoCaja, Cliente, ServicioConsultora, Honorario, Empleado, PagoSueldo, DatosEmpresa, Contador

admin.site.register(Docente)
admin.site.register(Curso)
admin.site.register(Participante)
admin.site.register(Inscripcion)

# Registramos las nuevas tablas de caja
admin.site.register(CuentaCaja)
admin.site.register(MovimientoCaja)
admin.site.register(Cliente)
admin.site.register(ServicioConsultora)
admin.site.register(Honorario)
# Eliminamos admin.site.register(Empleado) de aquí porque lo registramos abajo con más opciones
admin.site.register(PagoSueldo)

@admin.register(DatosEmpresa)
class DatosEmpresaAdmin(admin.ModelAdmin):
    # Columnas que se mostrarán en la lista del panel
    list_display = ('razon_social', 'nit', 'nro_ministerio', 'nro_caja_salud')
    
    # Evita que se puedan crear múltiples registros de configuración
    def has_add_permission(self, request):
        if DatosEmpresa.objects.exists():
            return False
        return True
    
@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    # Columnas que se verán en la lista principal de empleados
    list_display = ('nombre_completo', 'ci', 'codigo_rfid', 'cargo', 'fecha_ingreso', 'salario_base')
    
    # Buscador para encontrar empleados rápido
    search_fields = ('nombre_completo', 'ci', 'cargo')
    
    # Filtros laterales
    list_filter = ('sexo', 'cargo')

    # Organización de los campos al momento de crear/editar un empleado
    fieldsets = (
        ('Datos Laborales', {
            'fields': ('cargo', 'fecha_ingreso', 'salario_base')
        }),
        # --- AÑADE ESTE BLOQUE ---
        ('Horario y Control de Asistencia', {
            'fields': ('hora_ingreso', 'hora_salida', 'tolerancia_minutos', 'dias_laborales')
        }),
    )

@admin.register(Contador)
class ContadorAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo',)
    search_fields = ('nombre_completo',)