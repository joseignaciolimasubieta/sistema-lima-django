from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

class Docente(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Curso(models.Model):
    nombre = models.CharField(max_length=200)
    mes_curso = models.CharField(max_length=50)
    turno = models.CharField(max_length=50)
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    
    # --- NUEVOS CAMPOS DEL EXCEL ---
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_finalizacion = models.DateField(null=True, blank=True)
    horario = models.CharField(max_length=100, null=True, blank=True)
    dias = models.CharField(max_length=100, null=True, blank=True) # Ej: Lunes a Jueves
    duracion = models.CharField(max_length=200, null=True, blank=True) # Ej: 2 Semanas, 8 Sesiones
    modalidad = models.CharField(max_length=50, null=True, blank=True)
    # ==============================================================
    # --- NUEVO: ENLACE PARA CREAR MÓDULOS (PADRE E HIJO) ---
    # ==============================================================
    modulo_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcursos')
    
    # Precios
    inversion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    antiguos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # --- NUEVO CAMPO PARA MARKETING ---
    imagen_publicidad = models.ImageField(upload_to='marketing/', null=True, blank=True)
    # ==============================================================
    # --- NUEVO: CONTROL DE ENVÍO DE CERTIFICADOS ---
    # ==============================================================
    certificados_enviados = models.BooleanField(default=False)
    fecha_envio_certificados = models.DateField(null=True, blank=True)

    @property
    def estado(self):
        hoy = date.today()
        # Si el curso tiene fechas registradas, calcula el estado
        if self.fecha_inicio and self.fecha_finalizacion:
            if hoy < self.fecha_inicio:
                return 'NO INICIÓ'
            elif self.fecha_inicio <= hoy <= self.fecha_finalizacion:
                return 'EN CURSO'
            else:
                return 'FINALIZADO'
        # Si no tiene fechas, muestra esto por defecto
        return 'SIN FECHAS'
    
    def __str__(self):
        return f"{self.nombre} - {self.mes_curso}"

class Participante(models.Model):
    nombre_completo = models.CharField(max_length=255)
    celular = models.CharField(max_length=20)

    def __str__(self):
        return self.nombre_completo

class Inscripcion(models.Model):
    participante = models.ForeignKey(Participante, on_delete=models.PROTECT)
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT)
    fecha_inscripcion = models.DateField()
    modalidad = models.CharField(max_length=50, default='VIRTUAL')
    banco = models.CharField(max_length=50)
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    
    # --- MÓDULO DE CUENTAS POR COBRAR ---
    saldo_pendiente = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    registrado_por = models.CharField(max_length=100, blank=True, null=True)
    forma_pago = models.CharField(max_length=50, default='Efectivo') 
    vendedor = models.CharField(max_length=100, default='Administración')

    @property
    def comision(self):
        from decimal import Decimal
        return self.importe * Decimal('0.10')

    # ==============================================================
    # --- CEREBRO AUTOCURABLE PARA EL FLUJO DE CAJA (NUEVO) ---
    # ==============================================================
    def sincronizar_caja_inscripciones(self):
        from django.db.models import Sum
        from decimal import Decimal
        
        # 1. Definir la cuenta de destino (Caja o Banco)
        banco_limpio = str(self.banco).strip().upper() if self.banco else ''
        codigo_cuenta = '001' if banco_limpio in ['ADMINISTRACIÓN', 'ADMINISTRACION', 'EFECTIVO', '001 - ADMINISTRACIÓN'] else '002'
        nombre_cuenta = 'ADMINISTRACIÓN' if codigo_cuenta == '001' else 'BANCO'
        cuenta_destino, _ = CuentaCaja.objects.get_or_create(codigo=codigo_cuenta, defaults={'nombre': nombre_cuenta})
        
        # --- 🧹 LIMPIEZA DE REGISTROS FANTASMAS ---
        # Destruimos permanentemente cualquier registro que haya quedado atascado 
        # con la antigua automatización en este día específico y cuenta.
        MovimientoCaja.objects.filter(
            fecha=self.fecha_inscripcion,
            cuenta=cuenta_destino,
            detalle__icontains='CIERRE DIARIO'
        ).delete()
        # ------------------------------------------

        # 2. Lógica de Agrupación (Separamos Anticipos de Pagos Completos)
        if self.saldo_pendiente > 0:
            detalle_diario = "ANTICIPO DE INSCRIPCIÓN"
            inscripciones_grupo = Inscripcion.objects.filter(
                fecha_inscripcion=self.fecha_inscripcion,
                banco=self.banco,
                saldo_pendiente__gt=0
            )
        else:
            detalle_diario = str(self.modalidad).strip().upper() if self.modalidad else 'VIRTUAL'
            inscripciones_grupo = Inscripcion.objects.filter(
                fecha_inscripcion=self.fecha_inscripcion,
                banco=self.banco,
                modalidad=self.modalidad,
                saldo_pendiente=0
            )

        # 3. Sumar todo el dinero de ESE DÍA bajo ESE CONCEPTO exacto
        total_agrupado = inscripciones_grupo.aggregate(total=Sum('importe'))['total'] or Decimal('0.00')

        # 4. Buscar el registro maestro en el Flujo de Caja
        movimiento = MovimientoCaja.objects.filter(
            fecha=self.fecha_inscripcion,
            cuenta=cuenta_destino,
            detalle=detalle_diario,
            tipo='ENTRADA'
        ).first()

        # 5. Magia de Ajuste Automático (Actualiza, Crea o Destruye)
        if total_agrupado > 0:
            if movimiento:
                movimiento.monto = total_agrupado
                movimiento.save()
            else:
                MovimientoCaja.objects.create(
                    fecha=self.fecha_inscripcion,
                    detalle=detalle_diario,
                    cuenta=cuenta_destino,
                    tipo='ENTRADA',
                    monto=total_agrupado
                )
        else:
            if movimiento:
                movimiento.delete() # Si se eliminan todas las inscripciones del día, borra la fila limpia

    def save(self, *args, **kwargs):
        # 1. Guardamos la inscripción primero
        super().save(*args, **kwargs)
        
        # 2. Obligamos al Flujo de Caja a recalcular ese día
        self.sincronizar_caja_inscripciones()

    def delete(self, *args, **kwargs):
        # 1. Capturamos los datos vitales antes de que el alumno desaparezca
        f_temp = self.fecha_inscripcion
        b_temp = self.banco
        m_temp = self.modalidad
        s_temp = self.saldo_pendiente
        
        # 2. Destruimos la inscripción de la base de datos
        super().delete(*args, **kwargs)
        
        # 3. Usamos un "fantasma" para decirle a la Caja que revise las sumas de ese día.
        # Al revisar y no encontrar esta inscripción, le restará el dinero o borrará la fila.
        fantasma = Inscripcion(
            fecha_inscripcion=f_temp, 
            banco=b_temp, 
            modalidad=m_temp, 
            saldo_pendiente=s_temp
        )
        fantasma.sincronizar_caja_inscripciones()

