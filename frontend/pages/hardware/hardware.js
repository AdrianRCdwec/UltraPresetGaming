import { API_PRODUCTOS_URL } from '../../shared/js/api-config.js';
import {
    iniciarPanelCarrito,
    cargarCarritoHWDesdeServidor,
    añadirAlCarritoHW,
    getCarritoHW,
    MAPA_NOMBRES_RANURA,
    MAPA_ICONOS_RANURA,
} from '../../shared/js/carrito.js';

let categoriaActual = '';
let paginaActual = 1;
let idPanelActual = '';

const MAPA_CATEGORIAS_PANEL = {
    'panel-procesador': 'CPU',
    'panel-placa': 'MB',
    'panel-ram': 'RAM',
    'panel-caja': 'CASE',
    'panel-aire': 'AIR',
    'panel-liquida': 'LIQ',
    'panel-gpu': 'GPU',
    'panel-psu': 'PSU',
    'panel-disco': 'SSD',
    'panel-monitor': 'MON',
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. Inicializar panel de carrito centralizado
    iniciarPanelCarrito('hw');

    // 2. Restaurar primero desde localStorage para no dejar la UI vacía
    restaurarSeleccionesHardware();
    gestionarExclusionRefrigeracion();
    
    // 3. Sincronizar después con servidor y volver a pintar
    cargarCarritoHWDesdeServidor((carritoSincronizado) => {
        restaurarSeleccionesHardware(carritoSincronizado);
        gestionarExclusionRefrigeracion();
    });

    // 4. Lógica de paneles y buscador
    const buscador = document.getElementById('buscador-hardware');
    const tarjetasHardware = document.querySelectorAll('.hw-card');

    tarjetasHardware.forEach(tarjeta => {
        tarjeta.addEventListener('click', (e) => {
            // Si hacen clic en "Ver Precios", no abrimos el panel
            if (e.target.tagName.toLowerCase() === 'a') return;

            document.body.style.overflow = 'hidden';

            idPanelActual = tarjeta.getAttribute('for');
            categoriaActual = MAPA_CATEGORIAS_PANEL[idPanelActual] || 'NONE';
            paginaActual = 1;

            if (buscador) buscador.value = '';

            const grid = document.getElementById('grid-resultados');
            if (grid) {
                grid.innerHTML = '<p style="text-align: center; color: #666; width: 100%; grid-column: span 2;">Cargando componentes...</p>';
            }

            setTimeout(() => {
                cargarProductos(categoriaActual, '', paginaActual, false);
            }, 100);
        });
    });

    // 4. Restaurar scroll al cerrar el panel de piezas
    const btnCerrarPanelPiezas = document.querySelector('.sidepanel-close');
    const overlayPanelPiezas = document.querySelector('.overlay');

    if (btnCerrarPanelPiezas) {
        btnCerrarPanelPiezas.addEventListener('click', () => {
            document.body.style.overflow = '';
        });
    }

    if (overlayPanelPiezas) {
        overlayPanelPiezas.addEventListener('click', () => {
            document.body.style.overflow = '';
        });
    }

    // 5. Buscador del panel lateral
    if (buscador) {
        buscador.addEventListener('input', (evento) => {
            const textoBuscado = evento.target.value;
            paginaActual = 1;
            cargarProductos(categoriaActual, textoBuscado, paginaActual, false);
        });
    }
});

// ─── CARGAR PRODUCTOS DESDE API ─────────────────────────────────────────────
async function cargarProductos(categoria, texto, pagina, esCargarMas) {
    const grid = document.getElementById('grid-resultados');
    if (!grid) return;

    try {
        const params = new URLSearchParams({
            tipo: 'HW',
            categoria,
            page: pagina,
            page_size: 10,
        });

        if (texto) {
            params.append('search', texto);
        }

        const respuesta = await fetch(`${API_PRODUCTOS_URL}?${params.toString()}`);
        if (!respuesta.ok) {
            throw new Error(`Error ${respuesta.status}`);
        }

        const data = await respuesta.json();
        const productos = data.results ?? data;
        const hayMasPaginas = !!data.next;

        pintarResultados(productos, esCargarMas, hayMasPaginas);
    } catch (error) {
        console.error('Error en la búsqueda:', error);
        grid.innerHTML = '<p style="text-align: center; color: red; width: 100%; grid-column: span 2;">Error al conectar con la base de datos.</p>';
    }
}

