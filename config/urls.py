from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from envios import views_auth
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. Autenticación personalizada (Prioridad)
    path('accounts/login/', views_auth.login_view, name='login'),
    path('accounts/logout/', views_auth.logout_view, name='logout'),
    path('accounts/perfil/', views_auth.perfil_view, name='perfil'),
    
    # 2. Vistas web del sistema
    path('', include('envios.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 3. API REST con versionado dinamico
    path('api/<version>/', include('api.urls')),
    
    # 4. Auth JWT
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # 5. Documentación
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# ── Configuración de archivos estáticos y Silk (Solo Desarrollo) ──
if settings.DEBUG:
    from silk import urls as silk_urls
    urlpatterns += [
        path('silk/', include(silk_urls, namespace='silk')),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Personalización del Admin
admin.site.site_header = 'Sistema de Gestión de Encomiendas'
admin.site.site_title = 'Encomiendas Admin'
admin.site.index_title = 'Panel de Administración'