class CuentaCaja(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class MovimientoCaja(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada (Ingreso)'),
        ('SALIDA', 'Salida (Egreso)'),
    ]
    fecha = models.DateField()
    detalle = models.CharField(max_length=255)
    cuenta = models.ForeignKey(CuentaCaja, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.fecha} - {self.detalle} - {self.tipo}"

class Cliente(models.Model):
    # Razón Social reemplaza conceptualmente al antiguo nombre_contribuyente
    nombre_contribuyente = models.CharField(max_length=200, verbose_name="Razón Social")
    nit = models.CharField(max_length=50, blank=True, null=True, verbose_name="NIT")
    celular = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    
    # --- NUEVOS CAMPOS DEL REGISTRO ---
    domicilio_fiscal = models.CharField(max_length=255, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    contrasena = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contraseña")
    denominacion = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.nombre_contribuyente

class ServicioConsultora(models.Model):
    fecha = models.DateField()
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Cliente")
    servicio = models.CharField(max_length=100)
    periodo = models.CharField(max_length=100, blank=True, null=True)
    factura = models.CharField(max_length=100, blank=True, null=True)
    archivo_factura = models.FileField(upload_to='facturas/', blank=True, null=True, verbose_name="Archivo de Factura")
    forma_pago = models.CharField(max_length=100, blank=True, null=True)
    banco = models.CharField(max_length=100, blank=True, null=True)
    importe = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    contador = models.ForeignKey('Contador', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Contador Asignado")
    comision = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    observaciones = models.CharField(max_length=200, blank=True, null=True)

    # ==============================================================
    # --- CEREBRO AUTOCURABLE PARA EL FLUJO DE CAJA (NUEVO) ---
    # ==============================================================
    def sincronizar_caja_consultora(self):
        from django.db.models import Sum
        from decimal import Decimal
        
        # 1. Definir cuenta de destino
        banco_limpio = str(self.banco).strip().upper() if self.banco else ''
        codigo_cuenta = '001' if banco_limpio in ['ADMINISTRACIÓN', 'ADMINISTRACION', 'EFECTIVO', '001 - ADMINISTRACIÓN'] else '002'
        nombre_cuenta = 'ADMINISTRACIÓN' if codigo_cuenta == '001' else 'BANCO'
        cuenta_destino, _ = CuentaCaja.objects.get_or_create(codigo=codigo_cuenta, defaults={'nombre': nombre_cuenta})
        
        detalle_diario = str(self.servicio).strip().upper() if self.servicio else 'SERVICIO'

        # 2. Sumamos todo el dinero de ESE MISMO DÍA y ESE MISMO SERVICIO
        servicios_del_dia = ServicioConsultora.objects.filter(
            fecha=self.fecha,
            servicio=self.servicio,
            banco=self.banco
        )
        total_agrupado = servicios_del_dia.aggregate(total=Sum('importe'))['total'] or Decimal('0.00')

        # 3. Buscamos el registro en el Flujo de Caja
        movimiento = MovimientoCaja.objects.filter(
            fecha=self.fecha,
            cuenta=cuenta_destino,
            detalle=detalle_diario,
            tipo='ENTRADA'
        ).first()

        # 4. Magia de Ajuste Automático
        if total_agrupado > 0:
            if movimiento:
                movimiento.monto = total_agrupado
                movimiento.save() # Si quedan 9 servicios, baja el monto
            else:
                MovimientoCaja.objects.create(
                    fecha=self.fecha,
                    detalle=detalle_diario,
                    cuenta=cuenta_destino,
                    tipo='ENTRADA',
                    monto=total_agrupado
                ) # Si era nuevo, lo crea
        else:
            if movimiento:
                movimiento.delete() # Si llega a Bs. 0 (o borramos el último), destruye la fila por completo

    def save(self, *args, **kwargs):
        from decimal import Decimal
        
        # 1. Calculamos la comisión obligatoria del 50%
        if self.importe:
            self.comision = Decimal(str(self.importe)) * Decimal('0.50')
        else:
            self.comision = Decimal('0.00')

        # 2. Guardamos la consulta primero
        super().save(*args, **kwargs) 
        
        # 3. Obligamos al Flujo de Caja a recalcular
        self.sincronizar_caja_consultora()

    def delete(self, *args, **kwargs):
        # 1. Capturamos los datos base antes de que el registro desaparezca
        f_temp = self.fecha
        s_temp = self.servicio
        b_temp = self.banco
        
        # 2. Destruimos el registro permanentemente
        super().delete(*args, **kwargs)
        
        # 3. Usamos un "fantasma" para decirle a Caja que revise el día. 
        # (Al revisar el día sin este registro, el sistema descontará el monto o eliminará la fila)
        fantasma = ServicioConsultora(fecha=f_temp, servicio=s_temp, banco=b_temp)
        fantasma.sincronizar_caja_consultora()

class Honorario(models.Model):
    # Relación con el curso (y a través del curso, con el docente)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, null=True, blank=True)    
    # Nuevos campos extraídos del Excel
    carga = models.CharField(max_length=100, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    
    # Finanzas y montos
    monto_acordado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    anticipo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fecha_anticipo = models.DateField(null=True, blank=True)
    
    # Estados y cierres de pago
    estado = models.CharField(max_length=20, default='PENDIENTE') # 'PENDIENTE' o 'PAGADO'
    fecha_pago = models.DateField(null=True, blank=True)
    modo_pago = models.CharField(max_length=50, null=True, blank=True) # Ejemplo: Efectivo, Transferencia
    realizado_por = models.CharField(max_length=100, null=True, blank=True) # Quién registró el pago

    # Propiedades calculadas automáticas para el HTML
    @property
    def honorario_total(self):
        return self.monto_acordado

    @property
    def saldo(self):
        return self.monto_acordado - self.anticipo

    def __str__(self):
        return f"Honorario: {self.curso.nombre} - {self.monto_acordado} Bs."

class Empleado(models.Model):
    SEXO_CHOICES = [
        ('F', 'Femenino'),
        ('M', 'Masculino'),
    ]

    nombre_completo = models.CharField(max_length=200, verbose_name="Apellidos y Nombres")
    ci = models.CharField(max_length=20, verbose_name="Documento de Identidad")
    codigo_rfid = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código Tarjeta RFID")
    celular = models.CharField(max_length=20, blank=True, null=True)
    
    # Nuevos campos obligatorios para la planilla
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, default='M', verbose_name="Sexo (F/M)")
    cargo = models.CharField(max_length=150, verbose_name="Ocupación que desempeña")
    fecha_ingreso = models.DateField(blank=True, null=True, verbose_name="Fecha de Ingreso")
    salario_base = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Haber Básico Acordado")

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"

    def __str__(self):
        return self.nombre_completo

class PagoSueldo(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_pago = models.DateField()
    mes_correspondiente = models.CharField(max_length=50) # Ej. "2026-06"
    cuenta_origen = models.ForeignKey(CuentaCaja, on_delete=models.PROTECT, null=True, blank=True)
    
    # --- INGRESOS ---
    salario_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bono_antiguedad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bono_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    comisiones_certificados = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bono_consultora = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    otros_bonos = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # --- EGRESOS ---
    aportes_afp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rc_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    anticipos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prestamos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    multas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rendicion_cuentas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pasanaku = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # --- MATEMÁTICA ---
    @property
    def total_otros_bonos(self):
        return self.comisiones_certificados + self.bono_consultora + self.otros_bonos

    @property
    def total_ganado(self):
        return self.salario_base + self.bono_antiguedad + self.bono_ventas + self.total_otros_bonos

    @property
    def total_otros_descuentos(self):
        return self.anticipos + self.prestamos + self.multas + self.rendicion_cuentas + self.pasanaku

    @property
    def total_descuentos(self):
        return self.aportes_afp + self.rc_iva + self.total_otros_descuentos

    @property
    def liquido_pagable(self):
        return self.total_ganado - self.total_descuentos

    def __str__(self):
        return f"Pago a {self.empleado.nombre_completo} - {self.mes_correspondiente}"

    # ====================================================================
    # --- CEREBRO UNIFICADO DE AGRUPACIÓN (CAJA Y PRÉSTAMOS) ---
    # ====================================================================
    
    def get_detalle_mes_formateado(self):
        # Diccionario traductor para el Flujo de Caja
        meses = {
            '01': 'ENERO', '02': 'FEBRERO', '03': 'MARZO',
            '04': 'ABRIL', '05': 'MAYO', '06': 'JUNIO',
            '07': 'JULIO', '08': 'AGOSTO', '09': 'SEPTIEMBRE',
            '10': 'OCTUBRE', '11': 'NOVIEMBRE', '12': 'DICIEMBRE'
        }
        try:
            anio, mes = str(self.mes_correspondiente).strip().split('-')
            nombre_mes = meses.get(mes, '')
            return f"SUELDOS {nombre_mes} {anio}".strip()
        except:
            return f"SUELDOS {str(self.mes_correspondiente).upper()}"

    def sincronizar_caja_sueldos(self):
        from decimal import Decimal
        
        # 1. Formateamos el texto a "SUELDOS JULIO 2026"
        meses_dict = {
            '01': 'ENERO', '02': 'FEBRERO', '03': 'MARZO', '04': 'ABRIL',
            '05': 'MAYO', '06': 'JUNIO', '07': 'JULIO', '08': 'AGOSTO',
            '09': 'SEPTIEMBRE', '10': 'OCTUBRE', '11': 'NOVIEMBRE', '12': 'DICIEMBRE'
        }
        try:
            anio, mes = str(self.mes_correspondiente).strip().split('-')
            mes_literal = f"{meses_dict.get(mes, '')} {anio}"
        except:
            mes_literal = str(self.mes_correspondiente).upper()
            
        detalle_maestro = f"SUELDOS {mes_literal}"

        # 2. LIMPIEZA: Borramos los registros agrupados de este mes en Caja
        MovimientoCaja.objects.filter(
            tipo='SALIDA',
            detalle=detalle_maestro
        ).delete()

        # 3. RECALCULO Y AGRUPACIÓN: Sumamos el dinero separándolo por cuenta (Caja, Banco, etc.)
        pagos_del_mes = PagoSueldo.objects.filter(mes_correspondiente=self.mes_correspondiente)
        
        totales_por_cuenta = {}
        for pago in pagos_del_mes:
            cuenta_real = pago.cuenta_origen
            if not cuenta_real:
                cuenta_real = CuentaCaja.objects.filter(codigo='001').first()
                
            if not cuenta_real:
                continue # Evita errores si no hay cuentas creadas en la base de datos
                
            if cuenta_real.id not in totales_por_cuenta:
                totales_por_cuenta[cuenta_real.id] = {
                    'cuenta': cuenta_real,
                    'total': Decimal('0.00'),
                    'fecha': pago.fecha_pago 
                }
            totales_por_cuenta[cuenta_real.id]['total'] += pago.liquido_pagable

        # 4. GUARDAR: Insertamos el resumen limpio en el Flujo de Caja
        for data in totales_por_cuenta.values():
            if data['total'] > 0:
                MovimientoCaja.objects.create(
                    fecha=data['fecha'],
                    detalle=detalle_maestro,
                    cuenta=data['cuenta'],
                    tipo='SALIDA',
                    monto=data['total']
                )

    def save(self, *args, **kwargs):
        from decimal import Decimal
        es_nuevo = self.pk is None 
        super().save(*args, **kwargs) 
        
        self.sincronizar_caja_sueldos()
        
        # Amortiza el Préstamo
        if es_nuevo and self.prestamos > 0:
            monto_a_descontar = Decimal(str(self.prestamos))
            prestamos_activos = Prestamo.objects.filter(empleado=self.empleado, estado='ACTIVO').order_by('fecha_prestamo')
            for p in prestamos_activos:
                if monto_a_descontar <= 0:
                    break
                abono = min(monto_a_descontar, p.saldo_restante)
                if abono > 0:
                    PagoPrestamo.objects.create(prestamo=p, fecha_pago=self.fecha_pago, monto=abono, es_descuento_planilla=True)
                    monto_a_descontar -= abono

        # ==============================================================
        # --- NUEVA AUTOMATIZACIÓN: CERRAR ANTICIPOS DEL MES ---
        # ==============================================================
        if es_nuevo and self.anticipos > 0:
            anticipos_pendientes = AnticipoEmpleado.objects.filter(
                empleado=self.empleado, 
                mes_descuento=self.mes_correspondiente, 
                estado='PENDIENTE'
            )
            for ant in anticipos_pendientes:
                ant.estado = 'DESCONTADO'
                ant.save()
    @property
    def mes_literal(self):
        meses = {
            '01': 'ENERO', '02': 'FEBRERO', '03': 'MARZO',
            '04': 'ABRIL', '05': 'MAYO', '06': 'JUNIO',
            '07': 'JULIO', '08': 'AGOSTO', '09': 'SEPTIEMBRE',
            '10': 'OCTUBRE', '11': 'NOVIEMBRE', '12': 'DICIEMBRE'
        }
        try:
            # Descompone "2026-06" en año y mes
            anio, mes_num = str(self.mes_correspondiente).strip().split('-')
            return f"{meses.get(mes_num, '')} {anio}"
        except:
            return str(self.mes_correspondiente).upper()

    def delete(self, *args, **kwargs):
        mes_temporal = self.mes_correspondiente
        
        try:
            # Reversión segura del préstamo
            if self.prestamos > 0:
                pagos_prestamo = PagoPrestamo.objects.filter(
                    prestamo__empleado=self.empleado, fecha_pago=self.fecha_pago, es_descuento_planilla=True, monto__lte=self.prestamos
                )
                for pp in pagos_prestamo:
                    prestamo_afectado = pp.prestamo
                    pp.delete()
                    if prestamo_afectado.saldo_restante > 0:
                        prestamo_afectado.estado = 'ACTIVO'
                        prestamo_afectado.save()
                        
            # ==============================================================
            # --- NUEVA REVERSIÓN: DEVOLVER ANTICIPOS A PENDIENTE ---
            # ==============================================================
            anticipos_descontados = AnticipoEmpleado.objects.filter(
                empleado=self.empleado,
                mes_descuento=mes_temporal,
                estado='DESCONTADO'
            )
            for ant in anticipos_descontados:
                ant.estado = 'PENDIENTE'
                ant.save()
                
        except Exception as e:
            pass
            
        super().delete(*args, **kwargs)
        dummy = PagoSueldo(mes_correspondiente=mes_temporal)
        dummy.sincronizar_caja_sueldos()

class VentaServicio(models.Model):
    TIPO_SERVICIO_CHOICES = [
        ('CERTIFICADO', 'CERTIFICADO'),
        ('GRABACIÓN', 'GRABACIÓN'),
        ('SISTEMA', 'SISTEMA'),
        ('OTRO', 'OTRO'),
    ]

    # Vinculamos al alumno/cliente existente para no duplicar datos
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE, related_name='compras_servicios')
    
    # Datos del Servicio
    tipo_servicio = models.CharField(max_length=50, choices=TIPO_SERVICIO_CHOICES)
    detalle = models.CharField(max_length=250, null=True, blank=True, help_text="Ej: Certificado de...")
    
    # Control Financiero
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pago = models.CharField(max_length=50)  # Ej: EFECTIVO, DEPÓSITO
    banco = models.CharField(max_length=50)       # Ej: ADMINISTRACIÓN, BANCO
    vendedor = models.CharField(max_length=100)
    registrado_por = models.CharField(max_length=100)
    
    # Fechas
    fecha_venta = models.DateField()
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Calcula el 10% de comisión automáticamente
    @property
    def comision(self):
        from decimal import Decimal
        if self.importe:
            return self.importe * Decimal('0.10')
        return Decimal('0.00')

    # ==============================================================
    # --- CEREBRO AUTOCURABLE PARA EL FLUJO DE CAJA (NUEVO) ---
    # ==============================================================
    def sincronizar_caja_ventas(self):
        from django.db.models import Sum
        from decimal import Decimal
        
        # 1. Definir la cuenta de destino (Caja o Banco)
        banco_limpio = str(self.banco).strip().upper() if self.banco else ''
        codigo_cuenta = '001' if banco_limpio in ['ADMINISTRACIÓN', 'ADMINISTRACION', 'EFECTIVO', '001 - ADMINISTRACIÓN'] else '002'
        nombre_cuenta = 'ADMINISTRACIÓN' if codigo_cuenta == '001' else 'BANCO'
        cuenta_destino, _ = CuentaCaja.objects.get_or_create(codigo=codigo_cuenta, defaults={'nombre': nombre_cuenta})
        
        # 2. El nombre en caja será "CERTIFICADO", "GRABACIÓN", etc.
        detalle_diario = str(self.tipo_servicio).strip().upper() if self.tipo_servicio else 'SERVICIO'

        # 3. Sumar todo el dinero de ESE DÍA y de ESE MISMO TIPO DE SERVICIO (Ej: Todos los certificados de hoy en efectivo)
        ventas_grupo = VentaServicio.objects.filter(
            fecha_venta=self.fecha_venta,
            banco=self.banco,
            tipo_servicio=self.tipo_servicio
        )

        total_agrupado = ventas_grupo.aggregate(total=Sum('importe'))['total'] or Decimal('0.00')

        # 4. Buscar el registro maestro en el Flujo de Caja
        movimiento = MovimientoCaja.objects.filter(
            fecha=self.fecha_venta,
            cuenta=cuenta_destino,
            detalle=detalle_diario,
            tipo='ENTRADA'
        ).first()

        # 5. Magia de Ajuste Automático (Actualiza, Crea o Destruye)
        if total_agrupado > 0:
            if movimiento:
                movimiento.monto = total_agrupado
                movimiento.save()
            else:
                MovimientoCaja.objects.create(
                    fecha=self.fecha_venta,
                    detalle=detalle_diario,
                    cuenta=cuenta_destino,
                    tipo='ENTRADA',
                    monto=total_agrupado
                )
        else:
            if movimiento:
                movimiento.delete() # Si se borran todas las ventas de este tipo hoy, se borra el registro contable

    def save(self, *args, **kwargs):
        # 1. Guardamos la venta de servicio primero
        super().save(*args, **kwargs)
        
        # 2. Obligamos al Flujo de Caja a recalcular ese día
        self.sincronizar_caja_ventas()

    def delete(self, *args, **kwargs):
        # 1. Capturamos los datos vitales antes de que el registro desaparezca
        f_temp = self.fecha_venta
        b_temp = self.banco
        t_temp = self.tipo_servicio
        
        # 2. Destruimos la venta de servicio de la base de datos
        super().delete(*args, **kwargs)
        
        # 3. Usamos un "fantasma" para decirle a la Caja que revise las sumas de ese día.
        # Al revisar y notar que falta este monto, lo descontará o borrará la fila limpia.
        fantasma = VentaServicio(
            fecha_venta=f_temp, 
            banco=b_temp, 
            tipo_servicio=t_temp
        )
        fantasma.sincronizar_caja_ventas()

    class Meta:
        verbose_name = 'Venta de Servicio'
        verbose_name_plural = 'Ventas de Servicios'
        ordering = ['-fecha_venta', '-id']

    def __str__(self):
        nombre = getattr(self.participante, 'nombre_completo', None) or getattr(self.participante, 'nombre', 'Sin Nombre')
        return f"{self.tipo_servicio} - {nombre} (Bs {self.importe})"
    
class Asistencia(models.Model):
    ESTADOS_ASISTENCIA = (
        ('PRESENTE', 'Presente'),
        ('FALTA', 'Falta'),
        ('PENDIENTE', 'Pendiente'),
    )
    
    # Vinculamos la asistencia directamente a la inscripción (así sabemos qué alumno y de qué curso es)
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField()
    estado = models.CharField(max_length=15, choices=ESTADOS_ASISTENCIA, default='PENDIENTE')

    class Meta:
        # Esto evita que un docente pueda ponerle "Presente" y "Falta" al mismo alumno el mismo día
        unique_together = ('inscripcion', 'fecha')
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

    def __str__(self):
        return f"{self.inscripcion.participante.nombre_completo} - {self.fecha} - {self.estado}"
    
class DatosEmpresa(models.Model):
    razon_social = models.CharField(max_length=255, verbose_name="Razón Social")
    nit = models.CharField(max_length=50, verbose_name="Número de NIT")
    nro_ministerio = models.CharField(max_length=100, verbose_name="Nº Identificador Ministerio de Trabajo")
    nro_caja_salud = models.CharField(max_length=50, verbose_name="Nº de Empleador (Caja de Salud)")

    class Meta:
        verbose_name = "Datos de la Empresa"
        verbose_name_plural = "Datos de la Empresa"

    def __str__(self):
        return self.razon_social
    
class Contador(models.Model):
    nombre_completo = models.CharField(max_length=150, verbose_name="Nombre del Contador(a)")

    class Meta:
        verbose_name = "Contador"
        verbose_name_plural = "Contadores"

    def __str__(self):
        return self.nombre_completo
    
class Prestamo(models.Model):
    # Vinculamos al empleado (Si luego prestas a externos, se puede añadir un campo Cliente)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, null=True, blank=True)

    nombre_externo = models.CharField(max_length=200, null=True, blank=True, verbose_name="Nombre (Externo)")
    celular_externo = models.CharField(max_length=50, null=True, blank=True, verbose_name="Celular (Externo)")
    
    # 1. Condiciones del Préstamo (Igual que en tu Excel)
    fecha_prestamo = models.DateField(default=date.today)
    tipo_prestamo = models.CharField(max_length=50, default='AMORTIZABLE')
    tipo_cuota = models.CharField(max_length=50, choices=[('SEMANAL', 'SEMANAL'), ('MENSUAL', 'MENSUAL')])
    dia_de_pago = models.CharField(max_length=100, help_text="Ej: DOMINGO, DÍA 15 DEL MES")
    
    # 2. Matemática Financiera
    monto_prestado = models.DecimalField(max_digits=10, decimal_places=2)
    interes = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_deuda = models.DecimalField(max_digits=10, decimal_places=2)
    nro_cuotas = models.IntegerField(default=1)
    
    # 3. Seguimiento
    estado = models.CharField(max_length=20, default='ACTIVO') # ACTIVO, PAGADO, EN MORA
    observaciones = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"

    # Propiedades dinámicas para evitar redundancia de datos
    @property
    def pago_acumulado(self):
        # ¡OPTIMIZADO!: Al usar sum() en vez de aggregate(), le permitimos a Django 
        # usar la memoria RAM y evitamos hacer cientos de consultas a la base de datos.
        from decimal import Decimal
        total = sum(pago.monto for pago in self.pagos.all())
        return total if total else Decimal('0.00')

    @property
    def saldo_restante(self):
        return self.total_deuda - self.pago_acumulado

    # --- AUTOMATIZACIÓN: EL DINERO SALE DE CAJA AL OTORGAR EL PRÉSTAMO ---
    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        # Si no se define total de deuda, se asume capital + interés
        if not self.total_deuda:
            self.total_deuda = self.monto_prestado + self.interes
            
        super().save(*args, **kwargs)
        
        if es_nuevo:
            # Por defecto asumimos que sale de la caja de Administración
            cuenta_origen, _ = CuentaCaja.objects.get_or_create(codigo='001', defaults={'nombre': 'ADMINISTRACIÓN'})
            MovimientoCaja.objects.create(
                fecha=self.fecha_prestamo,
                detalle=f"Desembolso Préstamo: {self.empleado.nombre_completo}",
                cuenta=cuenta_origen,
                tipo='SALIDA',
                monto=self.monto_prestado
            )

    def __str__(self):
        return f"Préstamo a {self.empleado.nombre_completo} - {self.monto_prestado} Bs"
    @property
    def nombre_deudor(self):
        # Si hay empleado, muestra el empleado; si no, muestra el externo
        if self.empleado:
            return self.empleado.nombre_completo
        return self.nombre_externo or "Persona Externa"
    
    @property
    def fecha_estimada_fin(self):
        import calendar
        from datetime import timedelta, date
        
        if not self.fecha_prestamo or not self.nro_cuotas:
            return self.fecha_prestamo
            
        if self.tipo_cuota == 'MENSUAL':
            year = self.fecha_prestamo.year
            month = self.fecha_prestamo.month + self.nro_cuotas
            
            # Ajuste inteligente de años si las cuotas superan diciembre
            year += (month - 1) // 12
            month = (month - 1) % 12 + 1
            
            # Ajuste de días (ej. si el mes termina en 28 o 31)
            day = min(self.fecha_prestamo.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)
            
        elif self.tipo_cuota == 'QUINCENAL':
            return self.fecha_prestamo + timedelta(days=15 * self.nro_cuotas)
            
        elif self.tipo_cuota == 'SEMANAL':
            return self.fecha_prestamo + timedelta(days=7 * self.nro_cuotas)
            
        return self.fecha_prestamo


class PagoPrestamo(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField(default=date.today)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    es_descuento_planilla = models.BooleanField(default=False, help_text="¿Se descontó del sueldo?")

    class Meta:
        verbose_name = "Pago de Préstamo"
        verbose_name_plural = "Pagos de Préstamos"

    # --- AUTOMATIZACIÓN: EL DINERO ENTRA A CAJA (Si es en efectivo) ---
    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        # Si el pago lo trae en efectivo y no es descuento por planilla, entra a caja directa
        if es_nuevo and not self.es_descuento_planilla:
            cuenta_destino, _ = CuentaCaja.objects.get_or_create(codigo='001', defaults={'nombre': 'ADMINISTRACIÓN'})
            MovimientoCaja.objects.create(
                fecha=self.fecha_pago,
                detalle=f"Cobro Cuota Préstamo: {self.prestamo.nombre_deudor}",
                cuenta=cuenta_destino,
                tipo='ENTRADA',
                monto=self.monto
            )
            
        # Actualizamos el estado del préstamo si ya terminó de pagar
        if self.prestamo.saldo_restante <= 0:
            self.prestamo.estado = 'PAGADO'
            self.prestamo.save()

class ArqueoCaja(models.Model):
    CUENTAS_OPCIONES = [
        ('ADMINISTRACION', 'Administración (Efectivo)'),
        ('CAJA_CHICA', 'Caja Chica (Efectivo)'),
        ('GERENCIA', 'Gerencia (Efectivo)'),
        ('AHORRO', 'Ahorro (Efectivo)'),
        ('BANCO', 'Banco (Extracto)'),
    ]

    fecha_registro = models.DateTimeField(auto_now_add=True) # Guarda la fecha y hora exacta
    usuario = models.ForeignKey(User, on_delete=models.PROTECT) # Quién hizo el arqueo
    cuenta = models.CharField(max_length=50, choices=CUENTAS_OPCIONES)
    
    saldo_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    total_fisico = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)
    
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.cuenta} - {self.fecha_registro.strftime('%d/%m/%Y')} - Dif: {self.diferencia}"
    
class CitaConsultora(models.Model):
    ESTADOS_CITA = [
        ('PENDIENTE', 'Pendiente'),
        ('REALIZADA', 'Realizada'),
        ('CANCELADA', 'Cancelada'),
    ]
    nombre_cliente = models.CharField(max_length=200)
    celular = models.CharField(max_length=50, blank=True, null=True)
    
    # --- NUEVO CAMPO AÑADIDO ---
    modalidad = models.CharField(max_length=50, default='PRESENCIAL') 
    
    fecha = models.DateField()
    hora = models.CharField(max_length=10)
    motivo = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_CITA, default='PENDIENTE')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_cliente} - {self.fecha} {self.hora}"
    