// ─── PINTAR RESULTADOS ───────────────────────────────────────────────────────
function pintarResultados(productos, esCargarMas, hayMasPaginas) {
    const grid = document.getElementById('grid-resultados');
    if (!grid) return;

    if (!esCargarMas) {
        grid.innerHTML = '';
    }

    const btnAntiguo = document.getElementById('btn-ver-mas');
    if (btnAntiguo) btnAntiguo.remove();

    if (!Array.isArray(productos) || productos.length === 0) {
        if (!esCargarMas) {
            grid.innerHTML = '<p style="text-align:center; color:#666; font-size:14px; width:100%; grid-column:1 / -1;">No se encontraron componentes en esta categoría.</p>';
        }
        return;
    }

    productos.forEach(producto => {
        const nombre = producto.nombre || producto.producto_nombre || 'Componente sin nombre';

        let precioNumero = 0;
        let precioInfo = 'Sin ofertas';

        if (Array.isArray(producto.ofertas) && producto.ofertas.length > 0) {
            const ofertaMasBarata = producto.ofertas.reduce((prev, curr) =>
                parseFloat(prev.precio_final) < parseFloat(curr.precio_final) ? prev : curr
            );

            precioNumero = parseFloat(ofertaMasBarata.precio_final) || 0;
            precioInfo = `Desde ${precioNumero.toFixed(2).replace('.', ',')} €`;
        }

        const imagenPorDefecto = MAPA_ICONOS_RANURA[idPanelActual] || '../../assets/images/hardware/placeholder.jpg';
        const imagenProd = producto.imagen_url && producto.imagen_url !== 'null'
            ? producto.imagen_url
            : imagenPorDefecto;

        const card = document.createElement('div');
        card.className = 'component-card';
        card.style.cursor = 'pointer';

        card.innerHTML = `
            <div class="component-thumb">
                <img src="${imagenProd}" alt="${nombre}" style="object-fit: contain; padding: 10px;" loading="lazy">
            </div>
            <p>${nombre}</p>
            <span style="font-size: 11px; color: #2ecc71; font-weight: bold;">${precioInfo}</span>
        `;

        card.addEventListener('click', async () => {
            seleccionarComponente(producto.id, nombre, imagenProd, precioInfo);

            if (precioNumero > 0) {
                await añadirAlCarritoHW(idPanelActual, { ...producto, nombre }, precioNumero, imagenProd);
                gestionarExclusionRefrigeracion();
            }
        });

        grid.appendChild(card);
    });

    if (hayMasPaginas) {
        const btnVerMas = document.createElement('button');
        btnVerMas.id = 'btn-ver-mas';
        btnVerMas.innerText = 'Cargar más resultados...';
        btnVerMas.style.cssText = 'grid-column: 1 / -1; padding: 12px; background: #9814f1; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; margin-top: 10px; margin-bottom: 20px;';

        btnVerMas.onclick = () => {
            paginaActual++;
            const textoBuscador = document.getElementById('buscador-hardware')?.value || '';
            btnVerMas.innerText = 'Cargando...';
            btnVerMas.disabled = true;
            cargarProductos(categoriaActual, textoBuscador, paginaActual, true);
        };

        grid.appendChild(btnVerMas);
    }
}

