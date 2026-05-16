from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from django.utils import timezone

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes

# Importaciones del proyecto
from api.pagination import EncomiendaPagination, HistorialPagination
from api.filters import EncomiendaFilter
from api.permissions import EsEmpleadoActivo, EsPropietarioOAdmin
from api.throttles import EmpleadoRateThrottle, CambioEstadoThrottle
from api.exceptions import EstadoInvalidoError, EncomiendaYaEntregadaError
from .models import Encomienda, Empleado, Ruta
from .serializers import (
    EncomiendaSerializer,
    EncomiendaListSerializer,
    EncomiendaDetailSerializer,
    EncomiendaV2Serializer,
    HistorialEstadoSerializer,
    RutaSerializer,
)

class RutaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Las rutas cambian poco — cachear el listado 15 minutos.
    """
    queryset = Ruta.objects.activas()
    serializer_class = RutaSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(settings.CACHE_TTL))
    @method_decorator(vary_on_headers('Authorization'))
    def list(self, request, *args, **kwargs):
        """Cache por usuario (vary_on_headers diferencia el token)"""
        return super().list(request, *args, **kwargs)

@extend_schema_view(
    list=extend_schema(summary='Listar encomiendas', tags=['Encomiendas']),
    retrieve=extend_schema(summary='Detalle de encomienda', tags=['Encomiendas']),
)
class EncomiendaViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet optimizado con con_relaciones() y Caching manual.
    """
    queryset = Encomienda.objects.con_relaciones()
    permission_classes = [EsEmpleadoActivo]
    pagination_class = EncomiendaPagination
    throttle_classes = [EmpleadoRateThrottle]
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EncomiendaFilter
    search_fields = ['codigo', 'remitente__apellidos', 'destinatario__apellidos', 'descripcion']
    ordering_fields = ['fecha_registro', 'peso_kg', 'costo_envio']
    ordering = ['-fecha_registro']

    def get_serializer_class(self):
        version = getattr(self.request, 'version', 'v1')
        if version == 'v2':
            return EncomiendaV2Serializer
        if self.action == 'list':
            return EncomiendaListSerializer
        if self.action == 'retrieve':
            return EncomiendaDetailSerializer
        return EncomiendaSerializer

    def get_queryset(self):
        return Encomienda.objects.con_relaciones()

    def perform_update(self, serializer):
        """Invalidar caché cuando se actualiza una encomienda"""
        super().perform_update(serializer)
        # Borrar el caché de estadísticas de este empleado
        cache_key = f'estadisticas_empleado_{self.request.user.id}'
        cache.delete(cache_key)

    @action(detail=True, methods=['post'], url_path='cambiar_estado')
    def cambiar_estado(self, request, pk=None, **kwargs):
        enc = self.get_object()
        if enc.esta_entregada: raise EncomiendaYaEntregadaError()
        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')
        if not nuevo_estado: return Response({'error': 'Requerido'}, status=400)
        try:
            empleado = Empleado.objects.get(email=request.user.email)
            enc.cambiar_estado(nuevo_estado, empleado, observacion)
            
            # Invalidar caché al cambiar de estado
            cache.delete_many([
                f'estadisticas_empleado_{request.user.id}',
                f'encomienda_detalle_{pk}',
            ])
            
            return Response(EncomiendaSerializer(enc).data)
        except ValueError as e: raise EstadoInvalidoError(detail=str(e))
        except Exception as e: return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request, **kwargs):
        """Estadísticas globales con Caché manual por empleado"""
        cache_key = f'estadisticas_empleado_{request.user.id}'
        data = cache.get(cache_key)
        
        if data is None:
            hoy = timezone.now().date()
            data = {
                'total_activas': Encomienda.objects.activas().count(),
                'en_transito': Encomienda.objects.en_transito().count(),
                'con_retraso': Encomienda.objects.con_retraso().count(),
                'entregadas_hoy': Encomienda.objects.filter(estado='EN', fecha_entrega_real=hoy).count(),
            }
            cache.set(cache_key, data, settings.CACHE_TTL)
            
        return Response(data)

    @action(detail=False, methods=['get'])
    def con_retraso(self, request, **kwargs):
        qs = Encomienda.objects.con_retraso().con_relaciones()
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def pendientes(self, request, **kwargs):
        qs = Encomienda.objects.pendientes().con_relaciones()
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None, **kwargs):
        enc = self.get_object()
        qs = enc.historial.select_related('empleado').order_by('-fecha_cambio')
        paginator = HistorialPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(HistorialEstadoSerializer(page, many=True).data)
        return Response(HistorialEstadoSerializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        if not serializer.is_valid(): return Response(serializer.errors, status=400)
        try:
            empleado = Empleado.objects.get(email=self.request.user.email)
            encomiendas = serializer.save(empleado_registro=empleado)
            # Invalidar estadísticas al crear múltiples
            cache.delete(f'estadisticas_empleado_{request.user.id}')
            return Response(self.get_serializer(encomiendas, many=True).data, status=201)
        except Empleado.DoesNotExist: return Response({'error': '403'}, status=403)

    @action(detail=False, methods=['patch'], url_path='bulk_estado')
    def bulk_estado(self, request):
        ids, estado, obs = request.data.get('ids', []), request.data.get('estado'), request.data.get('observacion', '')
        if not ids or not estado: return Response({'error': '400'}, status=400)
        try:
            empleado = Empleado.objects.get(email=request.user.email)
            encomiendas = Encomienda.objects.filter(id__in=ids)
            actualizadas, errores = [], []
            for enc in encomiendas:
                try:
                    enc.cambiar_estado(estado, empleado, obs)
                    actualizadas.append(enc.id)
                except ValueError as e: errores.append({'id': enc.id, 'error': str(e)})
            
            # Invalidar estadísticas si hubo cambios
            if actualizadas:
                cache.delete(f'estadisticas_empleado_{request.user.id}')
                
            ids_proc = list(encomiendas.values_list('id', flat=True))
            return Response({'actualizadas': actualizadas, 'errores': errores, 'no_encontrados': [i for i in ids if i not in ids_proc], 'total': len(actualizadas)})
        except Empleado.DoesNotExist: return Response({'error': '403'}, status=403)
