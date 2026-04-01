# api/backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
            
        try:
            # Busca si lo que ha escrito coincide con un email o con un username
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
            
            # Comprueba la contraseña
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None