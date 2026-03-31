const API_URL = 'http://127.0.0.1:8000/api/productos/';

document.addEventListener('DOMContentLoaded', () => {
    cargarProductos();
});

async function cargarProductos() {
    try {
        const respuesta = await fetch(API_URL);
        const productos = await respuesta.json();
        
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

    if (producto.ofertas.length > 0) {
        let html = '';
        
        producto.ofertas.forEach((oferta, index) => {
            let imagenTienda = '../images/pcg.jpg'; 
            if(oferta.tienda_nombre.toLowerCase().includes('amazon')) {
                imagenTienda = '../images/amazon.jpg';
            }

            // Aquí está la magia: añadimos 'onclick' para que al pulsar, actualice el Checkout
            html += `
                <input class="offer-radio" type="radio" name="cpu-store" id="tienda-${index}">
                <label class="offer" for="tienda-${index}" title="${oferta.tienda_nombre}" 
                       onclick='actualizarCheckout(${JSON.stringify(producto)}, ${JSON.stringify(oferta)})'>
                    <img class="offer-logo" src="${imagenTienda}" alt="${oferta.tienda_nombre}">
                    <span class="offer-price">${oferta.precio_final} €</span>
                </label>
            `;
        });
        
        contenedor.innerHTML = html;
        
        // Hacemos clic automático en la primera oferta para que no salga vacío el checkout
        setTimeout(() => {
            const primerLabel = document.querySelector('label.offer');
            if(primerLabel) primerLabel.click();
        }, 100);

    } else {
        contenedor.innerHTML = '<p>No hay ofertas disponibles.</p>';
    }
}

// Nueva función que rellena el carrito
function actualizarCheckout(producto, oferta) {
    document.getElementById('checkout-name').textContent = producto.nombre;
    document.getElementById('checkout-price').textContent = `${oferta.precio_final} €`;
    document.getElementById('checkout-base').textContent = `${oferta.precio_base} €`;
    
    // Calculamos el ahorro (Precio Base - Precio Final)
    const ahorro = (oferta.precio_base - oferta.precio_final).toFixed(2);
    document.getElementById('checkout-ahorro').textContent = ahorro > 0 ? `- ${ahorro} €` : `0,00 €`;
    
    document.getElementById('checkout-total-final').textContent = `TOTAL: ${oferta.precio_final} €`;
    
    // Le ponemos el enlace real a la tienda al botón azul
    document.getElementById('btn-comprar').href = oferta.enlace_compra;
    
    // Mostramos si tiene envío o si es un mod/juego
    if (oferta.gastos_envio > 0) {
        document.getElementById('checkout-sub').textContent = `+ ${oferta.gastos_envio}€ Envío`;
    } else {
        document.getElementById('checkout-sub').textContent = 'Envío Gratis';
    }
}
