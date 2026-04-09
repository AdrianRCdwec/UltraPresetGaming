const API_URL = 'http://127.0.0.1:8000/api/productos/';
const API_CONFIG_URL = 'http://127.0.0.1:8000/api/configuracion/';

let categoriaActual = '';
let paginaActual = 1;
let idPanelActual = '';

// Función auxiliar para obtener el token
function obtenerToken() {
    return localStorage.getItem('access');
}

// ─── ESTADO DEL CARRITO ──────────────────────────────────────────────────────
// Intentamos cargar el carrito guardado. Si no hay nada, creamos un objeto vacío (usuarios no logueados)
let carritoHardware = JSON.parse(localStorage.getItem('carrito_hardware')) || {};
let carritoVideojuegos = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];

function guardarCarritoHardware() {
    localStorage.setItem('carrito_hardware', JSON.stringify(carritoHardware));
}

// ─── PETICIÓN GET (CARGAR CONFIGURACIÓN DEL SERVIDOR) ────────────────
async function cargarCarritoDesdeServidor() {
    const token = obtenerToken();
    if (!token) {
        console.log("Usuario no autenticado. Usando carrito local.");
        return; 
    }

    try {
        const respuesta = await fetch(API_CONFIG_URL, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (respuesta.ok) {
            const itemsGuardados = await respuesta.json();

            // Si el servidor nos devuelve datos, usamos la DB como fuente de verdad
            if (itemsGuardados.length > 0) {
                carritoHardware = {};
                
                itemsGuardados.forEach(item => {
                    carritoHardware[item.ranura] = {
                        db_id: item.id,
                        id: item.producto, 
                        nombre: item.producto_nombre,
                        precio: 0,
                        imagen: item.producto_imagen,
                        ranura: item.ranura
                    };
                });
                
                guardarCarritoHardware();
                actualizarCarritoUI();
                restaurarSeleccionesHardware();
                gestionarExclusionRefrigeracion();
                console.log("Carrito sincronizado con la DB:", carritoHardware);
            }
        }
    } catch (error) {
        console.error("Error cargando carrito del servidor:", error);
    }
}

// ─── INICIALIZACIÓN GENERAL ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // 1. Lógica del Carrito (Abrir/Cerrar)
    const btnCarrito = document.getElementById('btn-carrito-flotante');
    const panelCarrito = document.getElementById('carrito-panel');
    const overlayCarrito = document.getElementById('carrito-overlay');
    const btnCerrarCarrito = document.getElementById('carrito-cerrar');

    if(btnCarrito) {
        btnCarrito.addEventListener('click', (e) => {
            e.preventDefault();
            if(panelCarrito) panelCarrito.classList.add('abierto'); 
            if(overlayCarrito) overlayCarrito.classList.add('visible'); 
            document.body.style.overflow = 'hidden'; // Bloquea el scroll del fondo
            window.switchTab('hw');
        });
    }

    if(btnCerrarCarrito) {
        btnCerrarCarrito.addEventListener('click', () => {
            if(panelCarrito) panelCarrito.classList.remove('abierto');
            if(overlayCarrito) overlayCarrito.classList.remove('visible');
            document.body.style.overflow = ''; // Recupera el scroll
        });
    }

    if(overlayCarrito) {
        overlayCarrito.addEventListener('click', () => {
            if(panelCarrito) panelCarrito.classList.remove('abierto');
            if(overlayCarrito) overlayCarrito.classList.remove('visible');
            document.body.style.overflow = ''; // Recupera el scroll
        });
    }

    // 2. Lógica de Paneles y Buscador
    const buscador = document.getElementById('buscador-hardware');
    const tarjetasHardware = document.querySelectorAll('.hw-card');

    tarjetasHardware.forEach(tarjeta => {
        tarjeta.addEventListener('click', (e) => {
            // Si hacen clic en el botón de "Ver Precios", no recargamos el panel
            if (e.target.tagName.toLowerCase() === 'a') return;
            
            document.body.style.overflow = 'hidden'; // Bloquea el scroll al abrir panel lateral de piezas
            
            idPanelActual = tarjeta.getAttribute('for');
            
            const mapaCategorias = {
                'panel-procesador': 'CPU',
                'panel-placa': 'MB',
                'panel-ram': 'RAM',
                'panel-caja': 'CASE',
                'panel-aire': 'AIR',
                'panel-liquida': 'LIQ',
                'panel-gpu': 'GPU',
                'panel-psu': 'PSU',
                'panel-disco': 'SSD',
                'panel-monitor': 'MON'
            };
            
            categoriaActual = mapaCategorias[idPanelActual] || 'NONE';
            paginaActual = 1;
            
            if(buscador) buscador.value = '';
            
            const grid = document.getElementById('grid-resultados');
            if (grid) grid.innerHTML = '<p style="text-align: center; color: #666; width: 100%; grid-column: span 2;">Cargando componentes...</p>';
            
            setTimeout(() => {
                cargarProductos(categoriaActual, '', paginaActual, false);
            }, 100);
        });
    });

    // Restaurar scroll al cerrar el panel de piezas (click en X o en overlay)
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

    if(buscador) {
        buscador.addEventListener('input', (evento) => {
            const textoBuscado = evento.target.value;
            paginaActual = 1; 
            cargarProductos(categoriaActual, textoBuscado, paginaActual, false);
        });
    }
});

