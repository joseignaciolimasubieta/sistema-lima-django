from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views 

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'), 
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.portal_inicio, name='portal_inicio'),
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('participantes/', views.participantes, name='participantes'), 
    path('participantes/nuevo/', views.crear_participante, name='crear_participante'), 
    path('docentes/nuevo/', views.crear_docente, name='crear_docente'), 
    path('cursos/', views.cursos, name='cursos'), 
    path('cursos/<int:curso_id>/alumnos/', views.detalle_curso, name='detalle_curso'), 
    path('cursos/<int:curso_id>/pdf/', views.descargar_pdf_asistencia, name='descargar_pdf_asistencia'), 
    path('cursos/nuevo/', views.crear_curso, name='crear_curso'), 
    path('cursos/editar/<int:id>/', views.editar_curso, name='editar_curso'),
    path('cursos/eliminar/<int:id>/', views.eliminar_curso, name='eliminar_curso'),
    path('certificado/individual/<int:inscripcion_id>/', views.generar_certificado_individual, name='generar_certificado_individual'),
    path('inscripciones/', views.inscripciones, name='inscripciones'), 
    path('inscripciones/nuevo/', views.crear_inscripcion, name='crear_inscripcion'), 
    path('marketing/', views.marketing, name='marketing'),
    path('marketing/', views.marketing, name='marketing'),
    path('marketing/eliminar-afiche/<int:curso_id>/', views.eliminar_afiche_marketing, name='eliminar_afiche_marketing'), # <-- NUEVA RUTA AÑADIDA
    path('marketing/confirmar/<int:curso_id>/', views.confirmar_publicacion, name='confirmar_publicacion'), 
   # --- NUEVO MÓDULO DE CERTIFICADOS INDEPENDIENTE ---
    path('certificados/', views.lista_cursos_certificados, name='lista_cursos_certificados'),
    path('certificados/<int:curso_id>/', views.detalle_curso_certificados, name='detalle_curso_certificados'),
    # NUEVA RUTA PARA EL ENVÍO INDIVIDUAL
    path('certificado/individual/enviar/<int:inscripcion_id>/', views.enviar_certificado_individual, name='enviar_certificado_individual'),
    path('informacion-cursos/', views.informacion_cursos, name='informacion_cursos'),
    # ... otras rutas ...
    path('api/certificados/alumnos/<int:curso_id>/', views.api_obtener_alumnos_correo, name='api_obtener_alumnos_correo'),
    path('api/certificados/enviar/<int:inscripcion_id>/', views.api_enviar_certificado_js, name='api_enviar_certificado_js'),
    path('api/certificados/marcar/<int:curso_id>/', views.api_marcar_curso_enviado, name='api_marcar_curso_enviado'),

    # --- PORTAL PÚBLICO DE DESCARGAS ---
    path('mis-certificados/', views.portal_buscar_certificado, name='portal_buscar_certificado'),
    path('mis-certificados/descargar/<int:inscripcion_id>/', views.descargar_certificado_publico, name='descargar_certificado_publico'),

    # --- MÓDULO DE CITAS CONSULTORA ---
    path('consultora/citas/', views.citas_consultora, name='citas_consultora'),
    path('consultora/citas/guardar/', views.guardar_cita, name='guardar_cita'),
    path('consultora/citas/estado/<int:cita_id>/<str:nuevo_estado>/', views.cambiar_estado_cita, name='cambiar_estado_cita'),
    path('consultora/citas/eliminar/<int:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
    path('consultora/citas/boleta/<int:cita_id>/', views.imprimir_boleta_cita, name='imprimir_boleta_cita'),

    # --- MÓDULO DE ARCHIVO DIGITAL (DRIVE) ---
    path('consultora/archivo/', views.archivo_digital, name='archivo_digital'),
    path('consultora/archivo/guardar/', views.guardar_archivo, name='guardar_archivo'),
    path('consultora/archivo/eliminar/<int:archivo_id>/', views.eliminar_archivo, name='eliminar_archivo'),
    
    # --- MÓDULO DE CUENTAS POR COBRAR ---
    path('inscripciones/cuentas-por-cobrar/', views.cuentas_por_cobrar, name='cuentas_por_cobrar'), 
    path('inscripciones/cuentas-por-cobrar/cobrar/<int:id>/', views.liquidar_saldo_inscripcion, name='liquidar_saldo_inscripcion'),
    path('inscripciones/cuentas-por-cobrar/nuevo/', views.crear_inscripcion_cc, name='crear_inscripcion_cc'),
    path('inscripciones/cuentas-por-cobrar/editar/<int:id>/', views.editar_inscripcion_cc, name='editar_inscripcion_cc'),
    
    path('ventas/nueva/', views.crear_venta_servicio, name='crear_venta_servicio'), 
    path('ventas/editar/<int:id>/', views.editar_venta_servicio, name='editar_venta_servicio'), 
    path('ventas/eliminar/<int:id>/', views.eliminar_venta_servicio, name='eliminar_venta_servicio'), 
    path('caja/', views.flujo_caja, name='flujo_caja'), 
    path('caja/nuevo/', views.crear_movimiento, name='crear_movimiento'), 
    path('caja/exportar/excel/', views.exportar_excel_caja, name='exportar_excel_caja'), 
    path('arqueo/', views.arqueo_caja, name='arqueo_caja'),
    path('arqueos/historial/', views.historial_arqueos, name='historial_arqueos'),
    path('arqueos/eliminar/<int:arqueo_id>/', views.eliminar_arqueo, name='eliminar_arqueo'),
    path('consultora/', views.consultora, name='consultora'), 
    path('consultora/nuevo/', views.crear_servicio, name='crear_servicio'), 
    path('honorarios/', views.honorarios, name='honorarios'), 
    path('inscripciones/recibo/<int:inscripcion_id>/', views.imprimir_recibo, name='imprimir_recibo'), 
    path('rrhh/planillas/', views.planillas, name='planillas'), 
    path('rrhh/planillas/boletas/', views.buscar_boletas, name='buscar_boletas'), 
    path('rrhh/planillas/nuevo/', views.crear_pago, name='crear_pago'), 
    path('honorarios/<int:honorario_id>/anticipo/', views.registrar_anticipo, name='registrar_anticipo'), 
    path('honorarios/<int:honorario_id>/pagar/', views.pagar_honorario, name='pagar_honorario'), 
    path('caja/editar/<int:movimiento_id>/', views.editar_movimiento, name='editar_movimiento'), 
    path('consultora/editar/<int:servicio_id>/', views.editar_servicio, name='editar_servicio'), 
    path('consultora/eliminar-servicio/<int:servicio_id>/', views.eliminar_servicio, name='eliminar_servicio'),
    path('inscripciones/editar/<int:id>/', views.editar_inscripcion, name='editar_inscripcion'), 
    path('inscripciones/eliminar/<int:id>/', views.eliminar_inscripcion, name='eliminar_inscripcion'), 
    path('asistencia/toggle/', views.toggle_asistencia, name='toggle_asistencia'), 
    path('cursos/<int:curso_id>/certificados/', views.generar_certificados_curso, name='generar_certificados_curso'), 
    path('planillas/pdf/', views.descargar_pdf_planilla, name='descargar_pdf_planilla'), 
    path('empleado/<int:empleado_id>/datos_pago/', views.obtener_datos_empleado_pago, name='datos_empleado_pago'), 
    path('planillas/eliminar-pago/<int:pago_id>/', views.eliminar_pago, name='eliminar_pago'), 
    path('planillas/editar-pago/<int:pago_id>/', views.editar_pago, name='editar_pago'), 
    path('rrhh/anticipos/', views.lista_anticipos, name='lista_anticipos'),
    path('rrhh/anticipos/nuevo/', views.crear_anticipo, name='crear_anticipo'),
    path('rrhh/anticipos/eliminar/<int:anticipo_id>/', views.eliminar_anticipo, name='eliminar_anticipo'),
    path('consultora/crear-cliente/', views.crear_cliente, name='crear_cliente'), 
    path('api/buscar-cliente/', views.api_buscar_cliente, name='api_buscar_cliente'), 
    # --- MÓDULO DE CONTROL DE ASISTENCIA ---
    path('api/asistencia/rfid/', views.registrar_asistencia_rfid, name='registrar_asistencia_rfid'),
    path('empleados/asistencia/', views.asistencia_empleados, name='asistencia_empleados'),
    path('empleados/configuracion/', views.configuracion_empleados, name='configuracion_empleados'),
    
    # --- MÓDULO DE PRÉSTAMOS Y FINANCIERA ---
    path('financiera/prestamos/', views.lista_prestamos, name='lista_prestamos'), 
    path('financiera/prestamos/nuevo/', views.crear_prestamo, name='crear_prestamo'), 
    path('financiera/prestamos/<int:prestamo_id>/pagar/', views.registrar_pago_prestamo, name='registrar_pago_prestamo'), 
    path('financiera/prestamos/<int:prestamo_id>/editar/', views.editar_prestamo, name='editar_prestamo'),
    path('planillas/boleta/<int:pago_id>/', views.imprimir_boleta, name='imprimir_boleta'),     
    path('financiera/prestamos/recibo/<int:pago_id>/', views.imprimir_recibo_pago, name='imprimir_recibo_pago'), 
    path('consultora/eliminar-cliente/<int:cliente_id>/', views.eliminar_cliente, name='eliminar_cliente'), 

    # --- API DE NOTIFICACIONES ---
    path('api/notificaciones/', views.api_notificaciones, name='api_notificaciones'),
    
    # --- MÓDULO DE TAREAS KANBAN ---
    path('administracion/tareas/', views.lista_tareas, name='lista_tareas'),
    path('administracion/tareas/nueva/', views.crear_tarea, name='crear_tarea'),
    path('administracion/tareas/estado/<int:tarea_id>/', views.cambiar_estado_tarea, name='cambiar_estado_tarea'),
    path('administracion/tareas/eliminar/<int:tarea_id>/', views.eliminar_tarea, name='eliminar_tarea'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)