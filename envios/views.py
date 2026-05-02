# envios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.core.exceptions import PermissionDenied

from .models import Encomienda, Empleado, HistorialEstado
from .forms import EncomiendaForm
from config.choices import EstadoEnvio

# ── Condición personalizada para el sistema de encomiendas ──────
def es_empleado_activo(user):
    """True si el user tiene un Empleado activo asociado"""
    return (
        user.is_authenticated and
        Empleado.objects.filter(email=user.email, estado=1).exists()
    )

# ── Dashboard ────────────────────────────────────────────────
@login_required
@require_GET
def dashboard(request):
    """Vista principal del sistema con estadísticas"""
    hoy = timezone.now().date()
    context = {
        'total_activas': Encomienda.objects.activas().count(),
        'en_transito': Encomienda.objects.en_transito().count(),
        'con_retraso': Encomienda.objects.con_retraso().count(),
        'entregadas_hoy': Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO,
            fecha_entrega_real=hoy
        ).count(),
        'ultimas': Encomienda.objects.con_relaciones()[:5],
    }
    return render(request, 'envios/dashboard.html', context)

# ── Listado de encomiendas ──────────────────────────────────
@login_required
@require_GET
def encomienda_lista(request):
    """Listado de encomiendas con filtros de búsqueda y estado"""
    estado = request.GET.get('estado', '')
    q = request.GET.get('q', '')
    
    qs = Encomienda.objects.con_relaciones()
    
    if estado:
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(
            Q(codigo__icontains=q) |
            Q(remitente__apellidos__icontains=q) |
            Q(destinatario__apellidos__icontains=q)
        )
    
    paginator = Paginator(qs, 15) # 15 por página
    page_number = request.GET.get('page', 1)
    encomiendas = paginator.get_page(page_number)
    
    return render(request, 'envios/lista.html', {
        'encomiendas': encomiendas,
        'estados': EstadoEnvio.choices,
        'estado_activo': estado,
        'q': q,
    })

# ── Detalle de encomienda ────────────────────────────────────
@login_required
@require_GET
def encomienda_detalle(request, pk):
    """Detalle de una encomienda específica y su historial"""
    encomienda = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    historial = encomienda.historial.all().order_by('-fecha_cambio')
    
    return render(request, 'envios/detalle.html', {
        'encomienda': encomienda,
        'historial': historial,
    })

# ── Búsqueda por código directo ──────────────────────────────
@login_required
@require_GET
def encomienda_por_codigo(request, codigo):
    """Buscar encomienda por código exacto o devolver 404"""
    try:
        enc = Encomienda.objects.get(codigo=codigo.upper())
    except Encomienda.DoesNotExist:
        raise Http404(f'No existe la encomienda {codigo}')
    return render(request, 'envios/detalle.html', {'encomienda': enc})

# ── Crear encomienda ─────────────────────────────────────────
@login_required
@require_http_methods(['GET', 'POST'])
@permission_required('envios.add_encomienda', raise_exception=True)
def encomienda_crear(request):
    """Crear una nueva encomienda (GET muestra form, POST procesa)"""
    if request.method == 'POST':
        form = EncomiendaForm(request.POST)
        if form.is_valid():
            enc = form.save(commit=False)
            try:
                empleado = Empleado.objects.get(email=request.user.email)
                enc.empleado_registro = empleado
                enc.save()
                messages.success(request, f'Encomienda {enc.codigo} registrada correctamente.')
                return redirect('encomienda_detalle', pk=enc.pk)
            except Empleado.DoesNotExist:
                messages.error(request, 'El usuario actual no tiene un perfil de empleado asociado.')
    else:
        form = EncomiendaForm()
        
    return render(request, 'envios/form.html', {
        'form': form,
        'titulo': 'Nueva Encomienda',
    })

# ── Cambio de estado ─────────────────────────────────────────
@login_required
@require_POST
def encomienda_cambiar_estado(request, pk):
    """Procesar el cambio de estado de una encomienda"""
    enc = get_object_or_404(Encomienda, pk=pk)
    nuevo_estado = request.POST.get('estado')
    observacion = request.POST.get('observacion', '')
    
    try:
        empleado = Empleado.objects.get(email=request.user.email)
        enc.cambiar_estado(nuevo_estado, empleado, observacion)
        messages.success(request, f'Estado actualizado a: {enc.get_estado_display()}')
    except ValueError as e:
        messages.error(request, str(e))
    except Empleado.DoesNotExist:
        messages.error(request, 'No se pudo identificar al empleado.')
            
    return redirect('encomienda_detalle', pk=pk)

# ── Eliminar encomienda ─────────────────────────────────────────
@login_required
def encomienda_eliminar(request, pk):
    """Eliminar una encomienda solo si está en estado pendiente"""
    enc = get_object_or_404(Encomienda, pk=pk)
    
    # Solo se puede eliminar si está pendiente (punto 8 del entregable)
    if enc.estado != EstadoEnvio.PENDIENTE:
        raise PermissionDenied # → devuelve 403 Forbidden
        
    if request.method == 'POST':
        enc.delete()
        messages.success(request, 'Encomienda eliminada correctamente.')
        return redirect('encomienda_lista')
        
    return render(request, 'envios/confirmar_eliminar.html', {'enc': enc})

# ── API JSON para el estado ──────────────────────────────────
@login_required
@require_GET
def encomienda_estado_json(request, pk):
    """Endpoint AJAX para obtener el estado actual de una encomienda"""
    enc = get_object_or_404(Encomienda, pk=pk)
    return JsonResponse({
        'codigo': enc.codigo,
        'estado': enc.estado,
        'display': enc.get_estado_display(),
        'retraso': enc.tiene_retraso,
        'dias': enc.dias_en_transito,
    })

# ── Utilidad: Ping ───────────────────────────────────────────
def ping(request):
    """Endpoint de verificación de estado del servidor"""
    return HttpResponse('pong', status=200, content_type='text/plain')