class ArchivoDigital(models.Model):
    CATEGORIAS = [
        ('FACTURAS', 'Facturas Emitidas'),
        ('FORMULARIOS', 'Formularios y Declaraciones'),
        ('PLANILLAS', 'Planillas Impositivas'),
        ('OTROS', 'Otros Documentos'),
    ]
    periodo = models.CharField(max_length=20) # Guardará el formato '2026-06'
    categoria = models.CharField(max_length=50, choices=CATEGORIAS)
    enlace_drive = models.URLField(max_length=800) # Enlace directo a la carpeta
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.periodo} - {self.categoria}"
    
class AnticipoEmpleado(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha = models.DateField(default=date.today)
    mes_descuento = models.CharField(max_length=50) # Ej: "2026-07"
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    cuenta_origen = models.ForeignKey(CuentaCaja, on_delete=models.PROTECT, null=True, blank=True)
    estado = models.CharField(max_length=20, default='PENDIENTE') # PENDIENTE o DESCONTADO
    observaciones = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Anticipo de Sueldo"
        verbose_name_plural = "Anticipos de Sueldo"

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        # Automatización: El dinero sale de caja al entregar el anticipo físico
        if es_nuevo:
            MovimientoCaja.objects.create(
                fecha=self.fecha,
                detalle=f"Anticipo de Sueldo: {self.empleado.nombre_completo}",
                cuenta=self.cuenta_origen,
                tipo='SALIDA',
                monto=self.monto
            )

    def delete(self, *args, **kwargs):
        # Lógica para revertir el dinero a caja si eliminas el anticipo
        f_temp = self.fecha
        m_temp = self.monto
        e_nombre = self.empleado.nombre_completo
        super().delete(*args, **kwargs)
        
        fantasma = MovimientoCaja.objects.filter(
            fecha=f_temp,
            detalle=f"Anticipo de Sueldo: {e_nombre}",
            tipo='SALIDA',
            monto=m_temp
        ).first()
        if fantasma:
            fantasma.delete()
            
class AsistenciaEmpleado(models.Model):
    ESTADOS_ASISTENCIA = [
        ('PUNTUAL', 'Puntual'),
        ('RETRASO', 'Retraso'),
        ('FALTA', 'Falta'),
    ]
    TIPO_MARCADO = [
        ('INGRESO', 'Ingreso'),
        ('SALIDA', 'Salida'),
    ]
    
    # Vinculado a tu tabla Empleado existente
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asistencias_laborales')
    fecha = models.DateField(default=date.today)
    hora = models.TimeField(auto_now_add=True)  # Se registra la hora exacta automáticamente
    tipo = models.CharField(max_length=20, choices=TIPO_MARCADO)
    estado = models.CharField(max_length=20, choices=ESTADOS_ASISTENCIA, default='PUNTUAL')
    
    # Guardamos los minutos exactos de retraso para tus reportes
    minutos_retraso = models.IntegerField(default=0) 

    class Meta:
        verbose_name = "Asistencia de Empleado"
        verbose_name_plural = "Asistencias de Empleados"
        ordering = ['-fecha', '-hora'] # Ordena mostrando lo más reciente primero

    def __str__(self):
        return f"{self.empleado.nombre_completo} - {self.fecha} {self.hora} ({self.tipo})"