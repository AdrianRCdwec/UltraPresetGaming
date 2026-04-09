from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import TiendaViewSet, ProductoViewSet, OfertaViewSet, RegisterView, LoginView, PerfilView, ItemGuardadoViewSet

router = DefaultRouter()
router.register(r'tiendas', TiendaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'ofertas', OfertaViewSet)
router.register(r'configuracion', ItemGuardadoViewSet, basename='configuracion')

urlpatterns = [
    path('', include(router.urls)),

    # ─── AUTH ────────────────────────────────────────────────────────────────
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/',    LoginView.as_view(),    name='login'),
    path('auth/refresh/',  TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/perfil/',   PerfilView.as_view(),   name='perfil'),
]