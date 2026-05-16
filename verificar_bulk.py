import os
import django

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from envios.serializers import EncomiendaSerializer
from clientes.models import Cliente
from rutas.models import Ruta
from envios.models import Empleado, Encomienda
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from django.db import connection, reset_queries
from django.conf import settings

# ── 1. VERIFICAR TO_REPRESENTATION ────────────────────────────────
print('\n--- [1] VERIFICACIÓN DE REPRESENTACIÓN (JSON) ---')

c1 = Cliente.objects.first()
c2 = Cliente.objects.exclude(pk=c1.pk).first()
r1 = Ruta.objects.first()
emp = Empleado.objects.first()

# Asegurar que existe un usuario no-staff para la prueba
user, _ = User.objects.get_or_create(username='verificador', defaults={'is_staff': False})

factory = APIRequestFactory()
request = factory.get('/')
request.user = user

enc = Encomienda.objects.con_relaciones().first()
if enc:
    s = EncomiendaSerializer(enc, context={'request': request})
    data = s.data
    
    print(f'Campos en la respuesta: {list(data.keys())[:10]}...')
    print(f'¿Tiene estado_color?: {"estado_color" in data}')
    print(f'¿Tiene ruta_codigo?: {"ruta_codigo" in data}')
    print(f'¿Tiene costo_display?: {"costo_display" in data}')
    print(f'¿Observaciones ocultas para no-staff?: {"observaciones" not in data}')
else:
    print('No hay encomiendas para probar.')

# ── 2. VERIFICAR BULK (EFICIENCIA SQL) ───────────────────────────
print('\n--- [2] VERIFICACIÓN DE EFICIENCIA SQL (BULK) ---')

settings.DEBUG = True
reset_queries()

data_bulk = [
    {
        'codigo': 'ENC-BULK-SH-001', 'descripcion': 'Test 1',
        'peso_kg': '1.0', 'remitente_id': c1.pk, 'destinatario_id': c2.pk,
        'ruta_id': r1.pk, 'costo_envio': '25.00'
    },
    {
        'codigo': 'ENC-BULK-SH-002', 'descripcion': 'Test 2',
        'peso_kg': '2.0', 'remitente_id': c1.pk, 'destinatario_id': c2.pk,
        'ruta_id': r1.pk, 'costo_envio': '25.00'
    },
]

# Serializador con many=True (activa EncomiendaBulkSerializer)
s_bulk = EncomiendaSerializer(data=data_bulk, many=True)
if s_bulk.is_valid():
    # El guardado debería generar un solo INSERT masivo
    encomiendas = s_bulk.save(empleado_registro=emp)
    
    print(f'Encomiendas creadas: {len(encomiendas)}')
    # Filtramos para ver solo las queries de INSERT
    insert_queries = [q for q in connection.queries if 'INSERT' in q['sql']]
    print(f'Queries SQL de tipo INSERT: {len(insert_queries)}')
    
    if len(insert_queries) == 1:
        print('¡ÉXITO! Se utilizó una sola query SQL para insertar múltiples registros.')
    else:
        print(f'Aviso: Se detectaron {len(insert_queries)} inserts.')
else:
    print(f'Errores de validación: {s_bulk.errors}')
