// =============================================================================
// carrito.js — Módulo centralizado de carrito para UltraPresetGaming
// Ubicación sugerida: shared/js/carrito.js
// =============================================================================

import { API_CONFIGURACION_URL, API_PRODUCTOS_URL } from '../../shared/js/api-config.js';

// ─── MAPAS DE CATEGORÍAS (fuente única de verdad) ────────────────────────────
export const MAPA_NOMBRES_RANURA = {
    'panel-procesador': 'Procesador',
    'panel-placa':      'Placa Base',
    'panel-ram':        'Memoria RAM',
    'panel-caja':       'Caja/Torre',
    'panel-aire':       'Refrigeración por aire',
    'panel-liquida':    'Refrigeración Líquida',
    'panel-gpu':        'Tarjeta Gráfica',
    'panel-psu':        'Fuente de alimentación',
    'panel-disco':      'Disco Duro',
    'panel-monitor':    'Monitor',
};

export const MAPA_ICONOS_RANURA = {
    'panel-procesador': '../../assets/images/hardware/cpu.png',
    'panel-placa':      '../../assets/images/hardware/motherboard.png',
    'panel-ram':        '../../assets/images/hardware/ram.png',
    'panel-caja':       '../../assets/images/hardware/box.png',
    'panel-aire':       '../../assets/images/hardware/air.png',
    'panel-liquida':    '../../assets/images/hardware/liquid.png',
    'panel-gpu':        '../../assets/images/hardware/gpu.png',
    'panel-psu':        '../../assets/images/hardware/psu.png',
    'panel-disco':      '../../assets/images/hardware/storage.png',
    'panel-monitor':    '../../assets/images/hardware/monitor.png',
};

// ─── TOKEN ───────────────────────────────────────────────────────────────────
/**
 * Obtiene el token JWT del usuario buscando primero en sessionStorage
 * (sesión temporal) y luego en localStorage (sesión persistente).
 * @returns {string|null}
 */
export function obtenerToken() {
    return sessionStorage.getItem('access') || localStorage.getItem('access');
}

// ─── ESTADO INTERNO DEL CARRITO ──────────────────────────────────────────────
// Fuente de verdad en memoria durante la sesión.
// Se sincroniza con localStorage y con el servidor Django.
let carritoHW = JSON.parse(localStorage.getItem('carrito_hardware'))    || {};
let carritoVG = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];

// ─── PERSISTENCIA LOCAL ──────────────────────────────────────────────────────
export function guardarCarritoHW() {
    localStorage.setItem('carrito_hardware', JSON.stringify(carritoHW));
}

export function guardarCarritoVG() {
    localStorage.setItem('carrito_videojuegos', JSON.stringify(carritoVG));
}

// ─── GETTERS ─────────────────────────────────────────────────────────────────
export function getCarritoHW() { return carritoHW; }
export function getCarritoVG() { return carritoVG; }

// ─── SINCRONIZACIÓN DEL CARRITO TRAS LOGIN ───────────────────────────────────
export async function sincronizarCarritoTrasLogin() {
    const token = obtenerToken();
    if (!token) return;

    const carritoHWLocal = JSON.parse(localStorage.getItem('carrito_hardware')) || {};
    const carritoVGLocal = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];

    try {
        const respuesta = await fetch(API_CONFIGURACION_URL, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });

        if (!respuesta.ok) {
            console.error('No se pudo comprobar el carrito del servidor.');
            return;
        }

        const data = await respuesta.json();
        const itemsServidor = Array.isArray(data) ? data : (data.results ?? []);

        const itemsHWServidor = itemsServidor.filter(item => !item.ranura?.startsWith('videojuego_'));
        const itemsVGServidor = itemsServidor.filter(item => item.ranura?.startsWith('videojuego_'));

        const servidorHWVacio = itemsHWServidor.length === 0;
        const ranurasVGServidor = new Set(itemsVGServidor.map(item => item.ranura));

        // ─── HARDWARE: solo subir local si el servidor no tiene hardware ───
        if (servidorHWVacio) {
            for (const item of Object.values(carritoHWLocal)) {
                if (!item?.id || !item?.ranura) continue;

                const resp = await fetch(API_CONFIGURACION_URL, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        producto: item.id,
                        ranura: item.ranura,
                    }),
                });

                if (!resp.ok) {
                    console.error(`Error subiendo hardware local (${item.ranura}):`, resp.status);
                }
            }
        }

        // ─── VIDEOJUEGOS: fusionar local con servidor evitando duplicados ───
        for (const juego of carritoVGLocal) {
            if (!juego?.id) continue;

            const ranuraVG = `videojuego_${juego.id}`;
            if (ranurasVGServidor.has(ranuraVG)) continue;

            const resp = await fetch(API_CONFIGURACION_URL, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    producto: juego.id,
                    ranura: ranuraVG,
                }),
            });

            if (resp.ok) {
                ranurasVGServidor.add(ranuraVG);
            } else {
                console.error(`Error fusionando videojuego local (${juego.id}):`, resp.status);
            }
        }

        await cargarCarritoHWDesdeServidor();
        await cargarCarritoVGDesdeServidor();

    } catch (error) {
        console.error('Error sincronizando carrito tras login:', error);
    }
}

