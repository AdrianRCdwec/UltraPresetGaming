from django.db import models

class Tienda(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    url_base = models.URLField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    # Tipos de producto para poder filtrarlos luego
    TIPO_CHOICES = [
        ('HW', 'Hardware'),
        ('VG', 'Videojuego'),
    ]
    
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default='HW')
    descripcion = models.TextField(blank=True, null=True)
    # Aquí se cumple el requisito de la relación N:M (ternaria) a través de "Oferta"
    tiendas = models.ManyToManyField(Tienda, through='Oferta')

    def __str__(self):
        return self.nombre

class Oferta(models.Model):
    # Esta es la tabla intermedia que une Productos con Tiendas
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE)
    
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    gastos_envio = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    enlace_compra = models.URLField(max_length=500)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    @property
    def precio_final(self):
        # Esta función calcula automáticamente el precio real que pide el trabajo
        descuento = (self.precio_base * self.descuento_porcentaje) / 100
        return round((self.precio_base - descuento) + self.gastos_envio, 2)

    def __str__(self):
        return f"{self.producto.nombre} en {self.tienda.nombre} - {self.precio_final}€"
