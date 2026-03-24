from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TiendaViewSet, ProductoViewSet, OfertaViewSet

router = DefaultRouter()
router.register(r'tiendas', TiendaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'ofertas', OfertaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
