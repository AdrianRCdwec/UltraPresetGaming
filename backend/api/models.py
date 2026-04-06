from django.db import models


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

    @property
    def precio_final(self):
        descuento = (self.precio_base * self.descuento_porcentaje) / 100
        return round((self.precio_base - descuento) + self.gastos_envio, 2)

    def __str__(self):
        return f"{self.producto.nombre} en {self.tienda.nombre} - {self.precio_final}€"