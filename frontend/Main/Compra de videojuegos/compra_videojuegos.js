const API_BASE = 'http://127.0.0.1:8000/api/productos/';
const MEDIA_BASE = 'http://127.0.0.1:8000';

// Estado del carrito (cargamos desde localStorage si existe)
let carrito = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];
let carritoHardware = JSON.parse(localStorage.getItem('carrito_hardware')) || {};

function guardarCarritoVideojuegos() {
    localStorage.setItem('carrito_videojuegos', JSON.stringify(carrito));
}

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

    // Comprobamos si el juego ya existe en el carrito
    const estaEnCarrito = carrito.some(item => item.id === juego.id);
    const textoBoton = estaEnCarrito ? 'Añadido' : '+ Añadir';
    const disabledAttr = estaEnCarrito ? 'disabled style="background: #a5a5a5; cursor: not-allowed;"' : '';

    return `
        <div class="card-resultado">
            <img src="${imagen}" alt="${juego.nombre}" loading="lazy">
            <div class="card-resultado-info">
                <p class="titulo">${juego.nombre}</p>
                <p class="precio">${precio}</p>
            </div>
            <button id="btn-add-${juego.id}" class="btn-añadir" ${disabledAttr} onclick='añadirAlCarrito(${JSON.stringify(juego)})'>
                ${textoBoton}
            </button>
        </div>
    `;
}

// ─── CARRITO ─────────────────────────────────────────────────────────────────
function iniciarCarrito() {
    document.getElementById('btn-carrito-flotante').addEventListener('click', abrirCarrito);
    document.getElementById('carrito-cerrar').addEventListener('click', cerrarCarrito);
    document.getElementById('carrito-overlay').addEventListener('click', cerrarCarrito);
    actualizarCarritoUI();
}

function abrirCarrito() {
    document.getElementById('carrito-panel').classList.add('abierto');
    document.getElementById('carrito-overlay').classList.add('visible');
    document.body.style.overflow = 'hidden'; // Bloquear scroll
    window.switchTab('vg');
}

function cerrarCarrito() {
    document.getElementById('carrito-panel').classList.remove('abierto');
    document.getElementById('carrito-overlay').classList.remove('visible');
    document.body.style.overflow = ''; // Recuperar scroll
}

function añadirAlCarrito(juego) {
    const existente = carrito.find(item => item.id === juego.id);
    if (existente) return; // Si ya existe, no hacemos nada

    carrito.push(juego);
    guardarCarritoVideojuegos();
    actualizarCarritoUI();
    parpadearCarrito();

    // Cambiar el botón visualmente a "Añadido" al instante si estamos en la búsqueda
    const btn = document.getElementById(`btn-add-${juego.id}`);
    if (btn) {
        btn.textContent = 'Añadido';
        btn.disabled = true;
        btn.style.background = '#a5a5a5';
        btn.style.cursor = 'not-allowed';
    }
}

function parpadearCarrito() {
    const btn = document.getElementById('btn-carrito-flotante');
    btn.classList.add('carrito-parpadeando');
    setTimeout(() => btn.classList.remove('carrito-parpadeando'), 800);
}

window.switchTab = function(tab) {
    document.getElementById('carrito-panel').setAttribute('data-tab', tab);
    document.getElementById('tab-hw').classList.toggle('active', tab === 'hw');
    document.getElementById('tab-vg').classList.toggle('active', tab === 'vg');
    document.getElementById('carrito-items-hw').style.display = (tab === 'hw') ? 'flex' : 'none';
    document.getElementById('carrito-items-vg').style.display = (tab === 'vg') ? 'flex' : 'none';
    actualizarCarritoUI();
};

window.eliminarDelCarritoVG = function(id) {
    const idx = carrito.findIndex(item => item.id === id);
    if (idx !== -1) carrito.splice(idx, 1);
    guardarCarritoVideojuegos();
    actualizarCarritoUI();

    // Restaurar el botón si el usuario sigue viendo la tarjeta de búsqueda
    const btn = document.getElementById(`btn-add-${id}`);
    if (btn) {
        btn.textContent = '+ Añadir';
        btn.disabled = false;
        btn.style.background = ''; // Restaura el color CSS original
        btn.style.cursor = 'pointer';
    }
};

