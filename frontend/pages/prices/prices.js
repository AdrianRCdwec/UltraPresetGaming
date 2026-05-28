import { API_CONFIGURACION_URL, API_PRODUCTOS_URL } from '../../shared/js/api-config.js';
import { obtenerToken } from '../../shared/js/carrito.js';

const PLACEHOLDER_SHOP_LOGO = '../../assets/images/misc/placeholderShop.jpg';
let seleccionesCheckout = {}; // clave: ranura o videojuego_ID → { producto, oferta }

document.addEventListener('DOMContentLoaded', () => {
    cargarProductosDelCarrito();
});

async function cargarProductosDelCarrito() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const loadingMessage = document.getElementById('loading-message');
    const emptyCartMessage = document.getElementById('empty-cart-message');

    if (loadingMessage) loadingMessage.style.display = 'block';
    if (emptyCartMessage) emptyCartMessage.style.display = 'none';
    if (cartItemsContainer) cartItemsContainer.innerHTML = '';

    const token = obtenerToken();

    if (!token) {
        console.log('Sin token, cargando carrito desde localStorage...');
        await cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage);
        renderCheckout();
        return;
    }

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
        const cartItems = configData.results ? configData.results : configData;

        if (!cartItems.length) {
            await cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage);
            renderCheckout();
            return;
        }

        if (emptyCartMessage) emptyCartMessage.style.display = 'none';

        for (const cartItem of cartItems) {
            const productResponse = await fetch(`${API_PRODUCTOS_URL}${cartItem.producto}/`);

            if (!productResponse.ok) {
                console.error(`Error al obtener detalles del producto ${cartItem.producto}: ${productResponse.statusText}`);
                continue;
            }

            const productData = await productResponse.json();
            const esVideojuego = cartItem.ranura?.startsWith('videojuego_');
            renderCartItem(cartItem, productData, esVideojuego);
        }

    } catch (error) {
        console.error('Error al cargar productos del carrito desde servidor:', error);
        await cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage);
    } finally {
        if (loadingMessage) loadingMessage.style.display = 'none';
        renderCheckout();
    }
}

async function cargarDesdeLocalStorage(cartItemsContainer, loadingMessage, emptyCartMessage) {
    const rawHardware = localStorage.getItem('carrito_hardware');
    const carritoHardware = rawHardware ? JSON.parse(rawHardware) : {};
    const itemsHardware = Object.values(carritoHardware);

    const rawVideojuegos = localStorage.getItem('carrito_videojuegos');
    const carritoVideojuegos = rawVideojuegos ? JSON.parse(rawVideojuegos) : [];

    const hayItems = itemsHardware.length > 0 || carritoVideojuegos.length > 0;

    if (!hayItems) {
        if (loadingMessage) loadingMessage.style.display = 'none';
        if (emptyCartMessage) emptyCartMessage.style.display = 'block';
        return;
    }

    if (emptyCartMessage) emptyCartMessage.style.display = 'none';

    // Hardware
    for (const item of itemsHardware) {
        try {
            const productResponse = await fetch(`${API_PRODUCTOS_URL}${item.id}/`);
            if (!productResponse.ok) {
                console.error(`Error al obtener detalles del producto ${item.id}: ${productResponse.statusText}`);
                continue;
            }

            const productData = await productResponse.json();
            renderCartItem(item, productData, false);
        } catch (error) {
            console.error('Error al obtener producto hardware desde localStorage:', error);
        }
    }

    // Videojuegos
    for (const juego of carritoVideojuegos) {
        try {
            const productResponse = await fetch(`${API_PRODUCTOS_URL}${juego.id}/`);
            if (!productResponse.ok) {
                console.error(`Error al obtener detalles del videojuego ${juego.id}: ${productResponse.statusText}`);
                continue;
            }

            const productData = await productResponse.json();
            renderCartItem(juego, productData, true);
        } catch (error) {
            console.error('Error al obtener videojuego desde localStorage:', error);
        }
    }

    if (loadingMessage) loadingMessage.style.display = 'none';
}

function renderCartItem(cartItem, productData, esVideojuego = false) {
    const cartItemsContainer = document.getElementById('cart-items-container');
    if (!cartItemsContainer) return;

    const productId = cartItem.producto || cartItem.id;
    const productName = cartItem.producto_nombre || cartItem.nombre || productData.nombre;
    const productImage = cartItem.producto_imagen || cartItem.imagen || productData.imagen_url;

    const productSection = document.createElement('section');
    productSection.className = 'hw-item';
    productSection.id = `product-${productId}`;

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

            const precioNumero = parseFloat(oferta.precio_final) || 0;
            const precioFormateado = precioNumero.toFixed(2).replace(".", ",");

            label.innerHTML = `
                <img class="offer-logo" src="${shopLogo}" alt="${oferta.tienda_nombre}">
                <span class="offer-price">${precioFormateado} €</span>
            `;

            label.addEventListener('click', () => {
                const claveSeleccion = esVideojuego
                    ? `videojuego_${productId}`
                    : (cartItem.ranura ? cartItem.ranura : `hardware_${productId}`);
            
                registrarSeleccion(
                    {
                        id: productId,
                        nombre: productName,
                        imagen_url: productData.imagen_url || productImage || '../../assets/images/misc/placeholderHardware.jpg',
                    },
                    oferta,
                    esVideojuego,
                    claveSeleccion
                );
            });

            offersGrid.appendChild(radioInput);
            offersGrid.appendChild(label);
        });
    }

    productSection.appendChild(media);
    productSection.appendChild(offersGrid);
    cartItemsContainer.appendChild(productSection);
}

