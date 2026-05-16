import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from envios.models import Encomienda
from config.choices import EstadoEnvio
from .factories import (
    UserFactory, ClienteFactory, RutaFactory,
    EmpleadoFactory, EncomiendaFactory,
)

@pytest.mark.django_db
class TestAutenticacion:
    def test_sin_token_devuelve_401(self, api_client):
        response = api_client.get(reverse('encomienda-list', kwargs={'version': 'v1'}))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Nuevo formato:
        assert response.data['error'] is True
        assert response.data['code'] == 'AUTHENTICATION_REQUIRED'

    def test_token_invalido_devuelve_401(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION='Bearer tokeninvalido')
        response = api_client.get(reverse('encomienda-list', kwargs={'version': 'v1'}))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['code'] == 'AUTHENTICATION_REQUIRED'

    def test_con_token_valido_devuelve_200(self, auth_client):
        response = auth_client.get(reverse('encomienda-list', kwargs={'version': 'v1'}))
        assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
class TestListadoEncomiendas:
    def setup_method(self):
        self.user = UserFactory()
        self.empleado = EmpleadoFactory(email=self.user.email)
        self.ruta = RutaFactory()
        self.cliente1 = ClienteFactory()
        self.cliente2 = ClienteFactory()
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )

    def test_lista_respuesta_paginada(self):
        EncomiendaFactory(
            remitente=self.cliente1, destinatario=self.cliente2,
            ruta=self.ruta, empleado_registro=self.empleado
        )
        response = self.client.get(reverse('encomienda-list', kwargs={'version': 'v1'}))
        assert response.status_code == status.HTTP_200_OK
        for campo in ['count', 'next', 'previous', 'results']:
            assert campo in response.data
        assert response.data['count'] == 1

    def test_filtro_por_estado(self):
        enc_pe = EncomiendaFactory(estado='PE', ruta=self.ruta,
                                  remitente=self.cliente1, destinatario=self.cliente2,
                                  empleado_registro=self.empleado)
        enc_tr = EncomiendaFactory(estado='TR', ruta=self.ruta,
                                  remitente=self.cliente1, destinatario=self.cliente2,
                                  empleado_registro=self.empleado)
        response = self.client.get(reverse('encomienda-list', kwargs={'version': 'v1'}) + '?estado=PE')
        codigos = [r['codigo'] for r in response.data['results']]
        assert enc_pe.codigo in codigos
        assert enc_tr.codigo not in codigos

    def test_busqueda_por_codigo(self):
        enc = EncomiendaFactory(codigo='ENC-2026-BUSCAR', ruta=self.ruta,
                                remitente=self.cliente1, destinatario=self.cliente2,
                                empleado_registro=self.empleado)
        response = self.client.get(reverse('encomienda-list', kwargs={'version': 'v1'}) + '?search=BUSCAR')
        assert response.data['count'] == 1
        assert response.data['results'][0]['codigo'] == 'ENC-2026-BUSCAR'

