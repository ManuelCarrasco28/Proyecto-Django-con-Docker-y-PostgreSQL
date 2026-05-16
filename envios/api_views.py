from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.conf import settings

from .models import Encomienda
from clientes.models import Cliente
from rutas.models import Ruta
from .serializers import (
    EncomiendaSerializer, 
    EncomiendaDetailSerializer,
    ClienteSerializer, 
    RutaSerializer
)
from api.pagination import ClientePagination, EncomiendaPagination

# ── Encomiendas: listar + crear ──────────────────────────────────
class EncomiendaListCreateView(generics.ListCreateAPIView):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = EncomiendaPagination

    def perform_create(self, serializer):
        serializer.save(
            empleado_registro=self.request.user.empleado
        )

# ── Encomiendas: detalle + actualizar + eliminar ─────────────────
class EncomiendaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Encomienda.objects.con_relaciones()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EncomiendaDetailSerializer
        return EncomiendaSerializer

# ── Clientes: solo lectura ───────────────────────────────────────
@extend_schema(tags=['Clientes'])
class ClienteListView(generics.ListAPIView):
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ClientePagination
    
    def get_queryset(self):
        return Cliente.objects.activos()

# ── Rutas: solo lectura con Caché ────────────────────────────────
@extend_schema(
    summary='Listar rutas activas',
    description='Devuelve todas las rutas con estado Activo. Cacheado por 15 min.',
    tags=['Rutas'],
)
class RutaListView(generics.ListAPIView):
    serializer_class = RutaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    @method_decorator(cache_page(settings.CACHE_TTL))
    @method_decorator(vary_on_headers('Authorization'))
    def dispatch(self, *args, **kwargs):
        """
        Aplicamos el caché en dispatch para cubrir toda la respuesta.
        vary_on_headers('Authorization') asegura caché independiente por usuario/token.
        """
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return Ruta.objects.activas()
