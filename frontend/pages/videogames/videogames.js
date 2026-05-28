import { API_PRODUCTOS_URL } from '../../shared/js/api-config.js';
import {
    iniciarPanelCarrito,
    cargarCarritoVGDesdeServidor,
    añadirAlCarritoVG,
    getCarritoVG,
} from '../../shared/js/carrito.js';

// ─── INIT ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    cargarCarrusel('VG_ACC', 'track-tendencias');
    cargarCarrusel('VG_RPG', 'track-reservas');
    cargarCarrusel('VG_IND', 'track-recomendaciones');

    iniciarBuscador();
    iniciarModal();

    // El carrito ahora lo gestiona el módulo central
    iniciarPanelCarrito('vg');

    // Sincronizar videojuegos guardados y actualizar botones visuales
    cargarCarritoVGDesdeServidor((juegosGuardados) => {
        juegosGuardados.forEach(juego => {
            marcarBotonAñadido(juego.id);
        });
    });
});

// ─── CARRUSELES ──────────────────────────────────────────────────────────────
async function cargarCarrusel(categoria, trackId) {
    try {
        const res = await fetch(`${API_PRODUCTOS_URL}?tipo=VG&categoria=${categoria}&page_size=100`);
        const data = await res.json();
        const juegos = data.results ?? data;

        if (!juegos.length) return;

        const track = document.getElementById(trackId);
        if (!track) return;

        const html = [...juegos, ...juegos, ...juegos]
            .map(j => crearCardHTML(j))
            .join('');

        track.innerHTML = html;

        const duracion = juegos.length * 4;
        track.style.animationDuration = `${duracion}s`;

    } catch (e) {
        console.error(`Error cargando carrusel ${categoria}:`, e);
    }
}

function crearCardHTML(juego) {
    const precio = precioMinimo(juego.ofertas);
    const imagen = juego.imagen_url ? juego.imagen_url : '../../assets/images/misc/placeholderItem.jpg';

    return `
        <div class="card" onclick="window.abrirDetalle(${juego.id})" style="cursor:pointer;">
            <img src="${imagen}" alt="${juego.nombre}" loading="lazy">
            <p class="titulo">${juego.nombre}</p>
            <p class="precio">${precio}</p>
        </div>
    `;
}

function precioMinimo(ofertas) {
    if (!ofertas || !ofertas.length) return 'Sin precio';
    const min = Math.min(...ofertas.map(o => parseFloat(o.precio_final)));
    return `${min.toFixed(2).replace('.', ',')} €`;
}

// ─── BUSCADOR ────────────────────────────────────────────────────────────────
function iniciarBuscador() {
    const input = document.querySelector('.buscador');
    const form = document.querySelector('.buscador-form');
    const secciones = document.querySelectorAll('.tendencias, .reservas, .recomendaciones');
    const secResultados = document.getElementById('seccion-resultados');
    const gridResultados = document.getElementById('grid-resultados');
    const contador = document.getElementById('contador-resultados');

    if (!input || !form || !secResultados || !gridResultados || !contador) return;

    let timeout = null;

    input.addEventListener('input', () => {
        clearTimeout(timeout);
        const query = input.value.trim();

        if (!query) {
            secResultados.style.display = 'none';
            secciones.forEach(s => s.style.display = '');
            return;
        }

        secciones.forEach(s => s.style.display = 'none');
        secResultados.style.display = '';

        timeout = setTimeout(async () => {
            gridResultados.innerHTML = '<p class="buscando">Buscando...</p>';

            try {
                const res = await fetch(`${API_PRODUCTOS_URL}?tipo=VG&search=${encodeURIComponent(query)}&page_size=50`);
                const data = await res.json();
                const juegos = data.results ?? data;

                contador.textContent = `${juegos.length} resultado${juegos.length !== 1 ? 's' : ''}`;

                if (!juegos.length) {
                    gridResultados.innerHTML = '<p class="sin-resultados">No se encontraron juegos</p>';
                    return;
                }

                gridResultados.innerHTML = juegos.map(j => crearCardResultado(j)).join('');

                const botonesAdd = gridResultados.querySelectorAll('.btn-añadir');

                botonesAdd.forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();

                        const juegoId = parseInt(btn.dataset.juegoId, 10);
                        const juegoSeleccionado = juegos.find(j => j.id === juegoId);

                        if (juegoSeleccionado) {
                            añadirAlCarritoVG(juegoSeleccionado, (id) => {
                                marcarBotonAñadido(id);
                            });
                        }
                    });
                });

            } catch (e) {
                gridResultados.innerHTML = '<p class="sin-resultados">Error al buscar</p>';
            }
        }, 300);
    });

    form.addEventListener('submit', e => e.preventDefault());
}

