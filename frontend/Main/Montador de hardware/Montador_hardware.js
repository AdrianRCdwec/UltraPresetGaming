const API_URL = 'http://127.0.0.1:8000/api/productos/';
let categoriaActual = '';
let paginaActual = 1;

document.addEventListener('DOMContentLoaded', () => {
    const buscador = document.getElementById('buscador-hardware');
    
    // En lugar de escuchar los "radios" ocultos, escuchamos los clics en las tarjetas visuales (labels)
    const tarjetasHardware = document.querySelectorAll('.hw-card');

    tarjetasHardware.forEach(tarjeta => {
        tarjeta.addEventListener('click', (e) => {
            // Leemos a qué panel pertenece esta tarjeta (ej: "panel-procesador")
            const idPanel = tarjeta.getAttribute('for');
            
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
            
            categoriaActual = mapaCategorias[idPanel] || 'NONE';
            paginaActual = 1;
            
            // Forzamos que la barra de búsqueda se vacíe visualmente
            if(buscador) {
                buscador.value = '';
            }
            
            // Ponemos mensaje de carga y llamamos a la base de datos
            document.getElementById('grid-resultados').innerHTML = '<p style="text-align: center; color: #666; width: 100%; grid-column: span 2;">Cargando componentes...</p>';
            
            // Retrasamos la carga 100ms para asegurar que el panel se ha abierto visualmente
            setTimeout(() => {
                cargarProductos(categoriaActual, '', paginaActual, false);
            }, 100);
        });
    });

    // Escuchar la barra de búsqueda para que busque en la categoría abierta
    if(buscador) {
        buscador.addEventListener('input', (evento) => {
            const textoBuscado = evento.target.value;
            paginaActual = 1; 
            cargarProductos(categoriaActual, textoBuscado, paginaActual, false);
        });
    }
});

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
        document.getElementById('grid-resultados').innerHTML = '<p style="text-align: center; color: red; width: 100%; grid-column: span 2;">Error al conectar con la base de datos.</p>';
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
        if (producto.ofertas && producto.ofertas.length > 0) {
            const ofertaMasBarata = producto.ofertas.reduce((prev, curr) => 
                (prev.precio_final < curr.precio_final) ? prev : curr
            );
            precioInfo = `Desde ${ofertaMasBarata.precio_final}€`;
        }

        const htmlCard = `
            <div class="component-card">
                <div class="component-thumb">
                    <img src="../images/procesador.png" alt="${producto.nombre}" style="object-fit: contain; padding: 10px;">
                </div>
                <p>${producto.nombre}</p>
                <span style="font-size: 11px; color: #2ecc71; font-weight: bold;">${precioInfo}</span>
            </div>
        `;
        grid.innerHTML += htmlCard;
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