// ─── SELECCIÓN VISUAL DEL COMPONENTE ─────────────────────────────────────────
function seleccionarComponente(id, nombre, imagen, precioInfo) {
    const radioClose = document.getElementById('panel-close');
    if (radioClose) {
        radioClose.checked = true;
        document.body.style.overflow = '';
    }

    const labelDestino = document.querySelector(`label[for="${idPanelActual}"]`);
    if (!labelDestino) return;

    const seccionItem = labelDestino.closest('.hw-item');
    const imgDestino = seccionItem?.querySelector('.hw-icon');

    if (imgDestino) {
        imgDestino.src = imagen;
        imgDestino.removeAttribute('style');
        imgDestino.style.objectFit = 'contain';
    }

    labelDestino.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; height: 100%;">
            <p class="hw-kicker" style="font-weight: bold; margin: 0; font-size: 18px; flex: 1;">
                ${nombre}
            </p>

            <span style="font-size: 16px; font-weight: bold; flex: 1; text-align: center;">
                ${precioInfo.replace('.', ',')}
            </span>

            <div style="flex: 1; text-align: right;">
                <a class="hw-btn" href="../prices/prices.html?id=${id}"
                   style="display: inline-block; font-size: 14px; font-weight: 600; background: #9814f1; color: white; text-decoration: none; border: 1px solid #9814f1; padding: 6px 14px; border-radius: 4px; transition: all 0.2s ease;">
                    Ver Precios ➔
                </a>
            </div>
        </div>
    `;

    const btn = labelDestino.querySelector('.hw-btn');
    if (btn) {
        btn.addEventListener('mouseenter', () => {
            btn.style.background = 'transparent';
            btn.style.color = '#9814f1';
        });

        btn.addEventListener('mouseleave', () => {
            btn.style.background = '#9814f1';
            btn.style.color = 'white';
        });
    }
}

// ─── RESTAURAR SELECCIONES AL CARGAR ─────────────────────────────────────────
function restaurarSeleccionesHardware(carrito = null) {
    const carritoActual = carrito || getCarritoHW();

    for (const ranura in carritoActual) {
        const item = carritoActual[ranura];
        const labelDestino = document.querySelector(`label[for="${ranura}"]`);
        if (!labelDestino) continue;

        const seccionItem = labelDestino.closest('.hw-item');
        const imgDestino = seccionItem?.querySelector('.hw-icon');

        if (imgDestino && item.imagen) {
            imgDestino.src = item.imagen;
            imgDestino.removeAttribute('style');
            imgDestino.style.objectFit = 'contain';
        }

        labelDestino.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; height: 100%;">
                <p class="hw-kicker" style="font-weight: bold; margin: 0; font-size: 18px; flex: 1;">
                    ${item.nombre}
                </p>

                <span style="font-size: 16px; font-weight: bold; flex: 1; text-align: center;">
                    ${(parseFloat(item.precio) || 0).toFixed(2).replace('.', ',')} €
                </span>

                <div style="flex: 1; text-align: right;">
                    <a class="hw-btn" href="../prices/prices.html?id=${item.id}"
                       style="display: inline-block; font-size: 14px; font-weight: 600; background: #9814f1; color: white; text-decoration: none; border: 1px solid #9814f1; padding: 6px 14px; border-radius: 4px; transition: all 0.2s ease;">
                        Ver Precios ➔
                    </a>
                </div>
            </div>
        `;

        const btn = labelDestino.querySelector('.hw-btn');
        if (btn) {
            btn.addEventListener('mouseenter', () => {
                btn.style.background = 'transparent';
                btn.style.color = '#9814f1';
            });

            btn.addEventListener('mouseleave', () => {
                btn.style.background = '#9814f1';
                btn.style.color = 'white';
            });
        }
    }
}

// ─── EXCLUSIÓN AIRE VS LÍQUIDA ───────────────────────────────────────────────
function gestionarExclusionRefrigeracion() {
    const carritoActual = getCarritoHW();

    const labelAire = document.querySelector('label[for="panel-aire"]');
    const labelLiquida = document.querySelector('label[for="panel-liquida"]');

    const inputAire = document.getElementById('panel-aire');
    const inputLiquida = document.getElementById('panel-liquida');

    if (!labelAire || !labelLiquida) return;

    const sectionAire = labelAire.closest('.hw-item');
    const sectionLiquida = labelLiquida.closest('.hw-item');

    const tieneAire = carritoActual['panel-aire'] !== undefined;
    const tieneLiquida = carritoActual['panel-liquida'] !== undefined;

    if (tieneAire) {
        sectionLiquida.style.opacity = '0.4';
        sectionLiquida.style.pointerEvents = 'none';
        sectionLiquida.style.filter = 'grayscale(100%)';
        if (inputLiquida) inputLiquida.disabled = true;
    } else {
        sectionLiquida.style.opacity = '1';
        sectionLiquida.style.pointerEvents = 'auto';
        sectionLiquida.style.filter = 'none';
        if (inputLiquida) inputLiquida.disabled = false;
    }

    if (tieneLiquida) {
        sectionAire.style.opacity = '0.4';
        sectionAire.style.pointerEvents = 'none';
        sectionAire.style.filter = 'grayscale(100%)';
        if (inputAire) inputAire.disabled = true;
    } else {
        sectionAire.style.opacity = '1';
        sectionAire.style.pointerEvents = 'auto';
        sectionAire.style.filter = 'none';
        if (inputAire) inputAire.disabled = false;
    }
}