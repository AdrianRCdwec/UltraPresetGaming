(() => {
    const API_PERFIL_HEADER = 'http://127.0.0.1:8000/api/auth/perfil/';
    const MEDIA_BASE_HEADER = 'http://127.0.0.1:8000';

    document.addEventListener('DOMContentLoaded', () => {
        // 1. Obtenemos credenciales buscando en ambos storages
        const token = sessionStorage.getItem('access') || localStorage.getItem('access');
        const username = sessionStorage.getItem('username') || localStorage.getItem('username') || 'U';

        // 2. Buscamos el botón en el header
        const btnSesion = document.querySelector('header .sesion');

        if (token && btnSesion) {
            // --- USUARIO LOGUEADO ---

            // Calculamos ruta base para enlaces
            const currentPath = window.location.pathname;
            const isMainPage = currentPath.includes('Proyecto_5_pagina.html') || currentPath.endsWith('Main/') || currentPath.endsWith('/');
            const baseFolder = isMainPage ? '.' : '..';

            // Comprobamos si estamos dentro de la página del perfil
            const isProfilePage = currentPath.includes('perfil.html');

            // Quitamos el href por defecto
            btnSesion.removeAttribute('href');
            btnSesion.style.cursor = 'pointer';

            if (isProfilePage) {
                // ==========================================
                // LÓGICA PARA LA PÁGINA DE PERFIL (Solo Logout)
                // ==========================================
                btnSesion.innerHTML = 'Cerrar Sesión';
                btnSesion.style.padding = '10px 18px';
                btnSesion.style.width = 'auto'; // Reseteamos anchos del círculo si los tuviera
                btnSesion.style.height = 'auto';
                btnSesion.style.borderRadius = '999px';
                btnSesion.style.backgroundColor = '#e03e3e'; // Botón rojo
                btnSesion.style.color = 'white';
                btnSesion.style.border = 'none';
                btnSesion.style.fontWeight = 'bold';
                btnSesion.style.display = 'inline-flex';
                btnSesion.style.alignItems = 'center';
                btnSesion.style.justifyContent = 'center';

                // Al hacer click se cierra la sesión
                btnSesion.addEventListener('click', (e) => {
                    e.preventDefault();
                    localStorage.clear();
                    sessionStorage.clear();
                    window.location.href = `${baseFolder}/Login/login.html`;
                });

            } else {
                // ==========================================
                // LÓGICA PARA EL RESTO DE PÁGINAS (Foto + Menú)
                // ==========================================

                // A. Convertir el botón en la foto circular
                btnSesion.innerHTML = ''; 
                btnSesion.style.padding = '0';
                btnSesion.style.width = '42px';
                btnSesion.style.height = '42px';
                btnSesion.style.borderRadius = '50%';
                btnSesion.style.overflow = 'hidden';
                btnSesion.style.display = 'inline-flex';
                btnSesion.style.justifyContent = 'center';
                btnSesion.style.alignItems = 'center';
                btnSesion.style.border = '2px solid #9814f1';
                btnSesion.style.backgroundColor = '#f4f7f6';

                // B. Crear imagen
                const imgPerfil = document.createElement('img');
                imgPerfil.style.width = '100%';
                imgPerfil.style.height = '100%';
                imgPerfil.style.objectFit = 'cover';
                imgPerfil.style.display = 'block';
                imgPerfil.src = `https://ui-avatars.com/api/?name=${username}&background=9814f1&color=fff`;
                btnSesion.appendChild(imgPerfil);

                // C. Envolver el botón para crear el menú desplegable
                const container = document.createElement('div');
                container.className = 'user-menu-container';
                btnSesion.parentNode.insertBefore(container, btnSesion);
                container.appendChild(btnSesion);

                // D. Crear el menú flotante
                const dropdown = document.createElement('div');
                dropdown.className = 'user-dropdown';
                dropdown.innerHTML = `
                    <a href="${baseFolder}/Perfil/perfil.html">👤 Mi Perfil</a>
                    <a href="#">⚙️ Ajustes</a>
                    <button class="logout-btn" id="btn-logout-header">🚪 Cerrar Sesión</button>
                `;
                container.appendChild(dropdown);

                // E. Eventos del menú desplegable
                btnSesion.addEventListener('click', (e) => {
                    e.preventDefault();
                    dropdown.classList.toggle('show');
                });

                // Cerrar menú si pinchas fuera
                document.addEventListener('click', (e) => {
                    if (!container.contains(e.target)) {
                        dropdown.classList.remove('show');
                    }
                });

                // F. Evento de Cerrar Sesión desde el menú
                document.getElementById('btn-logout-header').addEventListener('click', () => {
                    localStorage.clear();
                    sessionStorage.clear();
                    window.location.href = `${baseFolder}/Login/login.html`;
                });

                // G. Traer foto real desde Django
                fetch(API_PERFIL_HEADER, {
                    method: 'GET',
                    headers: { 'Authorization': `Bearer ${token}` }
                })
                .then(res => {
                    if (res.ok) return res.json();
                    throw new Error('Token expirado');
                })
                .then(data => {
                    if (data.foto_perfil) {
                        imgPerfil.src = data.foto_perfil.startsWith('http') 
                            ? data.foto_perfil 
                            : `${MEDIA_BASE_HEADER}${data.foto_perfil}`;
                    }
                })
                .catch(err => console.log("Aviso: ", err.message));
            }
        }
    });
})();