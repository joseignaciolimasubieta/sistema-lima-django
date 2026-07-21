# tasks.py
import requests
import base64
from django.conf import settings
import tempfile
from weasyprint import HTML
from django.template.loader import render_to_string
from .models import Curso, Inscripcion
import os
from pathlib import Path

def procesar_y_enviar_certificados(curso_id, modalidad_actual, base_url):
    curso = Curso.objects.get(id=curso_id)
    inscritos = Inscripcion.objects.filter(curso=curso, modalidad=modalidad_actual).select_related('participante')
    
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

    for inscrito in inscritos:
        correo_destino = inscrito.participante.correo
        
        if correo_destino:
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
                
                with open(temp_pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

                url = "https://api.brevo.com/v3/smtp/email"
                
                payload = {
                    "sender": {"name": "Grupo Empresarial LIMA", "email": settings.DEFAULT_FROM_EMAIL},
                    "to": [{"email": correo_destino, "name": inscrito.participante.nombre_completo}],
                    "subject": f"Tu certificado del curso: {curso.nombre}",
                    "textContent": f"Hola {inscrito.participante.nombre_completo},\n\nAdjuntamos tu certificado digital emitido por el Grupo Empresarial LIMA. ¡Felicidades por culminar el curso!\n\nSaludos cordiales.",
                    "attachment": [{
                        "content": pdf_base64,
                        "name": nombre_archivo
                    }]
                }
                
                headers = {
                    "accept": "application/json",
                    "api-key": os.environ.get("BREVO_API_KEY"),
                    "content-type": "application/json"
                }

                response = requests.post(url, json=payload, headers=headers)
                
                if response.status_code == 201 or response.status_code == 200:
                    correos_enviados += 1
                    print(f"✅ Correo enviado con éxito a {correo_destino} vía API")
                else:
                    print(f"❌ Error de API para {correo_destino}: {response.text}")
                
            except Exception as e:
                print(f"❌ Error al enviar correo a {correo_destino}: {str(e)}")
            finally:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
            
    return f"Se enviaron {correos_enviados} certificados exitosamente."


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
        
        # Leemos el PDF temporal y lo convertimos a Base64 para enviarlo por API
        with open(temp_pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # --- ENVÍO SEGURIZADO VÍA API HTTP (A PRUEBA DE BLOQUEOS EN RENDER) ---
        # Usamos Brevo (puedes crear una cuenta gratis en brevo.com y sacar tu API Key)
        url = "https://api.brevo.com/v3/smtp/email"
        
        payload = {
            "sender": {"name": "Grupo Empresarial LIMA", "email": settings.DEFAULT_FROM_EMAIL},
            "to": [{"email": correo_destino, "name": inscrito.participante.nombre_completo}],
            "subject": f"Tu certificado del curso: {curso.nombre}",
            "textContent": f"Hola {inscrito.participante.nombre_completo},\n\nAdjuntamos tu certificado digital emitido por el Grupo Empresarial LIMA. ¡Felicidades por culminar el curso!\n\nSaludos cordiales.",
            "attachment": [{
                "content": pdf_base64,
                "name": nombre_archivo
            }]
        }
        
        headers = {
            "accept": "application/json",
            "api-key": os.environ.get("BREVO_API_KEY"), # Tu llave de API segura en las variables de entorno de Render
            "content-type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 201 or response.status_code == 200:
            print(f"✅ Certificado enviado correctamente a {correo_destino} vía API")
        else:
            print(f"❌ Error de API: {response.text}")
        
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            
    return f"Proceso finalizado para {correo_destino}."