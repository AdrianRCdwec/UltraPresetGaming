const API_CONFIGURACION_URL = 'http://127.0.0.1:8000/api/configuracion/';
const API_PRODUCTOS_URL = 'http://127.0.0.1:8000/api/productos/';
const PLACEHOLDER_SHOP_LOGO = '../../assets/images/misc/placeholderShop.jpg';
const seleccionesCheckout = {}; // clave: productId → { producto, oferta }

document.addEventListener('DOMContentLoaded', () => {
    cargarProductosDelCarrito();
});

async function cargarProductosDelCarrito() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const loadingMessage = document.getElementById('loading-message');
    const emptyCartMessage = document.getElementById('empty-cart-message');

    // Mostrar mensaje de carga y ocultar el de vacío
    if (loadingMessage) loadingMessage.style.display = 'block';
    if (emptyCartMessage) emptyCartMessage.style.display = 'none';
    if (cartItemsContainer) cartItemsContainer.innerHTML = ''; // Limpiar cualquier contenido previo

    const token = obtenerToken();

    // CASO 1: Sin token → tirar del carrito local
    if (!token) {
        console.log('Sin token, cargando carrito desde localStorage...');
        await cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage);
        return;
    }

    // CASO 2: Con token → intentar servidor, y si falla, fallback a local
    try {
        const configResponse = await fetch(API_CONFIGURACION_URL, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!configResponse.ok) {
            throw new Error(`Error al obtener la configuración del carrito: ${configResponse.statusText}`);
        }

        const configData = await configResponse.json();
        const cartItems = configData.results ? configData.results : configData; // Manejar paginación o array directo

        if (cartItems.length === 0) {
            // Si el servidor no tiene nada, probamos a mostrar el carrito local (por si hay desincronización)
            await cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage);
            return;
        }

        // Ocultar mensaje de vacío si hay productos
        if (emptyCartMessage) emptyCartMessage.style.display = 'none';

        // Llamada 2 (por cada producto): Obtener detalles y ofertas
        for (const cartItem of cartItems) {
            const productResponse = await fetch(`${API_PRODUCTOS_URL}${cartItem.producto}/`);

            if (!productResponse.ok) {
                console.error(`Error al obtener detalles del producto ${cartItem.producto}: ${productResponse.statusText}`);
                continue;
            }

            const productData = await productResponse.json();
            renderCartItem(cartItem, productData);
        }

    } catch (error) {
        console.error('Error al cargar productos del carrito desde servidor:', error);
        // Fallback a carrito local
        await cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage);
    } finally {
        if (loadingMessage) loadingMessage.style.display = 'none';
    }
}

async function cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage) {
    const raw = localStorage.getItem('carrito_hardware');
    const carritoLocal = raw ? JSON.parse(raw) : {};
    const items = Object.values(carritoLocal);

    if (!items.length) {
        if (loadingMessage) loadingMessage.style.display = 'none';
        if (emptyCartMessage) emptyCartMessage.style.display = 'block';
        return;
    }

    if (emptyCartMessage) emptyCartMessage.style.display = 'none';

    for (const item of items) {
        try {
            const productResponse = await fetch(`${API_PRODUCTOS_URL}${item.id}/`);
            if (!productResponse.ok) {
                console.error(`Error al obtener detalles del producto ${item.id}: ${productResponse.statusText}`);
                continue;
            }
            const productData = await productResponse.json();
            renderCartItem(item, productData);
        } catch (error) {
            console.error('Error al obtener producto desde localStorage:', error);
        }
    }

    if (loadingMessage) loadingMessage.style.display = 'none';
}

function renderCartItem(cartItem, productData) {
    const cartItemsContainer = document.getElementById('cart-items-container');
    if (!cartItemsContainer) return;

    // Normalizar campos para que funcione tanto con items de la API como con los de localStorage
    const productId = cartItem.producto || cartItem.id;
    const productName = cartItem.producto_nombre || cartItem.nombre;
    const productImage = cartItem.producto_imagen || cartItem.imagen;

    // Cada producto será un <section class="hw-item">
    const productSection = document.createElement('section');
    productSection.className = 'hw-item';
    productSection.id = `product-${productId}`;

    // ===== Lado izquierdo: .hw-media (icono + nombre) =====
    const media = document.createElement('div');
    media.className = 'hw-media';

    const iconWrap = document.createElement('span');
    iconWrap.className = 'hw-icon-wrap';

    const img = document.createElement('img');
    img.className = 'hw-icon';
    img.src = productData.imagen_url || productImage || '../../assets/images/misc/placeholderHardware.jpg';
    img.alt = productData.nombre || productName;

    iconWrap.appendChild(img);

    const nameLabel = document.createElement('p');
    nameLabel.className = 'hw-label';
    nameLabel.textContent = productName;

    media.appendChild(iconWrap);
    media.appendChild(nameLabel);

    // ===== Lado derecho: .offers-grid (radios + labels) =====
    const offersGrid = document.createElement('div');
    offersGrid.className = 'offers-grid';
    offersGrid.setAttribute('aria-label', 'Tiendas y precios');

    const ofertas = Array.isArray(productData.ofertas) ? productData.ofertas : [];

    if (ofertas.length === 0) {
        const noOffers = document.createElement('p');
        noOffers.className = 'no-offers';
        noOffers.textContent = 'No hay ofertas disponibles.';
        offersGrid.appendChild(noOffers);
    } else {
        const sortedOffers = [...ofertas].sort(
            (a, b) => parseFloat(a.precio_final) - parseFloat(b.precio_final)
        );

        sortedOffers.forEach((oferta, index) => {
            const shopLogo = oferta.tienda_logo || PLACEHOLDER_SHOP_LOGO;
            const inputId = `offer-${productId}-${index}`;

            const radioInput = document.createElement('input');
            radioInput.className = 'offer-radio';
            radioInput.type = 'radio';
            radioInput.name = `product-offers-${productId}`;
            radioInput.id = inputId;

            const label = document.createElement('label');
            label.className = 'offer';
            label.htmlFor = inputId;
            label.title = oferta.tienda_nombre;

            label.innerHTML = `
                <img class="offer-logo" src="${shopLogo}" alt="${oferta.tienda_nombre}">
                <span class="offer-price">${oferta.precio_final} €</span>
            `;

            // El click lo conectaremos al checkout en la parte 2
            label.addEventListener('click', () => {
                registrarSeleccion(productData, oferta);
            });

            offersGrid.appendChild(radioInput);
            offersGrid.appendChild(label);
        });
    }

    productSection.appendChild(media);
    productSection.appendChild(offersGrid);
    cartItemsContainer.appendChild(productSection);
}

