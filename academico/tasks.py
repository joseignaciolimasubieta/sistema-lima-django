# tasks.py
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import Curso, Inscripcion
import os
from pathlib import Path
from django.conf import settings

# Borramos el @shared_task que estaba aquí arriba
def procesar_y_enviar_certificados(curso_id, modalidad_actual, base_url):
    curso = Curso.objects.get(id=curso_id)
    inscritos = Inscripcion.objects.filter(curso=curso, modalidad=modalidad_actual).select_related('participante')
    
    # 1. Definimos las rutas y fondos según el docente
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    
    nombre_docente = curso.docente.nombre.lower()
    if 'juan' in nombre_docente or 'juanjo' in nombre_docente:
        archivo_fondo = 'certificado_juanjo.jpg'
    elif 'mariana' in nombre_docente:
        archivo_fondo = 'certificado_mariana.jpg'
    elif 'rodrigo' in nombre_docente:
        archivo_fondo = 'certificado_rodrigo.jpg'
    else:
        archivo_fondo = 'certificado.jpg'
        
    ruta_imagen = Path(os.path.join(ruta_actual, 'static', archivo_fondo)).as_uri()
    ruta_fuente = Path(os.path.join(ruta_actual, 'static', 'Montserrat-Bold.ttf')).as_uri()
    
    correos_enviados = 0

    # 2. Generamos y enviamos un correo por cada alumno
    for inscrito in inscritos:
        correo_destino = inscrito.participante.correo
        
        if correo_destino:
            # Renderizar el PDF individual en la RAM
            contexto = {
                'curso': curso,
                'lista_inscritos': [inscrito],
                'ruta_imagen': ruta_imagen,
                'ruta_fuente': ruta_fuente,
            }
            html_string = render_to_string('pdf_certificados.html', contexto)
            pdf_file = HTML(string=html_string, base_url=base_url).write_pdf()

            # Configurar el correo electrónico
            asunto = f'Tu certificado del curso: {curso.nombre}'
            mensaje = f'Hola {inscrito.participante.nombre_completo},\n\nAdjuntamos tu certificado digital emitido por el Grupo Empresarial LIMA. ¡Felicidades por culminar el curso!\n\nSaludos cordiales.'
            
            email = EmailMessage(
                subject=asunto,
                body=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL, # <-- Usa el correo oficial de settings
                to=[correo_destino]
            )
            
            # Adjuntar el archivo y enviarlo
            nombre_limpio = inscrito.participante.nombre_completo.replace(" ", "_")
            email.attach(f"Certificado_{nombre_limpio}.pdf", pdf_file, 'application/pdf')
            
            # --- TRUCO DE DEPURACIÓN ---
            try:
                email.send(fail_silently=False) # <-- Cambiamos a False para que nos muestre si hay errores
                print(f"✅ Correo enviado con éxito a {correo_destino}")
            except Exception as e:
                print(f"❌ Error al enviar correo a {correo_destino}: {str(e)}")
            
    return f"Se enviaron {correos_enviados} certificados exitosamente."

# tasks.py (Agregar al final)
def enviar_certificado_individual_task(inscripcion_id, base_url):
    inscrito = Inscripcion.objects.select_related('curso', 'curso__docente', 'participante').get(id=inscripcion_id)
    curso = inscrito.curso
    correo_destino = inscrito.participante.correo
    
    if not correo_destino:
        return f"El participante {inscrito.participante.nombre_completo} no tiene correo."

    # Definimos fondos según el docente
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    nombre_docente = curso.docente.nombre.lower()
    
    if 'juan' in nombre_docente or 'juanjo' in nombre_docente:
        archivo_fondo = 'certificado_juanjo.jpg'
    elif 'mariana' in nombre_docente:
        archivo_fondo = 'certificado_mariana.jpg'
    elif 'rodrigo' in nombre_docente:
        archivo_fondo = 'certificado_rodrigo.jpg'
    else:
        archivo_fondo = 'certificado.jpg'
        
    ruta_imagen = Path(os.path.join(ruta_actual, 'static', archivo_fondo)).as_uri()
    ruta_fuente = Path(os.path.join(ruta_actual, 'static', 'Montserrat-Bold.ttf')).as_uri()
    
    # Renderizamos el PDF
    contexto = {
        'curso': curso,
        'lista_inscritos': [inscrito],
        'ruta_imagen': ruta_imagen,
        'ruta_fuente': ruta_fuente,
    }
    html_string = render_to_string('pdf_certificados.html', contexto)
    pdf_file = HTML(string=html_string, base_url=base_url).write_pdf()

    # Preparamos y enviamos el correo
    asunto = f'Tu certificado del curso: {curso.nombre}'
    mensaje = f'Hola {inscrito.participante.nombre_completo},\n\nAdjuntamos tu certificado digital emitido por el Grupo Empresarial LIMA. ¡Felicidades por culminar el curso!\n\nSaludos cordiales.'
    
    email = EmailMessage(
        subject=asunto,
        body=mensaje,
        from_email=settings.DEFAULT_FROM_EMAIL, # <-- Usa el correo oficial de settings
        to=[correo_destino]
    )
            
    # Adjuntar el archivo y enviarlo
    nombre_limpio = inscrito.participante.nombre_completo.replace(" ", "_")
    email.attach(f"Certificado_{nombre_limpio}.pdf", pdf_file, 'application/pdf')
            
    # --- TRUCO DE DEPURACIÓN ---
    try:
        email.send(fail_silently=False) # <-- Cambiamos a False para que nos muestre si hay errores
        print(f"✅ Correo enviado con éxito a {correo_destino}")
    except Exception as e:
        print(f"❌ Error al enviar correo a {correo_destino}: {str(e)}")
    
    return f"Certificado enviado a {correo_destino} exitosamente."