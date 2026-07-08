from django import forms
from .models import Participante, Docente, Curso, Inscripcion, MovimientoCaja, CuentaCaja, Cliente, ServicioConsultora, Honorario, Empleado, PagoSueldo, Prestamo, PagoPrestamo, AnticipoEmpleado

class ParticipanteForm(forms.ModelForm):
    class Meta:
        model = Participante
        fields = ['nombre_completo', 'celular']

class DocenteForm(forms.ModelForm):
    class Meta:
        model = Docente
        fields = ['nombre']

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = '__all__'
        widgets = {
            'modulo_padre': forms.Select(attrs={'class': 'w-full h-12 bg-slate-50 border-2 border-slate-100 rounded-xl px-4 text-sm font-bold text-black uppercase outline-none focus:bg-white focus:border-[#0071e3] transition-all shadow-sm appearance-none cursor-pointer'}),
        }

class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = '__all__'

class MovimientoCajaForm(forms.ModelForm):
    class Meta:
        model = MovimientoCaja
        fields = '__all__'

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'

class ServicioConsultoraForm(forms.ModelForm):
    class Meta:
        model = ServicioConsultora
        exclude = ['comision']
        
class HonorarioForm(forms.ModelForm):
    class Meta:
        model = Honorario
        fields = '__all__'
        widgets = {
            'fecha_anticipo': forms.DateInput(attrs={'type': 'date'}),
        }

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = '__all__'

class PagoSueldoForm(forms.ModelForm):
    class Meta:
        model = PagoSueldo
        fields = '__all__'
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
        }

class PrestamoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = ['empleado', 'nombre_externo', 'celular_externo','fecha_prestamo', 'tipo_prestamo', 'tipo_cuota', 'dia_de_pago', 'monto_prestado', 'interes', 'observaciones', 'nro_cuotas']
        widgets = {
            'fecha_prestamo': forms.DateInput(attrs={'type': 'date'}),
        }

class PagoPrestamoForm(forms.ModelForm):
    class Meta:
        model = PagoPrestamo
        fields = ['fecha_pago', 'monto', 'es_descuento_planilla']
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
        }
        
class AnticipoEmpleadoForm(forms.ModelForm):
    class Meta:
        model = AnticipoEmpleado
        fields = '__all__'
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
        }