const API_BASE = 'http://127.0.0.1:8000/api/productos/';
const MEDIA_BASE = 'http://127.0.0.1:8000';

// Estado del carrito
const carrito = [];

// ─── INIT ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    cargarCarrusel('VG_TEND', 'track-tendencias');
    cargarCarrusel('VG_RES',  'track-reservas');
    cargarCarrusel('VG_REC',  'track-recomendaciones');
    iniciarBuscador();
    iniciarCarrito();
});

// ─── CARRUSELES ──────────────────────────────────────────────────────────────
async function cargarCarrusel(categoria, trackId) {
    try {
        const res  = await fetch(`${API_BASE}?tipo=VG&categoria=${categoria}&page_size=100`);
        const data = await res.json();
        const juegos = data.results ?? data;

        if (!juegos.length) return;

        const track = document.getElementById(trackId);
        // Triplicamos para que el bucle infinito nunca se quede sin cards
        const html = [...juegos, ...juegos, ...juegos]
            .map(j => crearCardHTML(j))
            .join('');
        track.innerHTML = html;

        // Ajustamos velocidad según número de cards
        const duracion = juegos.length * 4;
        track.style.animationDuration = `${duracion}s`;

    } catch (e) {
        console.error(`Error cargando carrusel ${categoria}:`, e);
    }
}

function crearCardHTML(juego, clicable = false) {
    const precio  = precioMinimo(juego.ofertas);
    const imagen = juego.imagen ? juego.imagen : '../images/placeholder.png';
    const onclick = clicable ? `onclick="abrirDetalle(${juego.id})"` : '';

    return `
        <a class="card" href="#" ${onclick}>
            <img src="${imagen}" alt="${juego.nombre}" loading="lazy">
            <p class="titulo">${juego.nombre}</p>
            <p class="precio">${precio}</p>
        </a>
    `;
}

function precioMinimo(ofertas) {
    if (!ofertas || !ofertas.length) return 'Sin precio';
    const min = Math.min(...ofertas.map(o => parseFloat(o.precio_final)));
    return `${min.toFixed(2)} €`;
}

// ─── BUSCADOR ────────────────────────────────────────────────────────────────
function iniciarBuscador() {
    const input      = document.querySelector('.buscador');
    const form       = document.querySelector('.buscador-form');
    const secciones  = document.querySelectorAll('.tendencias, .reservas, .recomendaciones');
    const secResultados = document.getElementById('seccion-resultados');
    const gridResultados = document.getElementById('grid-resultados');
    const contador   = document.getElementById('contador-resultados');

    let timeout = null;

    input.addEventListener('input', () => {
        clearTimeout(timeout);
        const query = input.value.trim();

        if (!query) {
            // Volver a mostrar carruseles
            secResultados.style.display = 'none';
            secciones.forEach(s => s.style.display = '');
            return;
        }

        // Ocultar carruseles, mostrar resultados
        secciones.forEach(s => s.style.display = 'none');
        secResultados.style.display = '';

        timeout = setTimeout(async () => {
            gridResultados.innerHTML = '<p class="buscando">Buscando...</p>';
            try {
                const res  = await fetch(`${API_BASE}?tipo=VG&search=${encodeURIComponent(query)}&page_size=50`);
                const data = await res.json();
                const juegos = data.results ?? data;

                contador.textContent = `${juegos.length} resultado${juegos.length !== 1 ? 's' : ''}`;

                if (!juegos.length) {
                    gridResultados.innerHTML = '<p class="sin-resultados">No se encontraron juegos</p>';
                    return;
                }

                gridResultados.innerHTML = juegos.map(j => crearCardResultado(j)).join('');

            } catch (e) {
                gridResultados.innerHTML = '<p class="sin-resultados">Error al buscar</p>';
            }
        }, 300); // Espera 300ms tras dejar de escribir
    });

    // Evitar que el form recargue la página
    form.addEventListener('submit', e => e.preventDefault());
}

function crearCardResultado(juego) {
    const precio = precioMinimo(juego.ofertas);
    const imagen = juego.imagen ? juego.imagen : '../images/placeholder.png';

    return `
        <div class="card-resultado">
            <img src="${imagen}" alt="${juego.nombre}" loading="lazy">
            <div class="card-resultado-info">
                <p class="titulo">${juego.nombre}</p>
                <p class="precio">${precio}</p>
            </div>
            <button class="btn-añadir" onclick='añadirAlCarrito(${JSON.stringify(juego)})'>
                + Añadir
            </button>
        </div>
    `;
}

// ─── CARRITO ─────────────────────────────────────────────────────────────────
function iniciarCarrito() {
    document.getElementById('btn-carrito-flotante').addEventListener('click', abrirCarrito);
    document.getElementById('carrito-cerrar').addEventListener('click', cerrarCarrito);
    document.getElementById('carrito-overlay').addEventListener('click', cerrarCarrito);
}

function abrirCarrito() {
    document.getElementById('carrito-panel').classList.add('abierto');
    document.getElementById('carrito-overlay').classList.add('visible');
}

function cerrarCarrito() {
    document.getElementById('carrito-panel').classList.remove('abierto');
    document.getElementById('carrito-overlay').classList.remove('visible');
}

function añadirAlCarrito(juego) {
    const existente = carrito.find(item => item.id === juego.id);
    if (existente) {
        existente.cantidad++;
    } else {
        carrito.push({ ...juego, cantidad: 1 });
    }
    actualizarCarritoUI();
    parpadearCarrito();
}

function parpadearCarrito() {
    const btn = document.getElementById('btn-carrito-flotante');
    btn.classList.add('carrito-parpadeando');
    setTimeout(() => btn.classList.remove('carrito-parpadeando'), 800);
}

function eliminarDelCarrito(id) {
    const idx = carrito.findIndex(item => item.id === id);
    if (idx !== -1) carrito.splice(idx, 1);
    actualizarCarritoUI();
}

function actualizarCarritoUI() {
    const contenedor = document.getElementById('carrito-items');
    const badge      = document.getElementById('carrito-badge');
    const total      = document.getElementById('carrito-total');

    const totalItems = carrito.reduce((acc, i) => acc + i.cantidad, 0);
    badge.textContent = totalItems;

    if (!carrito.length) {
        contenedor.innerHTML = '<p class="carrito-vacio">Tu carrito está vacío</p>';
        total.textContent = '0,00 €';
        return;
    }

    let suma = 0;
    contenedor.innerHTML = carrito.map(item => {
        const precio = item.ofertas?.length
            ? parseFloat(item.ofertas[0].precio_final)
            : 0;
        const subtotal = precio * item.cantidad;
        suma += subtotal;
        const imagen = item.imagen ? item.imagen : '../images/placeholder.png';

        return `
            <div class="carrito-item">
                <img src="${imagen}" alt="${item.nombre}">
                <div class="carrito-item-info">
                    <p class="carrito-item-nombre">${item.nombre}</p>
                    <p class="carrito-item-precio">${subtotal.toFixed(2)} €</p>
                </div>
                <button class="btn-eliminar" onclick="eliminarDelCarrito(${item.id})">✕</button>
            </div>
        `;
    }).join('');

    total.textContent = `${suma.toFixed(2)} €`;
}