// ─── SINCRONIZACIÓN CON EL SERVIDOR: HARDWARE ────────────────────────────────
/**
 * Carga la configuración de hardware guardada en la DB del usuario.
 * Para cada item obtiene el detalle del producto y calcula el precio mínimo.
 * @param {Function} [onSuccess] - Callback(carritoSincronizado) llamado al terminar
 */
export async function cargarCarritoHWDesdeServidor(onSuccess) {
    const token = obtenerToken();
    if (!token) return;

    try {
        const respuesta = await fetch(API_CONFIGURACION_URL, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });

        if (!respuesta.ok) {
            console.error('Error al cargar carrito HW del servidor:', respuesta.status);
            return;
        }

        const itemsGuardados = await respuesta.json();
        const itemsHW = itemsGuardados.filter(item => !item.ranura.startsWith('videojuego_'));

        if (!Array.isArray(itemsHW) || itemsHW.length === 0) return;

        const nuevoCarrito = {};

        for (const item of itemsHW) {
            let precioNumero = 0;
            let imagenProd   = item.producto_imagen;

            try {
                const respProd = await fetch(`${API_PRODUCTOS_URL}${item.producto}/`);
                if (respProd.ok) {
                    const prodData = await respProd.json();
                    if (prodData.ofertas && prodData.ofertas.length > 0) {
                        const masBarata = prodData.ofertas.reduce((prev, curr) =>
                            parseFloat(prev.precio_final) < parseFloat(curr.precio_final) ? prev : curr
                        );
                        precioNumero = parseFloat(masBarata.precio_final);
                    }
                    if (prodData.imagen_url) imagenProd = prodData.imagen_url;
                }
            } catch (e) {
                console.error('Error obteniendo datos del producto', item.producto, e);
            }

            nuevoCarrito[item.ranura] = {
                db_id:  item.id,
                id:     item.producto,
                nombre: item.producto_nombre,
                precio: precioNumero,
                imagen: imagenProd,
                ranura: item.ranura,
            };
        }

        carritoHW = nuevoCarrito;
        guardarCarritoHW();
        actualizarCarritoUI();

        if (typeof onSuccess === 'function') onSuccess(carritoHW);

    } catch (error) {
        console.error('Error cargando carrito HW del servidor:', error);
    }
}

// ─── SINCRONIZACIÓN CON EL SERVIDOR: VIDEOJUEGOS ─────────────────────────────
/**
 * Carga los videojuegos guardados en la DB del usuario.
 * @param {Function} [onSuccess] - Callback(juegosGuardados) llamado al terminar
 */