// ─── LÓGICA DEL CARRITO (AÑADIR Y UI) CON POST/PATCH ────────────────────────────────────────
window.switchTab = function(tab) {
    document.getElementById('carrito-panel').setAttribute('data-tab', tab);
    document.getElementById('tab-hw').classList.toggle('active', tab === 'hw');
    document.getElementById('tab-vg').classList.toggle('active', tab === 'vg');
    document.getElementById('carrito-items-hw').style.display = (tab === 'hw') ? 'flex' : 'none';
    document.getElementById('carrito-items-vg').style.display = (tab === 'vg') ? 'flex' : 'none';
    actualizarCarritoUI();
};

async function añadirAlCarrito(categoriaRanura, productoData, precioNumero, imagenProd) {
    const token = obtenerToken();
    const itemPrevio = carritoHardware[categoriaRanura];

    const payload = {
        producto: productoData.id,
        ranura: categoriaRanura
    };

    if (token) {
        try {
            let url = API_CONFIG_URL;
            let method = 'POST'; // Asumimos que es nuevo

            // Si ya había un item en esta ranura con un db_id, hacemos PATCH (actualizar) en vez de POST
            if (itemPrevio && itemPrevio.db_id) {
                url = `${API_CONFIG_URL}${itemPrevio.db_id}/`;
                method = 'PATCH'; 
            }

            const respuesta = await fetch(url, {
                method: method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (respuesta.ok) {
                const data = await respuesta.json();
                console.log(`Guardado en DB (${method}):`, data);

                // Usamos el ID de la base de datos devuelto por la API
                carritoHardware[categoriaRanura] = { 
                    db_id: data.id, 
                    id: productoData.id, 
                    nombre: productoData.nombre, 
                    precio: precioNumero, 
                    imagen: imagenProd, 
                    ranura: categoriaRanura 
                };
            } else {
                console.error(`Error guardando en el servidor con ${method}. Código: ${respuesta.status}`);
                if (method === 'PATCH') {
                    console.log("Intentando recuperar con POST...");
                    const fallbackRespuesta = await fetch(API_CONFIG_URL, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });
                    
                    if (fallbackRespuesta.ok) {
                        const fallbackData = await fallbackRespuesta.json();
                        carritoHardware[categoriaRanura] = { 
                            db_id: fallbackData.id, 
                            id: productoData.id, 
                            nombre: productoData.nombre, 
                            precio: precioNumero, 
                            imagen: imagenProd, 
                            ranura: categoriaRanura 
                        };
                    }
                }
            }
        } catch (error) {
            console.error("Error de conexión al añadir al carrito:", error);
        }
    } else {
        carritoHardware[categoriaRanura] = { 
            id: productoData.id, 
            nombre: productoData.nombre, 
            precio: precioNumero, 
            imagen: imagenProd, 
            ranura: categoriaRanura 
        };
    }

    guardarCarritoHardware();
    actualizarCarritoUI();
    parpadearCarrito();
    gestionarExclusionRefrigeracion(); 
}


// ─── ELIMINAR DEL CARRITO (Y DE LA DB SI EXISTE) ───────────────────────────
window.eliminarDelCarritoHW = async function(categoriaRanura) {
    const token = obtenerToken();
    const itemAEliminar = carritoHardware[categoriaRanura];

    // Si el item existe y tiene un db_id, enviamos un DELETE al servidor
    if (token && itemAEliminar && itemAEliminar.db_id) {
        try {
            const url = `${API_CONFIG_URL}${itemAEliminar.db_id}/`;
            const respuesta = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (respuesta.ok) {
                console.log(`Eliminado de DB (DELETE) con ID: ${itemAEliminar.db_id}`);
            } else {
                console.error("Error al intentar borrar el elemento en el servidor.");
            }
        } catch (error) {
            console.error("Error de red al intentar eliminar:", error);
        }
    }

    // Borramos localmente en cualquier caso
    delete carritoHardware[categoriaRanura];
    guardarCarritoHardware();
    actualizarCarritoUI();

    // Lógica para devolver el recuadro a su estado original (placeholder)
    const labelDestino = document.querySelector(`label[for="${categoriaRanura}"]`);
    if (labelDestino) {
        let nombreOriginal = '';
        if (categoriaRanura === 'panel-procesador') nombreOriginal = 'Procesador';
        if (categoriaRanura === 'panel-placa') nombreOriginal = 'Placa Base';
        if (categoriaRanura === 'panel-ram') nombreOriginal = 'Memoria RAM';
        if (categoriaRanura === 'panel-caja') nombreOriginal = 'Caja/Torre';
        if (categoriaRanura === 'panel-aire') nombreOriginal = 'Refrigeración por aire';
        if (categoriaRanura === 'panel-liquida') nombreOriginal = 'Refrigeración Líquida';
        if (categoriaRanura === 'panel-gpu') nombreOriginal = 'Tarjeta Gráfica';
        if (categoriaRanura === 'panel-psu') nombreOriginal = 'Fuente de alimentación';
        if (categoriaRanura === 'panel-disco') nombreOriginal = 'Disco Duro';
        if (categoriaRanura === 'panel-monitor') nombreOriginal = 'Monitor';
        
        if (nombreOriginal) {
            labelDestino.innerHTML = `<p class="hw-kicker">${nombreOriginal}</p>`;
        }
        
        // Restauramos el icono original
        const imgDestino = labelDestino.closest('.hw-item').querySelector('.hw-icon');
        if (imgDestino) {
            let imgOriginal = '../images/placeholder.jpg';
            if (categoriaRanura === 'panel-procesador') imgOriginal = '../images/procesador.png';
            if (categoriaRanura === 'panel-placa') imgOriginal = '../images/motherboard.png';
            if (categoriaRanura === 'panel-ram') imgOriginal = '../images/ram.png';
            if (categoriaRanura === 'panel-caja') imgOriginal = '../images/caja.png';
            if (categoriaRanura === 'panel-aire') imgOriginal = '../images/aire.png';
            if (categoriaRanura === 'panel-liquida') imgOriginal = '../images/liquida.png';
            if (categoriaRanura === 'panel-gpu') imgOriginal = '../images/gpu.png';
            if (categoriaRanura === 'panel-psu') imgOriginal = '../images/psu.png';
            if (categoriaRanura === 'panel-disco') imgOriginal = '../images/almacenamiento.png';
            if (categoriaRanura === 'panel-monitor') imgOriginal = '../images/monitor.png';
            
            imgDestino.src = imgOriginal;
        }
    }

    // Comprobamos la exclusión entre aire y líquida tras borrar
    gestionarExclusionRefrigeracion();
};

window.eliminarDelCarritoVG = function(id) {
    const idx = carritoVideojuegos.findIndex(item => item.id === id);
    if (idx !== -1) carritoVideojuegos.splice(idx, 1);
    localStorage.setItem('carrito_videojuegos', JSON.stringify(carritoVideojuegos));
    actualizarCarritoUI();
};

function parpadearCarrito() {
    const btn = document.getElementById('btn-carrito-flotante');
    if (!btn) return;
    btn.classList.add('carrito-parpadeando');
    setTimeout(() => btn.classList.remove('carrito-parpadeando'), 800);
}

function actualizarCarritoUI() {
    // Refrescar memorias
    carritoHardware = JSON.parse(localStorage.getItem('carrito_hardware')) || {};
    carritoVideojuegos = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];

    const tabActual = document.getElementById('carrito-panel').getAttribute('data-tab') || 'hw';
    const contHW = document.getElementById('carrito-items-hw');
    const contVG = document.getElementById('carrito-items-vg');

    if (!contHW || !contVG) return;

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

    // -- VIDEOJUEGOS --
    const arrayJuegos = (typeof carritoVideojuegos !== 'undefined' && carritoVideojuegos.length !== undefined) ? carritoVideojuegos : carritoVideojuegos;
    
    const totalItemsVG = arrayJuegos.length;
    document.getElementById('badge-vg-tab').textContent = totalItemsVG;
    let sumaVG = 0;

    if (arrayJuegos.length === 0) {
        contVG.innerHTML = '<p class="carrito-vacio">Sin juegos</p>';
    } else {
        contVG.innerHTML = arrayJuegos.map(item => {
            const precio = item.ofertas?.length ? parseFloat(item.ofertas[0].precio_final) : 0;
            sumaVG += precio; 
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

    // -- TOTALES Y BADGE GLOBAL --
    document.getElementById('gran-total-header').textContent = (sumaHW + sumaVG).toFixed(2) + ' €';
    document.getElementById('carrito-total-seccion').textContent = (tabActual === 'hw' ? sumaHW : sumaVG).toFixed(2) + ' €';
    
    const badgeFlotante = document.getElementById('carrito-badge');
    if (badgeFlotante) badgeFlotante.textContent = itemsHW.length + totalItemsVG;
}

// ─── LLAMADAS A LA API Y PINTADO ─────────────────────────────────────────────
async function cargarProductos(categoria, texto, pagina, esCargarMas) {
    try {
        let url = `${API_URL}?categoria=${categoria}&page=${pagina}`;
        if (texto.length > 0) url += `&search=${texto}`;

        const respuesta = await fetch(url);
        const data = await respuesta.json(); 
        
        const productos = data.results; 
        const hayMasPaginas = data.next !== null;

        pintarResultados(productos, esCargarMas, hayMasPaginas);
    } catch (error) {
        console.error('Error en la búsqueda:', error);
        const grid = document.getElementById('grid-resultados');
        if(grid) grid.innerHTML = '<p style="text-align: center; color: red; width: 100%; grid-column: span 2;">Error al conectar con la base de datos.</p>';
    }
}

function pintarResultados(productos, esCargarMas, hayMasPaginas) {
    const grid = document.getElementById('grid-resultados');
    if (!grid) return;

    if (!esCargarMas) grid.innerHTML = ''; 
    
    const btnAntiguo = document.getElementById('btn-ver-mas');
    if(btnAntiguo) btnAntiguo.remove();

    if (productos.length === 0 && !esCargarMas) {
        grid.innerHTML = '<p style="text-align: center; color: #666; font-size: 14px; width: 100%; grid-column: span 2;">No se encontraron componentes en esta categoría.</p>';
        return;
    }

    productos.forEach(producto => {
        let precioInfo = 'Sin ofertas';
        let precioNumero = 0; 
        
        if (producto.ofertas && producto.ofertas.length > 0) {
            const ofertaMasBarata = producto.ofertas.reduce((prev, curr) => 
                (parseFloat(prev.precio_final) < parseFloat(curr.precio_final)) ? prev : curr
            );
            precioNumero = parseFloat(ofertaMasBarata.precio_final);
            precioInfo = `Desde ${ofertaMasBarata.precio_final}€`;
        }

        // Elegir imagen por defecto según la categoría
        let imagenPorDefecto = '../images/placeholder.jpg';
        switch (categoriaActual) {
            case 'MB':   imagenPorDefecto = '../images/motherboard.png'; break;
            case 'RAM':  imagenPorDefecto = '../images/ram.png'; break;
            case 'CASE': imagenPorDefecto = '../images/caja.png'; break;
            case 'AIR':  imagenPorDefecto = '../images/aire.png'; break;
            case 'LIQ':  imagenPorDefecto = '../images/liquida.png'; break;
            case 'GPU':  imagenPorDefecto = '../images/gpu.png'; break;
            case 'PSU':  imagenPorDefecto = '../images/psu.png'; break;
            case 'SSD':  imagenPorDefecto = '../images/almacenamiento.png'; break;
            case 'MON':  imagenPorDefecto = '../images/monitor.png'; break;
            case 'CPU':  imagenPorDefecto = '../images/procesador.png'; break;
        }

        const imagenProd = producto.imagen || producto.imagen_url || imagenPorDefecto;

        const card = document.createElement('div');
        card.className = 'component-card';
        card.style.cursor = 'pointer'; 
        card.innerHTML = `
            <div class="component-thumb">
                <img src="${imagenProd}" alt="${producto.nombre}" style="object-fit: contain; padding: 10px;">
            </div>
            <p>${producto.nombre}</p>
            <span style="font-size: 11px; color: #2ecc71; font-weight: bold;">${precioInfo}</span>
        `;

        card.addEventListener('click', () => {
            seleccionarComponente(producto.id, producto.nombre, imagenProd, precioInfo);
            
            if (precioNumero > 0) {
                añadirAlCarrito(idPanelActual, producto, precioNumero, imagenProd);
            }
        });

        grid.appendChild(card);
    });

    if (hayMasPaginas) {
        const btnVerMas = document.createElement('button');
        btnVerMas.id = 'btn-ver-mas';
        btnVerMas.innerText = 'Cargar más resultados...';
        btnVerMas.style.cssText = 'grid-column: span 2; padding: 10px; background: #9814f1; color: white; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; font-weight: bold;';
        
        btnVerMas.onclick = () => {
            paginaActual++;
            const textoBuscador = document.getElementById('buscador-hardware').value;
            cargarProductos(categoriaActual, textoBuscador, paginaActual, true);
            btnVerMas.innerText = 'Cargando...';
        };

        grid.appendChild(btnVerMas);
    }
}

// ─── SELECCIÓN DEL COMPONENTE (VISUAL) ───────────────────────────────────────
function seleccionarComponente(id, nombre, imagen, precioInfo) {
    const radioClose = document.getElementById('panel-close');
    if (radioClose) {
        radioClose.checked = true;
        document.body.style.overflow = ''; // Recupera el scroll al seleccionar componente
    }

    const labelDestino = document.querySelector(`label[for="${idPanelActual}"]`);
    if (!labelDestino) return;

    const seccionItem = labelDestino.closest('.hw-item');
    const imgDestino = seccionItem.querySelector('.hw-icon');
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
                ${precioInfo}
            </span>
            
            <div style="flex: 1; text-align: right;">
                <a class="hw-btn" href="../Comparador de precios/comparador.html?id=${id}" 
                   style="display: inline-block; font-size: 14px; font-weight: 600; background: #9814f1; color: white; text-decoration: none; border: 1px solid #9814f1; padding: 6px 14px; border-radius: 4px; transition: all 0.2s ease;">
                    Ver Precios ➔
                </a>
            </div>
            
        </div>
    `;

    const btn = labelDestino.querySelector('.hw-btn');
    if(btn) {
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
function restaurarSeleccionesHardware() {
    for (const ranura in carritoHardware) {
        const item = carritoHardware[ranura];
        const labelDestino = document.querySelector(`label[for="${ranura}"]`);
        if (!labelDestino) continue;

        // Actualizar la imagen
        const seccionItem = labelDestino.closest('.hw-item');
        const imgDestino = seccionItem.querySelector('.hw-icon');
        if (imgDestino) {
            imgDestino.src = item.imagen;
            imgDestino.removeAttribute('style'); 
            imgDestino.style.objectFit = 'contain';
        }

        // Rellenar el bloque con los datos guardados
        labelDestino.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; height: 100%;">
                
                <p class="hw-kicker" style="font-weight: bold; margin: 0; font-size: 18px; flex: 1;">
                    ${item.nombre}
                </p>
                
                <span style="font-size: 16px; font-weight: bold; flex: 1; text-align: center;">
                    ${item.precio.toFixed(2)} €
                </span>
                
                <div style="flex: 1; text-align: right;">
                    <a class="hw-btn" href="../Comparador de precios/comparador.html?id=${item.id}" 
                       style="display: inline-block; font-size: 14px; font-weight: 600; background: #9814f1; color: white; text-decoration: none; border: 1px solid #9814f1; padding: 6px 14px; border-radius: 4px; transition: all 0.2s ease;">
                       Ver Precios ➔
                    </a>
                </div>
                
            </div>
        `;

        // Eventos del botón
        const btn = labelDestino.querySelector('.hw-btn');
        if(btn) {
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

// ─── LÓGICA DE EXCLUSIÓN: AIRE VS LÍQUIDA ────────────────────────────────────

// Esta función se encarga de oscurecer/bloquear la opción contraria
function gestionarExclusionRefrigeracion() {
    const labelAire = document.querySelector('label[for="panel-aire"]');
    const labelLiquida = document.querySelector('label[for="panel-liquida"]');

    // Recuperamos los input radio reales para deshabilitarlos físicamente
    const inputAire = document.getElementById('panel-aire');
    const inputLiquida = document.getElementById('panel-liquida');

    if (!labelAire || !labelLiquida) return;

    const sectionAire = labelAire.closest('.hw-item');
    const sectionLiquida = labelLiquida.closest('.hw-item');

    // Comprobamos si el usuario ya tiene algo de estas categorías
    const tieneAire = carritoHardware['panel-aire'] !== undefined;
    const tieneLiquida = carritoHardware['panel-liquida'] !== undefined;

    // Si tiene AIRE, bloqueamos LÍQUIDA
    if (tieneAire) {
        sectionLiquida.style.opacity = '0.4';
        sectionLiquida.style.pointerEvents = 'none';
        sectionLiquida.style.filter = 'grayscale(100%)';
        if(inputLiquida) inputLiquida.disabled = true; // Impide que se abra el panel
    } else {
        sectionLiquida.style.opacity = '1';
        sectionLiquida.style.pointerEvents = 'auto';
        sectionLiquida.style.filter = 'none';
        if(inputLiquida) inputLiquida.disabled = false;
    }

    // Si tiene LÍQUIDA, bloqueamos AIRE
    if (tieneLiquida) {
        sectionAire.style.opacity = '0.4';
        sectionAire.style.pointerEvents = 'none';
        sectionAire.style.filter = 'grayscale(100%)';
        if(inputAire) inputAire.disabled = true; // Impide que se abra el panel
    } else {
        sectionAire.style.opacity = '1';
        sectionAire.style.pointerEvents = 'auto';
        sectionAire.style.filter = 'none';
        if(inputAire) inputAire.disabled = false;
    }
}

// ─── AL CARGAR LA PÁGINA ─────────────────────────────────────────────────────
window.addEventListener('load', () => {
    actualizarCarritoUI();
    restaurarSeleccionesHardware(); 
    gestionarExclusionRefrigeracion();
    cargarCarritoDesdeServidor();
});