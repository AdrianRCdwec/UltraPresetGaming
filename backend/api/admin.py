from django.contrib import admin
from .models import Producto, Tienda, Oferta

# Registramos los modelos para poder añadir datos manualmente
admin.site.register(Producto)
admin.site.register(Tienda)
admin.site.register(Oferta)
