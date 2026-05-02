# envios/urls.py
from django.urls import path
from . import views, views_cbv

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Encomiendas (Usando CBV)
    path('encomiendas/', views_cbv.EncomiendaListView.as_view(), name='encomienda_lista'),
    path('encomiendas/nueva/', views_cbv.EncomiendaCreateView.as_view(), name='encomienda_crear'),
    path('encomiendas/<int:pk>/', views_cbv.EncomiendaDetailView.as_view(), name='encomienda_detalle'),
    path('encomiendas/<int:pk>/editar/', views_cbv.EncomiendaUpdateView.as_view(), name='encomienda_editar'),
    
    # Acciones específicas (FBV)
    path('encomiendas/<int:pk>/estado/', views.encomienda_cambiar_estado, name='encomienda_cambiar_estado'),
    path('encomiendas/<int:pk>/eliminar/', views.encomienda_eliminar, name='encomienda_eliminar'),
    
    # Búsqueda y API
    path('encomiendas/buscar/<str:codigo>/', views.encomienda_por_codigo, name='encomienda_por_codigo'),
    path('api/encomiendas/<int:pk>/estado/', views.encomienda_estado_json, name='encomienda_estado_json'),
    
    # Utilidades
    path('ping/', views.ping, name='ping'),
]
