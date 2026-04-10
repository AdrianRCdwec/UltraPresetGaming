from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Tienda(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    url_base = models.URLField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    TIPO_CHOICES = [
        ('HW', 'Hardware'),
        ('VG', 'Videojuego'),
    ]

    CATEGORIA_CHOICES = [
        ('CPU',    'Procesador'),
        ('MB',     'Placa Base'),
        ('RAM',    'Memoria RAM'),
        ('CASE',   'Caja/Torre'),
        ('AIR',    'Refrigeración Aire'),
        ('LIQ',    'Refrigeración Líquida'),
        ('GPU',    'Tarjeta Gráfica'),
        ('PSU',    'Fuente Alimentación'),
        ('SSD',    'Almacenamiento'),
        ('MON',    'Monitor'),
        ('NONE',   'Otro'),
        # Videojuegos
        ('VG_TEND', 'VG - Tendencia'),
        ('VG_RES',  'VG - Reserva'),
        ('VG_REC',  'VG - Recomendación'),
    ]

    nombre      = models.CharField(max_length=200)
    tipo        = models.CharField(max_length=2, choices=TIPO_CHOICES, default='HW')
    categoria   = models.CharField(max_length=7, choices=CATEGORIA_CHOICES, default='NONE')
    descripcion = models.TextField(blank=True, null=True)
    imagen      = models.ImageField(upload_to='productos/', blank=True, null=True)  # ← NUEVO
    tiendas     = models.ManyToManyField(Tienda, through='Oferta')

    def __str__(self):
        return self.nombre


class Oferta(models.Model):
    producto              = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tienda                = models.ForeignKey(Tienda, on_delete=models.CASCADE)
    precio_base           = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_porcentaje  = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    gastos_envio          = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    enlace_compra         = models.URLField(max_length=500)
    fecha_actualizacion   = models.DateTimeField(auto_now=True)
    disponible            = models.BooleanField(default=True)

    @property
    def precio_final(self):
        descuento = (self.precio_base * self.descuento_porcentaje) / 100
        return round((self.precio_base - descuento) + self.gastos_envio, 2)

    def __str__(self):
        return f"{self.producto.nombre} en {self.tienda.nombre} - {self.precio_final}€"


class ItemGuardado(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items_guardados')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    ranura = models.CharField(max_length=50) # Ej: 'panel-procesador', 'panel-placa', 'videojuego'
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Asegura que el usuario no pueda tener dos productos en la misma ranura
        unique_together = ('usuario', 'ranura')

    def __str__(self):
        return f"{self.ranura}: {self.producto.nombre} ({self.usuario.username})"

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    apodo = models.CharField(max_length=50, blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

# Esta señal crea un "Perfil" automáticamente cuando alguien se registra
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(usuario=instance)

class AlertaPrecio(models.Model):
    # RELACIÓN N:M TERNARIA PERFECTA (Conecta Usuario, Producto y Tienda)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alertas')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE)
    
    # Datos extra de la relación
    precio_objetivo = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    class Meta:
        # Evita que un usuario cree dos alertas idénticas para el mismo producto y tienda
        unique_together = ('usuario', 'producto', 'tienda')

    def __str__(self):
        return f"Alerta de {self.usuario.username} para {self.producto.nombre} en {self.tienda.nombre} (< {self.precio_objetivo}€)"