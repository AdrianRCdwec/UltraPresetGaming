from django.shortcuts import render
from rest_framework import viewsets
from .models import Tienda, Producto, Oferta
from .serializers import TiendaSerializer, ProductoSerializer, OfertaSerializer

# ModelViewSet ya crea automáticamente el GET, POST, PUT, PATCH y DELETE obligatorios del trabajo
class TiendaViewSet(viewsets.ModelViewSet):
    queryset = Tienda.objects.all()
    serializer_class = TiendaSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    
    # Ejemplo para cumplir el requisito de 'query params' (?search=ryzen)
    def get_queryset(self):
        queryset = Producto.objects.all()
        search = self.request.query_params.get('search', None)
        if search is not None:
            queryset = queryset.filter(nombre__icontains=search)
        return queryset

class OfertaViewSet(viewsets.ModelViewSet):
    queryset = Oferta.objects.all()
    serializer_class = OfertaSerializer