// Función que rellena el carrito inferior
function registrarSeleccion(producto, oferta) {
    if (!producto || !oferta) return;

    // Guardamos la selección por ID de producto
    seleccionesCheckout[producto.id] = { producto, oferta };
    renderCheckout();
}

function renderCheckout() {
    const itemsContainer = document.getElementById('checkout-items-container');
    const checkoutBase = document.getElementById('checkout-base');
    const checkoutAhorro = document.getElementById('checkout-ahorro');
    const checkoutTotal = document.getElementById('checkout-total-final');
    const checkoutSub = document.getElementById('checkout-sub');
    const btnComprar = document.getElementById('btn-comprar');

    if (!itemsContainer) return;

    itemsContainer.innerHTML = '';

    const selecciones = Object.values(seleccionesCheckout);

    // Si no hay nada seleccionado, reseteamos totales
    if (selecciones.length === 0) {
        itemsContainer.innerHTML = '<p class="checkout-empty">No hay productos seleccionados todavía.</p>';

        if (checkoutBase) checkoutBase.textContent = '0,00 €';
        if (checkoutAhorro) checkoutAhorro.textContent = '0,00 €';
        if (checkoutTotal) checkoutTotal.textContent = 'TOTAL: 0,00 €';
        if (checkoutSub) checkoutSub.textContent = 'Selecciona productos para ver el desglose de envío';
        if (btnComprar) btnComprar.href = '#';

        return;
    }

    let sumaBase = 0;
    let sumaFinal = 0;
    let sumaEnvio = 0;
    let ultimaOferta = null;

    selecciones.forEach(({ producto, oferta }) => {
        const base = parseFloat(oferta.precio_base) || 0;
        const final = parseFloat(oferta.precio_final) || 0;
        const envio = parseFloat(oferta.gastos_envio) || 0;

        sumaBase += base;
        sumaFinal += final;
        sumaEnvio += envio;
        ultimaOferta = oferta;

        // Crear la línea de checkout para este producto
        const itemDiv = document.createElement('div');
        itemDiv.className = 'checkout-item';

        const imgSrc = producto.imagen_url || '../../assets/images/hardware/placeholder.jpg';

        itemDiv.innerHTML = `
            <img class="checkout-img" src="${imgSrc}" alt="Producto">
            <div class="checkout-info">
                <p class="checkout-name">${producto.nombre}</p>
                <p class="checkout-sub">${oferta.tienda_nombre}</p>
            </div>
            <p class="checkout-price">${oferta.precio_final} €</p>
        `;

        itemsContainer.appendChild(itemDiv);
    });

    const ahorroTotal = sumaBase - sumaFinal;

    if (checkoutBase) checkoutBase.textContent = `${sumaBase.toFixed(2)} €`;
    if (checkoutAhorro) {
        checkoutAhorro.textContent = ahorroTotal > 0 ? `- ${ahorroTotal.toFixed(2)} €` : '0,00 €';
        checkoutAhorro.classList.toggle('positive-ahorro', ahorroTotal > 0);
        checkoutAhorro.classList.toggle('negative-ahorro', ahorroTotal < 0);
    }

    const totalConEnvio = sumaFinal + sumaEnvio;
    if (checkoutTotal) checkoutTotal.textContent = `TOTAL: ${totalConEnvio.toFixed(2)} €`;

    if (checkoutSub) {
        if (sumaEnvio > 0) {
            checkoutSub.textContent = `Incluye ${sumaEnvio.toFixed(2)} € en gastos de envío`;
        } else {
            checkoutSub.textContent = 'Envío Gratis';
        }
    }

    // Mantenemos el comportamiento de "IR A LA TIENDA": último producto seleccionado
    if (btnComprar && ultimaOferta) {
        btnComprar.href = ultimaOferta.enlace_compra || '#';
    }
}

function obtenerToken() {
    return sessionStorage.getItem('access');
}
