import { obtenerToken } from '../../shared/js/carrito.js';
import { API_CONFIGURACION_URL } from '../../shared/js/api-config.js';

document.addEventListener('DOMContentLoaded', async () => {
    const modsGrid = document.querySelector('.mods-grid');
    if (!modsGrid) return;

    async function obtenerJuegosDelCarrito() {
        let juegos = [];
        const token = obtenerToken();

        if (token) {
            try {
                const response = await fetch(API_CONFIGURACION_URL, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    const items = Array.isArray(data) ? data : (data.results || data.items || []);

                    juegos = items
                        .filter(item => item.ranura && item.ranura.startsWith('videojuego'))
                        .map(item => ({
                            id: item.producto || item.id,
                            nombre: item.producto_nombre || item.nombre || 'Videojuego sin nombre',
                            imagen: item.producto_imagen || item.imagen || '',
                            ranura: item.ranura
                        }));
                } else {
                    console.warn('No se pudo cargar el carrito desde servidor. Se usará localStorage.');
                }
            } catch (error) {
                console.error('Error al cargar carrito desde servidor:', error);
            }
        }

        if (juegos.length === 0) {
            const carritoLocal = JSON.parse(localStorage.getItem('carrito_videojuegos')) || [];

            juegos = carritoLocal.map(item => ({
                id: item.id,
                nombre: item.nombre,
                imagen: item.imagen || '',
                ofertas: item.ofertas || []
            }));
        }

        return juegos;
    }

    function obtenerPlataformasMods(juego) {
        // Normalizar: minúsculas, sin espacios extremos, sin acentos
        const nombre = (juego.nombre || '').toLowerCase().trim();
        const plataformas = [];

        // Siempre incluir Nexus Mods y ModDB (para ejemplo hasta método profesional)
        plataformas.push({
            nombre: 'Nexus Mods',
            descripcion: 'Catálogo grande y comunidad activa.',
            url: 'https://www.nexusmods.com'
        });

        plataformas.push({
            nombre: 'ModDB',
            descripcion: 'Base de datos de mods creada por la comunidad.',
            url: 'https://www.moddb.com'
        });

        // --- Bloques por juego específico ---

        if (
            nombre.includes('fifa') ||
            nombre.includes('fc 24') ||
            nombre.includes('fc 25') ||
            nombre.includes('fc 26') ||
            nombre.includes('ea sports fc')
        ) {
            plataformas.push({
                nombre: 'FIFA Infinity Mods',
                descripcion: 'Mods de comunidad para FIFA/FC.',
                url: 'https://dl.fifa-infinity.com'
            });

        } else if (
            nombre.includes('skyrim') ||
            nombre.includes('fallout') ||
            nombre.includes('cities skylines')
        ) {
            plataformas.push({
                nombre: 'Steam Workshop',
                descripcion: 'Contenido creado por usuarios en Steam.',
                url: 'https://steamcommunity.com/workshop/'
            });

        } else if (
            nombre.includes('sackboy') ||
            nombre.includes('super indie karts')
        ) {
            plataformas.push({
                nombre: 'GameBanana',
                descripcion: 'Comunidad con mods y contenido de juegos concretos.',
                url: 'https://gamebanana.com'
            });

        } else if (nombre.includes('rpg maker')) {
            plataformas.push({
                nombre: 'RPG Maker Web',
                descripcion: 'Recursos, plugins y mods oficiales de la comunidad RPG Maker.',
                url: 'https://www.rpgmakerweb.com/'
            });
        }

        return plataformas.slice(0, 3);
    }

    function renderizarTarjetaMod(juego) {
        const gameArticle = document.createElement('article');
        gameArticle.classList.add('game');
        gameArticle.dataset.id = juego.id;

        const imagen = juego.imagen || '../../assets/images/misc/placeholderItem.jpg';
        const plataformas = obtenerPlataformasMods(juego);

        const plataformasHTML = plataformas.map((plataforma, index) => `
            <li class="launcher">
                <div class="launcher-text">
                    <span class="launcher-name">${index + 1}) ${plataforma.nombre}</span>
                    <span class="launcher-desc">${plataforma.descripcion}</span>
                </div>
                <a class="launcher-go" href="${plataforma.url}" target="_blank" rel="noopener noreferrer">Abrir</a>
            </li>
        `).join('');

        gameArticle.innerHTML = `
            <div class="game-top">
                <div class="game-img">
                    <img 
                        src="${imagen}" 
                        alt="Portada de ${juego.nombre}"
                        onerror="this.src='../../assets/images/misc/placeholderItem.jpg'"
                    >
                </div>
                <div class="game-title">
                    <h2>${juego.nombre}</h2>
                    <p>Modders recomendados</p>
                    <div class="game-tags">
                        <span class="tag tag-safe">Seguro</span>
                        <span class="tag tag-count">${plataformas.length} opciones</span>
                    </div>
                </div>
            </div>
            <ul class="launchers">
                ${plataformasHTML}
            </ul>
        `;

        return gameArticle;
    }

    const juegos = await obtenerJuegosDelCarrito();

    if (juegos.length > 0) {
        modsGrid.innerHTML = '';
        juegos.forEach(juego => {
            modsGrid.appendChild(renderizarTarjetaMod(juego));
        });
    } else {
        modsGrid.innerHTML = '<p>No tienes videojuegos en tu carrito para mostrar mods.</p>';
    }
});