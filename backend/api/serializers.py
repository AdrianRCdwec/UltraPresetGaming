from rest_framework import serializers
from .models import Tienda, Producto, Oferta

class TiendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tienda
        fields = '__all__'

class OfertaSerializer(serializers.ModelSerializer):
    # Traemos el nombre de la tienda para que el frontend lo lea más fácil
    tienda_nombre = serializers.ReadOnlyField(source='tienda.nombre')
    # Exponemos el campo calculado de precio final
    precio_final = serializers.ReadOnlyField()

    class Meta:
        model = Oferta
        fields = [
            'id', 'tienda', 'tienda_nombre', 'precio_base', 'descuento_porcentaje',
            'gastos_envio', 'precio_final', 'enlace_compra', 'fecha_actualizacion'
            ]

class ProductoSerializer(serializers.ModelSerializer):
    # Anidamos las ofertas para que al pedir un producto, nos lleguen todos sus precios
    ofertas = OfertaSerializer(source='oferta_set', many=True, read_only=True)

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'tipo', 'descripcion', 'ofertas']