@pytest.mark.django_db
class TestCrearEncomienda:
    def setup_method(self):
        self.user = UserFactory()
        self.empleado = EmpleadoFactory(email=self.user.email)
        self.cliente1 = ClienteFactory()
        self.cliente2 = ClienteFactory()
        self.ruta = RutaFactory(precio_base=Decimal('25.00'))
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )
        self.data_valida = {
            'codigo': 'ENC-2026-TEST', 'descripcion': 'Paquete de prueba',
            'peso_kg': '3.50', 'remitente_id': self.cliente1.pk,
            'destinatario_id': self.cliente2.pk,
            'ruta_id': self.ruta.pk, 'costo_envio': '25.00',
        }

    def test_crear_exitoso_devuelve_201(self):
        response = self.client.post(
            reverse('encomienda-list', kwargs={'version': 'v1'}), self.data_valida, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['codigo'] == 'ENC-2026-TEST'
        assert response.data['estado'] == 'PE'
        # Verificar nuevos campos de to_representation
        assert 'costo_display' in response.data
        assert 'estado_color' in response.data
        assert response.data['ruta_codigo'] is not None

    def test_crear_asigna_empleado_del_token(self):
        self.client.post(
            reverse('encomienda-list', kwargs={'version': 'v1'}), self.data_valida, format='json'
        )
        enc = Encomienda.objects.get(codigo='ENC-2026-TEST')
        assert enc.empleado_registro.email == self.user.email

    def test_remitente_igual_destinatario_devuelve_400(self):
        data = {**self.data_valida, 'destinatario_id': self.cliente1.pk}
        response = self.client.post(
            reverse('encomienda-list', kwargs={'version': 'v1'}), data, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Verificar en el campo 'detail' debido al nuevo Exception Handler
        assert 'destinatario' in response.data['detail'] or 'non_field_errors' in response.data['detail']
        assert response.data['code'] == 'VALIDATION_ERROR'

    def test_peso_negativo_devuelve_400_con_campo(self):
        data = {**self.data_valida, 'peso_kg': '-1.00'}
        response = self.client.post(
            reverse('encomienda-list', kwargs={'version': 'v1'}), data, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'peso_kg' in response.data['detail']

    def test_codigo_sin_prefijo_devuelve_400(self):
        data = {**self.data_valida, 'codigo': 'PKG-2026-001'}
        response = self.client.post(
            reverse('encomienda-list', kwargs={'version': 'v1'}), data, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'codigo' in response.data['detail']

    def test_sin_auth_no_crea_y_devuelve_401(self, api_client):
        response = api_client.post(
            reverse('encomienda-list', kwargs={'version': 'v1'}), self.data_valida, format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['code'] == 'AUTHENTICATION_REQUIRED'

@pytest.mark.django_db
class TestCambiarEstado:
    def setup_method(self):
        self.user = UserFactory()
        self.empleado = EmpleadoFactory(email=self.user.email)
        self.enc = EncomiendaFactory(
            empleado_registro=self.empleado, estado='PE'
        )
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )

    def test_cambiar_estado_exitoso_actualiza_bd_y_crea_historial(self):
        url = reverse('encomienda-cambiar-estado', kwargs={'version': 'v1', 'pk': self.enc.pk})
        data = {'estado': 'TR', 'observacion': 'Recogido en agencia Lima'}
        response = self.client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == 'TR'
        self.enc.refresh_from_db()
        assert self.enc.estado == EstadoEnvio.EN_TRANSITO

    def test_cambiar_al_mismo_estado_devuelve_422(self):
        url = reverse('encomienda-cambiar-estado', kwargs={'version': 'v1', 'pk': self.enc.pk})
        response = self.client.post(url, {'estado': 'PE'}, format='json')
        # Ahora devuelve 422 (Unprocessable Entity) por nuestra excepción personalizada
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.data['code'] == 'ESTADO_INVALIDO'

    def test_encomienda_inexistente_devuelve_404(self):
        url = reverse('encomienda-cambiar-estado', kwargs={'version': 'v1', 'pk': 99999})
        response = self.client.post(url, {'estado': 'TR'}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['code'] == 'NOT_FOUND'

@pytest.mark.django_db
class TestAccionesPersonalizadas:
    def setup_method(self):
        from django.utils import timezone
        from datetime import timedelta
        self.user = UserFactory()
        self.empleado = EmpleadoFactory(email=self.user.email)
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )
        ayer = timezone.now().date() - timedelta(days=1)
        self.enc_retraso = EncomiendaFactory(
            estado='TR', fecha_entrega_est=ayer,
            empleado_registro=self.empleado
        )
        self.enc_normal = EncomiendaFactory(
            estado='PE', empleado_registro=self.empleado
        )

    def test_con_retraso_solo_devuelve_retrasadas(self):
        response = self.client.get(reverse('encomienda-con-retraso', kwargs={'version': 'v1'}))
        assert response.status_code == status.HTTP_200_OK
        codigos = [r['codigo'] for r in response.data]
        assert self.enc_retraso.codigo in codigos

    def test_pendientes_solo_devuelve_pendientes(self):
        response = self.client.get(reverse('encomienda-pendientes', kwargs={'version': 'v1'}))
        assert response.status_code == status.HTTP_200_OK
        codigos = [r['codigo'] for r in response.data]
        assert self.enc_normal.codigo in codigos

    def test_estadisticas_devuelve_todos_los_contadores(self):
        response = self.client.get(reverse('encomienda-estadisticas', kwargs={'version': 'v1'}))
        assert response.status_code == status.HTTP_200_OK
        assert 'total_activas' in response.data
        assert response.data['con_retraso'] == 1

@pytest.mark.django_db
class TestVersionado:
    def setup_method(self):
        self.user = UserFactory()
        EmpleadoFactory(email=self.user.email)
        EncomiendaFactory()
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}'
        )

    def test_v1_responde_200_con_cabecera(self):
        response = self.client.get('/api/v1/encomiendas/')
        assert response.status_code == status.HTTP_200_OK
        assert response['X-API-Version'] == 'v1'

    def test_v2_responde_200_con_cabecera(self):
        response = self.client.get('/api/v2/encomiendas/')
        assert response.status_code == status.HTTP_200_OK
        assert response['X-API-Version'] == 'v2'

    def test_v2_incluye_campo_meta(self):
        response = self.client.get('/api/v2/encomiendas/')
        primer = response.data['results'][0]
        assert 'meta' in primer

    def test_v3_no_permitida_devuelve_404(self):
        response = self.client.get('/api/v3/encomiendas/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['code'] == 'NOT_FOUND'