export async function cargarCarritoVGDesdeServidor(onSuccess) {
    const token = obtenerToken();

    if (!token) {
        actualizarCarritoUI();
        if (onSuccess) onSuccess(getCarritoVG());
        return;
    }

    try {
        const respuesta = await fetch(API_CONFIGURACION_URL, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (respuesta.ok) {
            const data = await respuesta.json();
            const items = (data.results ?? data).filter(item => item.ranura?.startsWith('videojuego_'));

            const carritoServidor = items.map(item => ({
                db_id: item.id,
                id: item.producto,
                nombre: item.producto_nombre,
                imagen: item.producto_imagen,
                ofertas: item.producto_ofertas || [],
                precio: item.producto_precio_minimo || 0
            }));

            localStorage.setItem('carrito_videojuegos', JSON.stringify(carritoServidor));
        }
    } catch (error) {
        console.error('Error cargando carrito VG desde servidor:', error);
    } finally {
        actualizarCarritoUI();
        if (onSuccess) onSuccess(getCarritoVG());
    }
}

// ─── AÑADIR AL CARRITO: HARDWARE ─────────────────────────────────────────────
/**
 * Añade o actualiza un componente de hardware en la ranura indicada.
 * Si el usuario está logueado hace POST o PATCH según exista ya en DB.
 * Si no está logueado, guarda solo en localStorage.
 *
 * @param {string} categoriaRanura  - Ej: 'panel-procesador'
 * @param {Object} productoData     - Objeto con {id, nombre, ...}
 * @param {number} precioNumero     - Precio final numérico
 * @param {string} imagenProd       - URL de la imagen del producto
 */
export async function añadirAlCarritoHW(categoriaRanura, productoData, precioNumero, imagenProd) {
    const token      = obtenerToken();
    const itemPrevio = carritoHW[categoriaRanura];
    const payload    = { producto: productoData.id, ranura: categoriaRanura };

    if (token) {
        try {
            const esPatch = !!(itemPrevio && itemPrevio.db_id);
            const method  = esPatch ? 'PATCH' : 'POST';
            const url     = esPatch
                ? `${API_CONFIGURACION_URL}${itemPrevio.db_id}/`
                : API_CONFIGURACION_URL;

            const respuesta = await fetch(url, {
                method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (respuesta.ok) {
                const data = await respuesta.json();
                carritoHW[categoriaRanura] = {
                    db_id:  data.id,
                    id:     productoData.id,
                    nombre: productoData.nombre,
                    precio: precioNumero,
                    imagen: imagenProd,
                    ranura: categoriaRanura,
                };
            } else {
                console.error(`Error guardando en DB con ${method}. Código: ${respuesta.status}`);
                // Fallback: si el PATCH falla, intenta POST
                if (esPatch) {
                    const fb = await fetch(API_CONFIGURACION_URL, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(payload),
                    });
                    if (fb.ok) {
                        const fbData = await fb.json();
                        carritoHW[categoriaRanura] = {
                            db_id:  fbData.id,
                            id:     productoData.id,
                            nombre: productoData.nombre,
                            precio: precioNumero,
                            imagen: imagenProd,
                            ranura: categoriaRanura,
                        };
                    }
                }
            }
        } catch (error) {
            console.error('Error de conexión al añadir HW al carrito:', error);
        }
    } else {
        // Sin sesión: solo localStorage
        carritoHW[categoriaRanura] = {
            id:     productoData.id,
            nombre: productoData.nombre,
            precio: precioNumero,
            imagen: imagenProd,
            ranura: categoriaRanura,
        };
    }

    guardarCarritoHW();
    actualizarCarritoUI();
    parpadearCarrito();
}

// ─── ELIMINAR DEL CARRITO: HARDWARE ──────────────────────────────────────────
/**
 * Elimina un componente de hardware de la ranura indicada.
 * Si está logueado envía DELETE al servidor.
 * @param {string}   categoriaRanura
 * @param {Function} [onEliminar] - Callback(ranura) para restaurar la UI del configurador
 */
export async function eliminarDelCarritoHW(categoriaRanura, onEliminar) {
    const token         = obtenerToken();
    const itemAEliminar = carritoHW[categoriaRanura];

    if (token && itemAEliminar && itemAEliminar.db_id) {
        try {
            const respuesta = await fetch(`${API_CONFIGURACION_URL}${itemAEliminar.db_id}/`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            if (respuesta.ok) {
                console.log(`Eliminado de DB (DELETE) con ID: ${itemAEliminar.db_id}`);
            } else {
                console.error('Error al borrar el elemento en el servidor.');
            }
        } catch (error) {
            console.error('Error de red al intentar eliminar:', error);
        }
    }

    delete carritoHW[categoriaRanura];
    guardarCarritoHW();
    actualizarCarritoUI();

    if (typeof onEliminar === 'function') onEliminar(categoriaRanura);
}

// ─── AÑADIR AL CARRITO: VIDEOJUEGOS ──────────────────────────────────────────
/**
 * Añade un videojuego al carrito. Evita duplicados.
 * Si el usuario está logueado hace POST a la API.
 * @param {Object}   juegoData  - Objeto con {id, nombre, imagen_url, ofertas}
 * @param {Function} [onAñadir] - Callback(id) para marcar el botón en la UI
 */
export async function añadirAlCarritoVG(juegoData, onAñadir) {
    const yaExiste = carritoVG.some(item => item.id === juegoData.id);
    if (yaExiste) return;

    const token  = obtenerToken();
    const ranura = `videojuego_${juegoData.id}`;

    const precioMinimo = juegoData.ofertas && juegoData.ofertas.length > 0
        ? parseFloat(juegoData.ofertas.reduce((p, c) =>
            parseFloat(p.precio_final) < parseFloat(c.precio_final) ? p : c
          ).precio_final)
        : 0;

    const nuevoItem = {
        id:      juegoData.id,
        nombre:  juegoData.nombre,
        imagen:  juegoData.imagen_url || juegoData.imagen || '../../assets/images/misc/placeholderItem.jpg',
        ofertas: juegoData.ofertas || [],
        precio:  precioMinimo,
    };

    if (token) {
        try {
            const respuesta = await fetch(API_CONFIGURACION_URL, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ producto: juegoData.id, ranura }),
            });

            if (respuesta.ok) {
                const data = await respuesta.json();
                nuevoItem.db_id = data.id;
            } else {
                console.error('Error guardando videojuego en DB. Código:', respuesta.status);
            }
        } catch (error) {
            console.error('Error de conexión al añadir VG al carrito:', error);
        }
    }

    carritoVG.push(nuevoItem);
    guardarCarritoVG();
    actualizarCarritoUI();
    parpadearCarrito();

    if (typeof onAñadir === 'function') onAñadir(juegoData.id);
}

