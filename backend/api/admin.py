from django.contrib import admin
from .models import Producto, Tienda, Oferta
from .scraper import actualizar_precio_oferta

# Acción personalizada para el panel de administración
@admin.action(description='Actualizar precios mediante Scraping')
def actualizar_precios(modeladmin, request, queryset):
    actualizados = 0
    fallidos = 0
    
    for oferta in queryset:
        if actualizar_precio_oferta(oferta):
            actualizados += 1
        else:
            fallidos += 1
            
    modeladmin.message_user(request, f"Precios actualizados: {actualizados}. Fallidos/Protegidos: {fallidos}")

# Configuración visual de la tabla Ofertas
class OfertaAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tienda', 'precio_base', 'precio_final', 'fecha_actualizacion')
    actions = [actualizar_precios]

# Registramos los modelos
admin.site.register(Producto)
admin.site.register(Tienda)
admin.site.register(Oferta, OfertaAdmin)