window.eliminarDelCarritoHW = function(ranura) {
    delete carritoHardware[ranura];
    localStorage.setItem('carrito_hardware', JSON.stringify(carritoHardware));
    actualizarCarritoUI();
};

function actualizarCarritoUI() {
    carrito = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];
    carritoHardware = JSON.parse(localStorage.getItem('carrito_hardware')) || {};

    const tabActual = document.getElementById('carrito-panel').getAttribute('data-tab') || 'vg';
    const contHW = document.getElementById('carrito-items-hw');
    const contVG = document.getElementById('carrito-items-vg');

    if (!contHW || !contVG) return;

    // -- VIDEOJUEGOS --
    // (Ojo: en Montador_hardware.js recuerda usar "carritoVideojuegos" y en compra_videojuegos.js usar "carrito")
    const arrayJuegos = (typeof carrito !== 'undefined' && carrito.length !== undefined) ? carrito : carritoVideojuegos;
    
    const totalItemsVG = arrayJuegos.length;
    document.getElementById('badge-vg-tab').textContent = totalItemsVG;
    let sumaVG = 0;

    if (arrayJuegos.length === 0) {
        contVG.innerHTML = '<p class="carrito-vacio">Sin juegos</p>';
    } else {
        contVG.innerHTML = arrayJuegos.map(item => {
            const precio = item.ofertas?.length ? parseFloat(item.ofertas[0].precio_final) : 0;
            sumaVG += precio; // Ya no multiplicamos por cantidad
            const img = item.imagen || '../images/placeholder.png';
            return `
                <div class="carrito-item" style="display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; background: #f7f7f7;">
                    <img src="${img}" style="width: 54px; height: 54px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">
                    <div style="flex: 1; min-width: 0;">
                        <span style="font-size: 10px; color: #888; text-transform: uppercase; font-weight: 800;">Videojuego</span>
                        <p style="font-size: 13px; font-weight: 700; margin: 0 0 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #101828;">${item.nombre}</p>
                        <p style="font-size: 14px; font-weight: 800; color: #6a2fd8; margin: 0;">${precio.toFixed(2)} €</p>
                    </div>
                    <button class="btn-eliminar" onclick="window.eliminarDelCarritoVG(${item.id})" style="background: none; border: none; font-size: 16px; cursor: pointer; color: #bbb; padding: 4px;">✕</button>
                </div>`;
        }).join('');
    }

    // -- HARDWARE --
    const itemsHW = Object.values(carritoHardware);
    document.getElementById('badge-hw-tab').textContent = itemsHW.length;
    let sumaHW = 0;

    if (itemsHW.length === 0) {
        contHW.innerHTML = '<p class="carrito-vacio">Tu PC está vacío</p>';
    } else {
        contHW.innerHTML = itemsHW.map(item => {
            sumaHW += item.precio;
            return `
                <div class="carrito-item" style="display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; background: #f7f7f7;">
                    <img src="${item.imagen}" style="width: 54px; height: 54px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">
                    <div style="flex: 1; min-width: 0;">
                        <span style="font-size: 10px; color: #888; text-transform: uppercase; font-weight: 800;">Hardware</span>
                        <p style="font-size: 13px; font-weight: 700; margin: 0 0 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #101828;">${item.nombre}</p>
                        <p style="font-size: 14px; font-weight: 800; color: #6a2fd8; margin: 0;">${item.precio.toFixed(2)} €</p>
                    </div>
                    <button class="btn-eliminar" onclick="window.eliminarDelCarritoHW('${item.ranura}')" style="background: none; border: none; font-size: 16px; cursor: pointer; color: #bbb; padding: 4px;">✕</button>
                </div>`;
        }).join('');
    }

    // -- TOTALES --
    document.getElementById('gran-total-header').textContent = (sumaHW + sumaVG).toFixed(2) + ' €';
    document.getElementById('carrito-total-seccion').textContent = (tabActual === 'vg' ? sumaVG : sumaHW).toFixed(2) + ' €';
    
    const badgeFlotante = document.getElementById('carrito-badge');
    if (badgeFlotante) badgeFlotante.textContent = itemsHW.length + totalItemsVG;
}