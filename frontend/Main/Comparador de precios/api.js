const API_URL = 'http://127.0.0.1:8000/api/productos/';

document.addEventListener('DOMContentLoaded', () => {
    cargarProductos();
});

async function cargarProductos() {
    try {
        const respuesta = await fetch(API_URL);
        const data = await respuesta.json();
        
        // Manejar si Django devuelve paginación ({count, next, previous, results: [...]}) o el array directo
        const productos = data.results ? data.results : data;
        
        if (productos.length > 0) {
            pintarProductosEnHTML(productos[0]);
        }
    } catch (error) {
        console.error('Error al conectar con la API:', error);
    }
}

function pintarProductosEnHTML(producto) {
    const contenedor = document.getElementById('lista-productos'); 
    const labelNombre = document.getElementById('nombre-producto-api');
    
    if (!contenedor || !labelNombre) return; 

    labelNombre.textContent = producto.nombre;
    contenedor.innerHTML = ''; 

    if (producto.ofertas && producto.ofertas.length > 0) {
        // Limpiamos primero por si acaso
        contenedor.innerHTML = '';
        
        producto.ofertas.forEach((oferta, index) => {
            let imagenTienda = '../images/pcg.jpg'; 
            if(oferta.tienda_nombre.toLowerCase().includes('amazon')) {
                imagenTienda = '../images/amazon.jpg';
            }

            // Creamos el input radio
            const input = document.createElement('input');
            input.className = 'offer-radio';
            input.type = 'radio';
            input.name = 'cpu-store';
            input.id = `tienda-${index}`;

            // Creamos el label visual
            const label = document.createElement('label');
            label.className = 'offer';
            label.htmlFor = `tienda-${index}`;
            label.title = oferta.tienda_nombre;
            
            // Contenido HTML interno del label
            label.innerHTML = `
                <img class="offer-logo" src="${imagenTienda}" alt="${oferta.tienda_nombre}">
                <span class="offer-price">${oferta.precio_final} €</span>
            `;

            // Event Listener seguro (sustituye al onclick con JSON.stringify)
            label.addEventListener('click', () => {
                actualizarCheckout(producto, oferta);
            });

            // Añadimos al contenedor
            contenedor.appendChild(input);
            contenedor.appendChild(label);
        });
        
        // Seleccionamos visualmente la primera oferta y actualizamos el checkout
        setTimeout(() => {
            const primerInput = document.getElementById('tienda-0');
            if(primerInput) primerInput.checked = true;
            actualizarCheckout(producto, producto.ofertas[0]);
        }, 100);

    } else {
        contenedor.innerHTML = '<p style="color: #666; margin-top: 10px;">No hay ofertas disponibles.</p>';
    }
}

// Función que rellena el carrito inferior
function actualizarCheckout(producto, oferta) {
    const checkoutName = document.getElementById('checkout-name');
    const checkoutPrice = document.getElementById('checkout-price');
    const checkoutBase = document.getElementById('checkout-base');
    const checkoutAhorro = document.getElementById('checkout-ahorro');
    const checkoutTotal = document.getElementById('checkout-total-final');
    const btnComprar = document.getElementById('btn-comprar');
    const checkoutSub = document.getElementById('checkout-sub');

    if (checkoutName) checkoutName.textContent = producto.nombre;
    if (checkoutPrice) checkoutPrice.textContent = `${oferta.precio_final} €`;
    if (checkoutBase) checkoutBase.textContent = `${oferta.precio_base} €`;
    
    // Calculamos el ahorro (Precio Base - Precio Final)
    const base = parseFloat(oferta.precio_base);
    const final = parseFloat(oferta.precio_final);
    const ahorro = (base - final).toFixed(2);
    
    if (checkoutAhorro) {
        checkoutAhorro.textContent = ahorro > 0 ? `- ${ahorro} €` : `0,00 €`;
    }
    
    if (checkoutTotal) checkoutTotal.textContent = `TOTAL: ${oferta.precio_final} €`;
    
    // Enlace real al botón azul
    if (btnComprar) btnComprar.href = oferta.enlace_compra || '#';
    
    // Mostrar si tiene envío
    if (checkoutSub) {
        const envio = parseFloat(oferta.gastos_envio);
        if (envio > 0) {
            checkoutSub.textContent = `+ ${envio.toFixed(2)}€ Envío`;
        } else {
            checkoutSub.textContent = 'Envío Gratis';
        }
    }
}