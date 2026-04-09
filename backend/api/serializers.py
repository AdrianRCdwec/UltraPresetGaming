from rest_framework import serializers
from .models import Tienda, Producto, Oferta, ItemGuardado, Perfil
from django.contrib.auth.models import User

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
        fields = ['id', 'nombre', 'tipo', 'categoria', 'descripcion', 'imagen', 'ofertas']


class ItemGuardadoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_imagen = serializers.SerializerMethodField()

    class Meta:
        model = ItemGuardado
        fields = ['id', 'producto', 'producto_nombre', 'producto_imagen', 'ranura', 'fecha_agregado']
        read_only_fields = ['id', 'fecha_agregado']

    def get_producto_imagen(self, obj):
        if obj.producto.imagen:
            return obj.producto.imagen.url
        return None

class PerfilSerializer(serializers.ModelSerializer):
    # Traemos campos del modelo User
    username = serializers.CharField(source='usuario.username', read_only=True)
    email = serializers.EmailField(source='usuario.email', read_only=True)
    nombre = serializers.CharField(source='usuario.first_name', required=False, allow_blank=True)

    class Meta:
        model = Perfil
        fields = ['username', 'email', 'nombre', 'apodo', 'foto_perfil']

    def update(self, instance, validated_data):
        # 1. Extraemos y guardamos el "nombre" en el modelo User original
        usuario_data = validated_data.pop('usuario', {})
        if 'first_name' in usuario_data:
            instance.usuario.first_name = usuario_data['first_name']
            instance.usuario.save()

        # 2. Guardamos el apodo y la foto en el modelo Perfil
        instance.apodo = validated_data.get('apodo', instance.apodo)
        
        if 'foto_perfil' in validated_data:
            instance.foto_perfil = validated_data.get('foto_perfil')

        instance.save()
        return instance
