from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date
from django.db.models import Sum
from .models import Inscripcion, MovimientoCaja, CuentaCaja

def tarea_cierre_automatico():
    print("Iniciando Cierre de Caja Automático...")
    hoy = date.today()
    
    # 1. SEGURIDAD: Verificar si ya se hizo el cierre hoy (evita duplicados)
    if MovimientoCaja.objects.filter(fecha=hoy, detalle__startswith="CIERRE DIARIO").exists():
        print("El cierre de hoy ya fue realizado. Cancelando tarea.")
        return
        
    # 2. Buscar inscripciones de hoy
    inscripciones_hoy = Inscripcion.objects.filter(fecha_inscripcion=hoy)
    if not inscripciones_hoy.exists():
        print("No hubo inscripciones hoy. Nada que cerrar.")
        return

    # 3. Resumir dinero
    resumen = inscripciones_hoy.values('modalidad', 'forma_pago').annotate(total=Sum('importe'))
    
    try:
        cuenta_admin = CuentaCaja.objects.get(codigo='001')
        cuenta_banco = CuentaCaja.objects.get(codigo='002')
    except CuentaCaja.DoesNotExist:
        print("Error crítico: No existen las cuentas 001 o 002.")
        return

    # 4. Inyectar al flujo de caja
    for item in resumen:
        total = item['total']
        if total and total > 0:
            forma_pago = item['forma_pago']
            modalidad = item['modalidad']
            cuenta_destino = cuenta_banco if forma_pago.upper() == 'DEPÓSITO' else cuenta_admin
            
            MovimientoCaja.objects.create(
                fecha=hoy,
                detalle=f"CIERRE DIARIO AUTOMÁTICO: INGRESOS {modalidad} ({forma_pago})",
                cuenta=cuenta_destino,
                tipo='ENTRADA',
                monto=total
            )
    print("¡Cierre Automático completado con éxito!")

def iniciar_programador():
    # Configuramos el reloj con la hora de Bolivia (La Paz)
    scheduler = BackgroundScheduler(timezone="America/La_Paz")
    
    # Le decimos que ejecute la tarea todos los días a las 23:59
    scheduler.add_job(tarea_cierre_automatico, 'cron', hour=23, minute=59)
    
    scheduler.start()