// ─── ELIMINAR DEL CARRITO: VIDEOJUEGOS ───────────────────────────────────────
/**
 * Elimina un videojuego del carrito por su ID.
 * Si está logueado y el item tiene db_id, envía DELETE al servidor.
 * @param {number} id
 */
export async function eliminarDelCarritoVG(id) {
    const token = obtenerToken();
    const item  = carritoVG.find(i => i.id === id);

    if (token && item && item.db_id) {
        try {
            const respuesta = await fetch(`${API_CONFIGURACION_URL}${item.db_id}/`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            if (respuesta.ok) {
                console.log(`VG eliminado de DB con ID: ${item.db_id}`);
            } else {
                console.error('Error al borrar VG en el servidor.');
            }
        } catch (error) {
            console.error('Error de red al eliminar VG:', error);
        }
    }

    const idx = carritoVG.findIndex(i => i.id === id);
    if (idx !== -1) carritoVG.splice(idx, 1);
    guardarCarritoVG();
    actualizarCarritoUI();
}

// ─── RENDERIZADO DEL PANEL CARRITO ───────────────────────────────────────────
/**
 * Actualiza todo el contenido visual del panel carrito lateral.
 * Lee siempre desde localStorage para garantizar coherencia entre módulos.
 */
export function actualizarCarritoUI() {
    const carritoHardware = JSON.parse(localStorage.getItem('carrito_hardware')) || {};
    const carritoVideojuegos = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];

    const panelCarrito = document.getElementById('carrito-panel');
    const contHW = document.getElementById('carrito-items-hw');
    const contVG = document.getElementById('carrito-items-vg');

    if (!contHW || !contVG || !panelCarrito) return;

    const tabActual = panelCarrito.getAttribute('data-tab') || 'hw';

    const itemsHW = Object.values(carritoHardware);
    const itemsVG = Array.isArray(carritoVideojuegos) ? carritoVideojuegos : [];

    let sumaHW = 0;
    let sumaVG = 0;

    const badgeHW = document.getElementById('badge-hw-tab');
    const badgeVG = document.getElementById('badge-vg-tab');
    const badgeFlotante = document.getElementById('carrito-badge');
    const totalSeccion = document.getElementById('carrito-total-seccion');
    const totalGlobal = document.getElementById('gran-total-header');

    if (badgeHW) badgeHW.textContent = itemsHW.length;
    if (badgeVG) badgeVG.textContent = itemsVG.length;

    // HARDWARE
    if (itemsHW.length === 0) {
        contHW.innerHTML = '<p class="carrito-vacio">Tu PC está vacío</p>';
    } else {
        contHW.innerHTML = itemsHW.map(item => {
            const precio = parseFloat(item.precio) || 0;
            sumaHW += precio;

            const imagenItem = item.imagen || '../../assets/images/hardware/placeholder.jpg';
            const nombreItem = item.nombre || 'Producto de hardware';

            return `
                <div class="carrito-item" style="display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; background: #f7f7f7;">
                    <img src="${imagenItem}" style="width: 54px; height: 54px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">
                    <div style="flex: 1; min-width: 0;">
                        <span style="font-size: 10px; color: #888; text-transform: uppercase; font-weight: 800;">Hardware</span>
                        <p style="font-size: 13px; font-weight: 700; margin: 0 0 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #101828;">${nombreItem}</p>
                        <p style="font-size: 14px; font-weight: 800; color: #6a2fd8; margin: 0;">${precio.toFixed(2).replace('.', ',')} €</p>
                    </div>
                    <button class="btn-eliminar" onclick="window.carritoEliminarHW('${item.ranura}')" style="background: none; border: none; font-size: 16px; cursor: pointer; color: #bbb; padding: 4px;">✕</button>
                </div>
            `;
        }).join('');
    }

    // VIDEOJUEGOS
    if (itemsVG.length === 0) {
        contVG.innerHTML = '<p class="carrito-vacio">Sin juegos</p>';
    } else {
        contVG.innerHTML = itemsVG.map(item => {
            const precio = item.ofertas?.length
                ? (parseFloat(item.ofertas[0].precio_final) || 0)
                : (parseFloat(item.precio) || 0);

            sumaVG += precio;

            const imagenItem = item.imagen || '../../assets/images/misc/placeholderItem.jpg';
            const nombreItem = item.nombre || 'Videojuego';

            return `
                <div class="carrito-item" style="display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; background: #f7f7f7;">
                    <img src="${imagenItem}" style="width: 54px; height: 54px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">
                    <div style="flex: 1; min-width: 0;">
                        <span style="font-size: 10px; color: #888; text-transform: uppercase; font-weight: 800;">Videojuego</span>
                        <p style="font-size: 13px; font-weight: 700; margin: 0 0 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #101828;">${nombreItem}</p>
                        <p style="font-size: 14px; font-weight: 800; color: #6a2fd8; margin: 0;">${precio.toFixed(2).replace('.', ',')} €</p>
                    </div>
                    <button class="btn-eliminar" onclick="window.carritoEliminarVG(${item.id})" style="background: none; border: none; font-size: 16px; cursor: pointer; color: #bbb; padding: 4px;">✕</button>
                </div>
            `;
        }).join('');
    }

    const subtotalPestaña = tabActual === 'vg' ? sumaVG : sumaHW;
    const totalGeneral = sumaHW + sumaVG;
    const totalItems = itemsHW.length + itemsVG.length;

    if (totalSeccion) {
        totalSeccion.textContent = `${subtotalPestaña.toFixed(2).replace('.', ',')} €`;
    }

    if (totalGlobal) {
        totalGlobal.textContent = `${totalGeneral.toFixed(2).replace('.', ',')} €`;
    }

    if (badgeFlotante) {
        badgeFlotante.textContent = totalItems;
        badgeFlotante.style.display = totalItems > 0 ? 'inline-flex' : 'none';
    }
}

