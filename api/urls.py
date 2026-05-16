from rest_framework.routers import DefaultRouter
from django.urls import path, include
from envios.viewsets import EncomiendaViewSet, RutaViewSet
from envios import api_views

router = DefaultRouter()
router.register('encomiendas', EncomiendaViewSet, basename='encomienda')
router.register('rutas', RutaViewSet, basename='ruta')

urlpatterns = [
    path('', include(router.urls)),
    path('clientes/', api_views.ClienteListView.as_view()),
]
