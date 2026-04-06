from django.contrib import admin
from .models import Producto, Tienda, Oferta

# Configuración visual de la tabla Ofertas
class OfertaAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tienda', 'precio_base', 'precio_final', 'fecha_actualizacion')
    list_filter = ('tienda',) # He añadido un filtro por tienda que te será muy útil
    search_fields = ('producto__nombre',) # Y un buscador por nombre de producto

# Configuración visual de la tabla Productos (Opcional pero muy recomendable)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'tipo')
    list_filter = ('categoria', 'tipo')
    search_fields = ('nombre',)

# Registramos los modelos
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Tienda)
admin.site.register(Oferta, OfertaAdmin)