// ─── PARPADEO DEL BOTÓN CARRITO ───────────────────────────────────────────────
export function parpadearCarrito() {
    const btn = document.getElementById('btn-carrito-flotante');
    if (!btn) return;
    btn.classList.add('carrito-parpadeando');
    setTimeout(() => btn.classList.remove('carrito-parpadeando'), 800);
}

// ─── CAMBIO DE TAB ───────────────────────────────────────────────────────────
/**
 * Cambia entre la pestaña de Hardware y Videojuegos en el panel carrito.
 * Expuesto como window.switchTab para uso en HTML inline.
 * @param {'hw'|'vg'} tab
 */
export function switchTab(tab) {
    const panel = document.getElementById('carrito-panel');
    if (!panel) return;
    panel.setAttribute('data-tab', tab);

    const tabHW   = document.getElementById('tab-hw');
    const tabVG   = document.getElementById('tab-vg');
    const itemsHW = document.getElementById('carrito-items-hw');
    const itemsVG = document.getElementById('carrito-items-vg');

    if (tabHW)   tabHW.classList.toggle('active',   tab === 'hw');
    if (tabVG)   tabVG.classList.toggle('active',   tab === 'vg');
    if (itemsHW) itemsHW.style.display = tab === 'hw' ? 'flex' : 'none';
    if (itemsVG) itemsVG.style.display = tab === 'vg' ? 'flex' : 'none';

    actualizarCarritoUI();
}
window.switchTab = switchTab;