function crearCardResultado(juego) {
    const precio = precioMinimo(juego.ofertas);
    const imagen = juego.imagen_url ? juego.imagen_url : '../../assets/images/misc/placeholderItem.jpg';

    const estaEnCarrito = getCarritoVG().some(item => item.id === juego.id);
    const textoBoton = estaEnCarrito ? 'Añadido' : '+ Añadir';
    const disabledAttr = estaEnCarrito ? 'disabled style="background: #a5a5a5; cursor: not-allowed;"' : '';

    return `
        <div class="card-resultado" onclick="window.abrirDetalle(${juego.id})" style="cursor:pointer;">
            <img src="${imagen}" alt="${juego.nombre}" loading="lazy">
            <div class="card-resultado-info">
                <p class="titulo">${juego.nombre}</p>
                <p class="precio">${precio}</p>
            </div>
            <button 
                type="button"
                id="btn-add-${juego.id}" 
                class="btn-añadir"
                data-juego-id="${juego.id}"
                ${disabledAttr}
            >
                ${textoBoton}
            </button>
        </div>
    `;
}

// ─── MODAL ───────────────────────────────────────────────────────────────────
function iniciarModal() {
    const modal = document.getElementById('modal-detalle-vg');
    const btnClose = document.getElementById('modal-close-vg');

    if (btnClose) {
        btnClose.addEventListener('click', cerrarModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) cerrarModal();
        });
    }
}

window.abrirDetalle = async function(juegoId) {
    const modal = document.getElementById('modal-detalle-vg');
    const contenido = document.getElementById('modal-contenido-vg');

    if (!modal || !contenido) return;

    modal.classList.add('visible');
    document.body.style.overflow = 'hidden';
    contenido.innerHTML = '<p class="modal-cargando">Cargando...</p>';

    try {
        const res = await fetch(`${API_PRODUCTOS_URL}${juegoId}/`);
        if (!res.ok) throw new Error(`Error ${res.status}`);

        const juego = await res.json();
        pintarModal(juego);
    } catch (e) {
        contenido.innerHTML = '<p class="modal-error">Error al cargar el juego.</p>';
    }
};

function pintarModal(juego) {
    const contenido = document.getElementById('modal-contenido-vg');
    if (!contenido) return;

    const imagen = juego.imagen_url ? juego.imagen_url : '../../assets/images/misc/placeholderItem.jpg';
    const estaEnCarrito = getCarritoVG().some(item => item.id === juego.id);
    const textoBoton = estaEnCarrito ? 'Añadido' : '+ Añadir al carrito';
    const disabledAttr = estaEnCarrito ? 'disabled style="background: #a5a5a5; cursor: not-allowed;"' : '';

    const ofertasHTML = juego.ofertas && juego.ofertas.length > 0
        ? [...juego.ofertas]
            .sort((a, b) => parseFloat(a.precio_final) - parseFloat(b.precio_final))
            .map(o => `
                <div class="modal-oferta">
                    <span class="modal-tienda">${o.tienda_nombre}</span>
                    <span class="modal-precio-oferta">${parseFloat(o.precio_final).toFixed(2).replace('.', ',')} €</span>
                    <a href="${o.enlace_compra || '#'}" target="_blank" rel="noopener noreferrer" class="modal-btn-compra">Comprar</a>
                </div>
            `)
            .join('')
        : '<p class="sin-resultados">No hay ofertas disponibles.</p>';

    contenido.innerHTML = `
        <img class="modal-imagen" src="${imagen}" alt="${juego.nombre}">
        <div class="modal-info">
            <h2 class="modal-titulo">${juego.nombre}</h2>
            <p class="modal-precio">${precioMinimo(juego.ofertas)}</p>
            <button class="btn-añadir-modal" id="btn-add-modal-${juego.id}" ${disabledAttr}>${textoBoton}</button>
            <div class="modal-ofertas">${ofertasHTML}</div>
        </div>
    `;

    const btnAñadir = document.getElementById(`btn-add-modal-${juego.id}`);
    if (btnAñadir && !estaEnCarrito) {
        btnAñadir.addEventListener('click', () => {
            añadirAlCarritoVG(juego, (id) => {
                marcarBotonAñadido(id);

                btnAñadir.textContent = 'Añadido';
                btnAñadir.disabled = true;
                btnAñadir.style.background = '#a5a5a5';
                btnAñadir.style.cursor = 'not-allowed';
            });
        });
    }
}

function cerrarModal() {
    const modal = document.getElementById('modal-detalle-vg');
    if (modal) modal.classList.remove('visible');
    document.body.style.overflow = '';
}

// ─── HELPERS UI ──────────────────────────────────────────────────────────────
function marcarBotonAñadido(juegoId) {
    const btn = document.getElementById(`btn-add-${juegoId}`);
    if (!btn) return;

    btn.textContent = 'Añadido';
    btn.disabled = true;
    btn.style.background = '#a5a5a5';
    btn.style.cursor = 'not-allowed';
}