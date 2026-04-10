from .models import Tienda, Producto, Oferta, ItemGuardado, Perfil, AlertaPrecio
from .serializers import TiendaSerializer, ProductoSerializer, OfertaSerializer, ItemGuardadoSerializer, PerfilSerializer, AlertaPrecioSerializer
from rest_framework import viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

# Configuramos la paginación (de 10 en 10)
class PaginacionProductos(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all().order_by('id')
    serializer_class = ProductoSerializer
    pagination_class = PaginacionProductos # Activar paginación
    
    def get_queryset(self):
        queryset = Producto.objects.all().order_by('id')
        search = self.request.query_params.get('search', None)
        categoria = self.request.query_params.get('categoria', None)
        tipo = self.request.query_params.get('tipo', None)
        
        # Filtro de texto
        if search is not None:
            queryset = queryset.filter(nombre__icontains=search)
            
        # Filtro estricto por categoría (ej: Solo placas base)
        if categoria is not None:
            queryset = queryset.filter(categoria=categoria)
            
        if tipo is not None:
            queryset = queryset.filter(tipo=tipo)
            
        return queryset

class TiendaViewSet(viewsets.ModelViewSet):
    queryset = Tienda.objects.all()
    serializer_class = TiendaSerializer

class OfertaViewSet(viewsets.ModelViewSet):
    queryset = Oferta.objects.all()
    serializer_class = OfertaSerializer

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username', '').strip()
        email    = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        password2 = request.data.get('password2', '')

        # Validaciones
        if not username or not email or not password:
            return Response({'error': 'Todos los campos son obligatorios.'}, status=400)

        if password != password2:
            return Response({'error': 'Las contraseñas no coinciden.'}, status=400)

        if len(password) < 8:
            return Response({'error': 'La contraseña debe tener al menos 8 caracteres.'}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Ese nombre de usuario ya está en uso.'}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({'error': 'Ese email ya está registrado.'}, status=400)

        # Crear usuario
        user = User.objects.create_user(username=username, email=email, password=password)

        # Devolver tokens directamente para que el usuario quede logueado
        refresh = RefreshToken.for_user(user)
        return Response({
            'access':   str(refresh.access_token),
            'refresh':  str(refresh),
            'username': user.username,
            'email':    user.email,
        }, status=201)


class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response({'error': 'Usuario y contraseña son obligatorios.'}, status=400)

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({'error': 'Usuario o contraseña incorrectos.'}, status=401)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access':   str(refresh.access_token),
            'refresh':  str(refresh),
            'username': user.username,
            'email':    user.email,
        })


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    # Función auxiliar: get_or_create evita que reviente si un usuario antiguo no tiene perfil
    def get_object(self):
        perfil, created = Perfil.objects.get_or_create(usuario=self.request.user)
        return perfil

    def get(self, request):
        perfil = self.get_object()
        serializer = PerfilSerializer(perfil, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        perfil = self.get_object()
        # partial=True permite enviar solo la foto, o solo el nombre, sin obligar a enviar todo
        serializer = PerfilSerializer(perfil, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ItemGuardadoViewSet(viewsets.ModelViewSet):
    serializer_class = ItemGuardadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ItemGuardado.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class AlertaPrecioViewSet(viewsets.ModelViewSet):
    serializer_class = AlertaPrecioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Solo devuelve las alertas del usuario logueado
        return AlertaPrecio.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)