// ─── INICIALIZACIÓN DEL PANEL CARRITO ────────────────────────────────────────
/**
 * Registra los listeners de apertura/cierre del panel carrito lateral.
 * Se llama desde hardware.js y videogames.js en su DOMContentLoaded.
 * La tab que se abre al hacer clic en el botón flotante se controla
 * desde cada página mediante el parámetro tabPorDefecto.
 *
 * @param {'hw'|'vg'} tabPorDefecto
 */
export function iniciarPanelCarrito(tabPorDefecto = 'hw') {
    const btnCarrito = document.getElementById('btn-carrito-flotante');
    const btnCerrar = document.getElementById('carrito-cerrar');
    const overlay = document.getElementById('carrito-overlay');
    const tabHW = document.getElementById('tab-hw');
    const tabVG = document.getElementById('tab-vg');
    const panel = document.getElementById('carrito-panel');

    const abrirCarrito = () => {
        actualizarCarritoUI();

        if (panel) panel.classList.add('abierto');
        if (overlay) overlay.classList.add('visible');

        document.body.style.overflow = 'hidden';
        switchTab(tabPorDefecto);
    };

    const cerrarCarrito = () => {
        if (panel) panel.classList.remove('abierto');
        if (overlay) overlay.classList.remove('visible');

        document.body.style.overflow = '';
    };

    actualizarCarritoUI();
    switchTab(tabPorDefecto);

    if (btnCarrito) {
        btnCarrito.onclick = (e) => {
            e.preventDefault();
            abrirCarrito();
        };
    }

    if (btnCerrar) {
        btnCerrar.onclick = cerrarCarrito;
    }

    if (overlay) {
        overlay.onclick = cerrarCarrito;
    }

    if (tabHW) {
        tabHW.onclick = () => switchTab('hw');
    }

    if (tabVG) {
        tabVG.onclick = () => switchTab('vg');
    }

    window.carritoEliminarHW = (ranura) => eliminarDelCarritoHW(ranura, _restaurarPlaceholderHW);
    window.carritoEliminarVG = (id) => eliminarDelCarritoVG(id);
}

// ─── HELPER INTERNO ──────────────────────────────────────────────────────────
/**
 * Restaura el label e icono original de una ranura en la UI del configurador.
 * Solo tiene efecto si el DOM del configurador está en la página actual.
 * @param {string} categoriaRanura
 */
function _restaurarPlaceholderHW(categoriaRanura) {
    const nombreOriginal = MAPA_NOMBRES_RANURA[categoriaRanura];
    const iconoOriginal  = MAPA_ICONOS_RANURA[categoriaRanura];

    const labelDestino = document.querySelector(`label[for="${categoriaRanura}"]`);
    if (labelDestino && nombreOriginal) {
        labelDestino.innerHTML = `<p class="hw-kicker">${nombreOriginal}</p>`;
    }

    if (labelDestino && iconoOriginal) {
        const hwItem     = labelDestino.closest('.hw-item');
        const imgDestino = hwItem ? hwItem.querySelector('.hw-icon') : null;
        if (imgDestino) imgDestino.src = iconoOriginal;
    }
}