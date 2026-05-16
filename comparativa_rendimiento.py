import os
import django
import time
from decimal import Decimal

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection, reset_queries
from django.conf import settings
from envios.models import Encomienda

settings.DEBUG = True

def imprimir_separador(titulo):
    print('=' * 60)
    print(titulo)
    print('=' * 60)

# ── CASO 1: SIN NINGUNA OPTIMIZACIÓN ───────────────────────────────
imprimir_separador('CASO 1: Sin ninguna optimización')
reset_queries()
t0 = time.time()
# Forzamos la carga de 15 registros sin select_related
encomiendas = list(Encomienda.objects.all()[:15])
for enc in encomiendas:
    _ = enc.remitente.nombre_completo
    _ = enc.destinatario.nombre_completo
    _ = enc.ruta.destino
    _ = enc.empleado_registro.apellidos

print(f'Queries: {len(connection.queries)}')
print(f'Tiempo: {(time.time()-t0)*1000:.1f}ms\n')

# ── CASO 2: CON CON_RELACIONES() (Select + Prefetch) ───────────────
imprimir_separador('CASO 2: Con con_relaciones()')
reset_queries()
t0 = time.time()
# Usamos nuestra optimización actual
encomiendas = list(Encomienda.objects.con_relaciones()[:15])
for enc in encomiendas:
    _ = enc.remitente.nombre_completo
    _ = enc.destinatario.nombre_completo
    _ = enc.ruta.destino
    _ = enc.empleado_registro.apellidos

print(f'Queries: {len(connection.queries)}')
print(f'Tiempo: {(time.time()-t0)*1000:.1f}ms\n')

# ── CASO 3: CON CON_RELACIONES() + ONLY() ──────────────────────────
imprimir_separador('CASO 3: Con con_relaciones() + only()')
reset_queries()
t0 = time.time()
# Optimización extrema: solo cargamos las columnas que usamos
encomiendas = list(
    Encomienda.objects.con_relaciones().only(
        'id', 'codigo', 'estado', 'peso_kg', 'costo_envio',
        'fecha_registro', 'fecha_entrega_est',
        'remitente_id', 'remitente__nombres', 'remitente__apellidos',
        'destinatario_id', 'destinatario__nombres', 'destinatario__apellidos',
        'ruta_id', 'ruta__destino',
        'empleado_registro_id', 'empleado_registro__apellidos'
    )[:15]
)
for enc in encomiendas:
    _ = enc.remitente.nombre_completo
    _ = enc.destinatario.nombre_completo
    _ = enc.ruta.destino
    _ = enc.empleado_registro.apellidos

print(f'Queries: {len(connection.queries)}')
print(f'Tiempo: {(time.time()-t0)*1000:.1f}ms\n')
