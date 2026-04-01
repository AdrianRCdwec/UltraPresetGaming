const API_URL = 'http://127.0.0.1:8000/api/productos/';
let categoriaActual = '';
let paginaActual = 1;
let idPanelActual = '';

// ─── ESTADO DEL CARRITO ──────────────────────────────────────────────────────
// Objeto en vez de array para que al elegir otro componente de la misma categoría, se sustituya.
let carritoHardware = {};

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
                'panel-aire': 'COOL',
                'panel-liquida': 'COOL',
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


// ─── LÓGICA DEL CARRITO (AÑADIR Y UI) ────────────────────────────────────────
function añadirAlCarrito(categoriaRanura, productoData, precioNumero, imagenProd) {
    carritoHardware[categoriaRanura] = {
        id: productoData.id, 
        nombre: productoData.nombre, 
        precio: precioNumero,
        imagen: imagenProd,
        ranura: categoriaRanura
    };
    
    actualizarCarritoUI();
    parpadearCarrito();
}

window.eliminarDelCarrito = function(categoriaRanura) {
    delete carritoHardware[categoriaRanura];
    actualizarCarritoUI();
};

function parpadearCarrito() {
    const btn = document.getElementById('btn-carrito-flotante');
    if (!btn) return;
    btn.classList.add('carrito-parpadeando');
    setTimeout(() => btn.classList.remove('carrito-parpadeando'), 800);
}

function actualizarCarritoUI() {
    const contenedor = document.getElementById('carrito-items');
    const badge      = document.getElementById('carrito-badge');
    const totalDiv   = document.getElementById('carrito-total');

    if (!contenedor || !badge || !totalDiv) return;

    const itemsCarrito = Object.values(carritoHardware);
    badge.textContent = itemsCarrito.length;

    if (itemsCarrito.length === 0) {
        contenedor.innerHTML = '<p class="carrito-vacio">Tu PC está vacío</p>';
        totalDiv.textContent = '0,00 €';
        return;
    }

    let sumaTotal = 0;
    
    contenedor.innerHTML = itemsCarrito.map(item => {
        sumaTotal += item.precio;

        let nombreRanura = "Componente";
        if(item.ranura === 'panel-procesador') nombreRanura = "Procesador";
        if(item.ranura === 'panel-placa') nombreRanura = "Placa Base";
        if(item.ranura === 'panel-ram') nombreRanura = "Memoria RAM";
        if(item.ranura === 'panel-caja') nombreRanura = "Caja/Torre";
        if(item.ranura === 'panel-aire') nombreRanura = "Refrig. Aire";
        if(item.ranura === 'panel-liquida') nombreRanura = "Refrig. Líquida";
        if(item.ranura === 'panel-gpu') nombreRanura = "Tarjeta Gráfica";
        if(item.ranura === 'panel-psu') nombreRanura = "Fuente de Alimentación";
        if(item.ranura === 'panel-disco') nombreRanura = "Disco Duro";
        if(item.ranura === 'panel-monitor') nombreRanura = "Monitor";

        return `
            <div class="carrito-item" style="display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; background: #f7f7f7; margin-bottom: 10px;">
                <img src="${item.imagen}" alt="${item.nombre}" style="width: 54px; height: 54px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">
                <div class="carrito-item-info" style="flex: 1; min-width: 0;">
                    <span style="font-size: 10px; color: #888; text-transform: uppercase; font-weight: 800; display: block;">${nombreRanura}</span>
                    <p class="carrito-item-nombre" style="font-size: 13px; font-weight: 700; margin: 0 0 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.nombre}</p>
                    <p class="carrito-item-precio" style="font-size: 14px; font-weight: 800; color: #6a2fd8; margin: 0;">${item.precio.toFixed(2)} €</p>
                </div>
                <button class="btn-eliminar" onclick="window.eliminarDelCarrito('${item.ranura}')" style="background: none; border: none; font-size: 16px; cursor: pointer; color: #bbb; padding: 4px; border-radius: 4px;">✕</button>
            </div>
        `;
    }).join('');

    totalDiv.textContent = `${sumaTotal.toFixed(2)} €`;
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

        const imagenProd = producto.imagen || producto.imagen_url || '../images/procesador.png';

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