function registrarSeleccion(producto, oferta, esVideojuego = false, claveOriginal = null) {
    if (!producto || !oferta) return;

    const clave = claveOriginal || (esVideojuego ? `videojuego_${producto.id}` : `hardware_${producto.id}`);
    seleccionesCheckout[clave] = { producto, oferta };
    renderCheckout();
}

function reconstruirSeleccionesCheckoutDesdeCarritos() {
    const carritoHW = JSON.parse(localStorage.getItem('carrito_hardware')) || {};
    const carritoVG = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];

    const nuevasSelecciones = {};

    // Hardware
    Object.entries(carritoHW).forEach(([ranura, item]) => {
        nuevasSelecciones[ranura] = {
            producto: {
                id: item.id,
                nombre: item.nombre,
                imagen_url: item.imagen || '../../assets/images/hardware/placeholder.jpg',
            },
            oferta: {
                tienda_nombre: item.tienda_nombre || '—',
                precio_base: item.precio || 0,
                precio_final: item.precio || 0,
                gastos_envio: item.gastos_envio || 0,
                enlace_compra: item.enlace_compra || '#',
            },
        };
    });

    // Videojuegos
    carritoVG.forEach((juego, index) => {
        const oferta = (juego.ofertas && juego.ofertas.length > 0)
            ? juego.ofertas[0]
            : {
                tienda_nombre: 'Steam',
                precio_base: 0,
                precio_final: 0,
                gastos_envio: 0,
                enlace_compra: juego.link || '#',
            };

        nuevasSelecciones[`videojuego_${juego.id || index}`] = {
            producto: {
                id: juego.id,
                nombre: juego.nombre,
                imagen_url: juego.imagen || '../../assets/images/hardware/placeholder.jpg',
            },
            oferta: {
                tienda_nombre: oferta.tienda_nombre || 'Steam',
                precio_base: oferta.precio_base || oferta.precio_final || 0,
                precio_final: oferta.precio_final || 0,
                gastos_envio: oferta.gastos_envio || 0,
                enlace_compra: oferta.enlace_compra || juego.link || '#',
            },
        };
    });

    seleccionesCheckout = nuevasSelecciones;
}

function renderCheckout() {
    const checkoutSection = document.getElementById('checkout-summary');
    const itemsContainer = document.getElementById('checkout-items-container');
    const checkoutBase = document.getElementById('checkout-base');
    const checkoutAhorro = document.getElementById('checkout-ahorro');
    const checkoutTotal = document.getElementById('checkout-total-final');
    const checkoutSub = document.getElementById('checkout-sub');
    const btnComprar = document.getElementById('btn-comprar');

    if (!itemsContainer) return;

    itemsContainer.innerHTML = '';

    const selecciones = Object.values(seleccionesCheckout);

    if (selecciones.length === 0) {
        if (checkoutSection) checkoutSection.style.display = 'none';

        if (checkoutBase) checkoutBase.textContent = '';
        if (checkoutAhorro) checkoutAhorro.textContent = '';
        if (checkoutTotal) checkoutTotal.textContent = '';
        if (checkoutSub) checkoutSub.textContent = '';
        if (btnComprar) btnComprar.href = '#';

        return;
    }

    if (checkoutSection) checkoutSection.style.display = 'block';

    let sumaBase = 0;
    let sumaFinal = 0;
    let sumaEnvio = 0;

    selecciones.forEach(({ producto, oferta }) => {
        const base = parseFloat(oferta.precio_base) || parseFloat(oferta.precio_final) || 0;
        const final = parseFloat(oferta.precio_final) || 0;
        const envio = parseFloat(oferta.gastos_envio) || 0;

        sumaBase += base;
        sumaFinal += final;
        sumaEnvio += envio;

        const itemDiv = document.createElement('div');
        itemDiv.className = 'checkout-item';

        const imgSrc = producto.imagen_url || '../../assets/images/hardware/placeholder.jpg';

        itemDiv.innerHTML = `
            <img class="checkout-img" src="${imgSrc}" alt="${producto.nombre}">
            <div class="checkout-info">
                <p class="checkout-name">${producto.nombre}</p>
                <p class="checkout-sub">${oferta.tienda_nombre || 'Tienda no disponible'}</p>
            </div>
            <p class="checkout-price">${final.toFixed(2).replace('.', ',')} €</p>
        `;

        itemsContainer.appendChild(itemDiv);
    });

    const ahorroTotal = sumaBase - sumaFinal;
    const totalConEnvio = sumaFinal + sumaEnvio;

    if (checkoutBase) {
        checkoutBase.textContent = `${sumaBase.toFixed(2).replace('.', ',')} €`;
    }

    if (checkoutAhorro) {
        checkoutAhorro.textContent = ahorroTotal > 0
            ? `- ${ahorroTotal.toFixed(2).replace('.', ',')} €`
            : '0,00 €';

        checkoutAhorro.classList.toggle('positive-ahorro', ahorroTotal > 0);
        checkoutAhorro.classList.toggle('negative-ahorro', ahorroTotal < 0);
    }

    if (checkoutTotal) {
        checkoutTotal.textContent = `TOTAL: ${totalConEnvio.toFixed(2).replace('.', ',')} €`;
    }

    if (checkoutSub) {
        checkoutSub.textContent = sumaEnvio > 0
            ? `Incluye ${sumaEnvio.toFixed(2).replace('.', ',')} € en gastos de envío`
            : 'Envío gratis';
    }

    if (btnComprar) {
        const enlaces = selecciones
            .map(({ oferta }) => oferta.enlace_compra)
            .filter(Boolean);

        btnComprar.href = enlaces[0] || '#';
    }
}