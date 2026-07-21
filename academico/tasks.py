# tasks.py
from django.core.mail import EmailMessage
from django.conf import settings
import os
import tempfile
from pathlib import Path
from weasyprint import HTML
from django.template.loader import render_to_string
from .models import Inscripcion

def enviar_certificado_individual_task(inscripcion_id, base_url):
    inscrito = Inscripcion.objects.select_related('curso', 'curso__docente', 'participante').get(id=inscripcion_id)
    curso = inscrito.curso
    correo_destino = inscrito.participante.correo
    
    if not correo_destino:
        return f"El participante {inscrito.participante.nombre_completo} no tiene correo."

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
    
    contexto = {
        'curso': curso,
        'lista_inscritos': [inscrito],
        'ruta_imagen': ruta_imagen,
        'ruta_fuente': ruta_fuente,
    }
    
    html_string = render_to_string('pdf_certificados.html', contexto)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
        HTML(string=html_string, base_url=base_url).write_pdf(temp_pdf.name)
        temp_pdf_path = temp_pdf.name

    try:
        nombre_limpio = inscrito.participante.nombre_completo.replace(" ", "_")
        nombre_archivo = f"Certificado_{nombre_limpio}.pdf"
        
        # Leemos los bytes del PDF generado
        with open(temp_pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        # --- ENVÍO VÍA GMAIL (SMTP NATIVO) ---
        asunto = f"Tu certificado del curso: {curso.nombre}"
        mensaje = f"Hola {inscrito.participante.nombre_completo},\n\nAdjuntamos tu certificado digital emitido por el Grupo Empresarial LIMA. ¡Felicidades por culminar el curso!\n\nSaludos cordiales."
        
        email = EmailMessage(
            subject=asunto,
            body=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[correo_destino]
        )
        
        # Adjuntamos el archivo y enviamos
        email.attach(nombre_archivo, pdf_bytes, 'application/pdf')
        email.send(fail_silently=False)
        
        print(f"✅ Certificado enviado a {correo_destino} vía Gmail")
        
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        raise e
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            
    return f"Proceso finalizado para {correo_destino}."