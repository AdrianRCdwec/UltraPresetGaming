from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from .models import Tienda, Producto, Oferta
from .serializers import TiendaSerializer, ProductoSerializer, OfertaSerializer

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
        
        # Filtro de texto
        if search is not None:
            queryset = queryset.filter(nombre__icontains=search)
            
        # Filtro estricto por categoría (ej: Solo placas base)
        if categoria is not None:
            queryset = queryset.filter(categoria=categoria)
            
        return queryset

class TiendaViewSet(viewsets.ModelViewSet):
    queryset = Tienda.objects.all()
    serializer_class = TiendaSerializer

class OfertaViewSet(viewsets.ModelViewSet):
    queryset = Oferta.objects.all()
    serializer_class = OfertaSerializer
