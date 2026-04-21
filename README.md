# UltraPresetGaming

**UltraPresetGaming** es una aplicación web comparadora de precios de hardware y videojuegos desarrollada como Trabajo de Fin de Ciclo (Tipo 2) del ciclo formativo de 2.º DAW.
El objetivo es ofrecer a los usuarios una forma sencilla y visual de comparar el precio y la disponibilidad de los mismos productos en distintas tiendas y plataformas online (PcComponentes, Coolmod, Alternate, LifeInformatica, NeoByte, Steam, PlayStation Store, etc.).

> **Tecnologías usadas**  
> * Front‑end: HTML5 semántico, CSS modular (variables, media‑queries), JavaScript vanilla (puro).  
> * Back‑end: Django + Django REST Framework, API RESTful.  
> * Autenticación: JWT.  
> * Base de datos: SQLite (optimizada para concurrencia en lectura).

---

## Índice

1. [Descripción del proyecto](#descripción-del-proyecto)  
2. [Arquitectura](#arquitectura)  
3. [Endpoints de la API](#endpoints)  
4. [Modelos y relaciones](#modelos-y-relaciones)  
5. [Instalación y ejecución](#instalación-y-ejecución)  
6. [Conexión con el front‑end](#conexión-con-el-front‑end)  
7. [Licencia](#licencia)  
8. [Contacto](#contacto)

---

## Descripción del proyecto

UltraPresetGaming permite a los usuarios comparar precios de hardware y videojuegos en tiempo real entre distintas tiendas y plataformas.  
El usuario puede iniciar sesión con su cuenta (JWT) y usar el comparador, el carrito de compras y el panel de perfil.

El proyecto está pensado para ser usado por gamers, entusiastas de la tecnología y cualquier persona que busque la mejor oferta.

---

## Arquitectura

```
┌───────────────────────────────────────┐
│               Front‑end               │
│        (HTML5, CSS, JavaScript)       │
└─────┬─────────────────────────────┬───┘
      │                             │
┌─────▼────────────┐          ┌─────▼─────┐
│   Header         │          │ API REST  │
│ (auth_header.js) │          │ (Django)  │
└─────▲────────────┘          └─────▲─────┘
      │                             │
┌─────┴─────┐                 ┌─────┴─────┐
│   Carrito │                 │  Modelo   │
│   (JS)    │                 │  (SQLite) │
└─────▲─────┘                 └─────▲─────┘
      │                             │
┌─────┴─────┐                 ┌─────┴───────┐
│ Comparador│                 │ Serializador│
│  (HTML)   │                 │    (DRF)    │
└───────────┘                 └─────────────┘
```

- **Front‑end**: páginas semánticas (header, nav, main, aside, footer) con media‑queries para dispositivos móviles, tablet y escritorio.  
- **Back‑end**: Django 3.x con Django‑REST‑Framework, 5 endpoints CRUD (GET, POST, PUT, PATCH, DELETE).  
- **JWT**: autenticación con token guardado en `localStorage`.  
- **Modelo de datos**: `Producto`, `Tienda`, `Usuario`, `Carrito`, con relación N:N entre `Carrito` y `Producto`.  

---

## Endpoints

| Método | Ruta | Parámetros | Acción |
|--------|------|------------|--------|
| GET | `/api/productos/` | `?categoria=hardware` | Lista todos los productos. |
| POST | `/api/carrito/` | `producto_id` en body | Añade un producto al carrito. |
| PUT | `/api/carrito/<int:pk>/` | `producto_id` en body | Actualiza la cantidad del producto. |
| PATCH | `/api/carrito/<int:pk>/` | `cantidad=2` en query | Reduce la cantidad en 1. |
| DELETE | `/api/carrito/<int:pk>/` | | Elimina el carrito. |

> Todos los endpoints aceptan/retornan **JSON** y requieren el encabezado `Authorization: Bearer <token>` cuando la operación es privada.

---

## Modelos y relaciones

```python
class Producto(models.Model):
    nombre = models.CharField(max_length=255, db_index=True)
    categoria = models.CharField(max_length=255, db_index=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    url_imagen = models.URLField()
    tienda = models.ForeignKey('Tienda', on_delete=models.CASCADE)

class Tienda(models.Model):
    nombre = models.CharField(max_length=100, db_index=True)
    url_base = models.URLField()

class Carrito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    productos = models.ManyToManyField(Producto, through='DetalleCarrito')
    total = models.DecimalField(max_digits=10, decimal_places=2)

class DetalleCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
```

---

## Instalación y ejecución

1. **Clonar el repositorio**  
   ```bash
   git clone https://github.com/tu_usuario/UltraPresetGaming.git
   cd UltraPresetGaming
   ```

2. **Crear entorno virtual**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Migraciones**  
   ```bash
   python manage.py migrate
   ```

4. **Iniciar servidor**  
   ```bash
   python manage.py runserver
   ```

5. **Acceder a la aplicación**  
   Navega a `http://127.0.0.1:8000/` y empieza a usar el comparador.

---

## Conexión con el front‑end

El front‑end consume los endpoints a través de `fetch`:

```js
fetch('/api/productos/', {
    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
})
.then(r => r.json())
.then(data => { /* renderiza productos */ })
```

Para crear un carrito nuevo:

```js
fetch('/api/carrito/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
    },
    body: JSON.stringify({ usuario: 'juan', productos: [1,2,3] })
})
```

---

## Pruebas

> (Pendiente) Se planifica introducir pruebas unitarias con **pytest** para las funciones críticas del back‑end y del motor de scraping.

---

## Licencia

MIT License – Vea el archivo `LICENSE`.

---

## Contacto

- **Autor:** Adrián Rodríguez Campos  
- **GitHub:** https://github.com/AdrianRCdwec/UltraPresetGaming

---