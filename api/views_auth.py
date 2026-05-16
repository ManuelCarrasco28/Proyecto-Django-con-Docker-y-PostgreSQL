from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class EncomiendaTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar datos personalizados al payload del JWT
        token['username'] = user.username
        token['email'] = user.email
        
        try:
            # Intentamos obtener el perfil de empleado asociado al usuario
            emp = user.empleado
            token['empleado_id'] = emp.id
            token['empleado_cod'] = emp.codigo
            token['cargo'] = emp.cargo
        except Exception:
            # Si el usuario no tiene perfil de empleado, ignoramos estos campos
            pass
            
        return token

class EncomiendaTokenView(TokenObtainPairView):
    """
    Vista personalizada para obtener el token JWT incluyendo datos del empleado.
    """
    serializer_class = EncomiendaTokenSerializer
