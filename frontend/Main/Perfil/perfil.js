const API_PERFIL = 'http://127.0.0.1:8000/api/auth/perfil/';
const MEDIA_BASE = 'http://127.0.0.1:8000'; 

document.addEventListener('DOMContentLoaded', () => {
    // 1. SOLUCIÓN BUG: Buscamos en ambos storages
    const token = localStorage.getItem('access') || sessionStorage.getItem('access');

    if (!token) {
        alert("Debes iniciar sesión para ver tu perfil.");
        window.location.href = "../Login/login.html";
        return;
    }

    // Elementos del DOM
    const form = document.getElementById('perfil-form');
    const inputUsername = document.getElementById('input-username');
    const inputEmail = document.getElementById('input-email');
    const inputNombre = document.getElementById('input-nombre');
    const inputApodo = document.getElementById('input-apodo');
    const imgPreview = document.getElementById('img-preview');
    const inputFoto = document.getElementById('input-foto');
    const btnGuardar = document.getElementById('btn-guardar');
    const mensajeEstado = document.getElementById('mensaje-estado');
    const btnLogout = document.getElementById('btn-logout');

    let archivoFotoNuevo = null;

    async function cargarPerfil() {
        try {
            const respuesta = await fetch(API_PERFIL, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (respuesta.ok) {
                const data = await respuesta.json();
                inputUsername.value = data.username || '';
                inputEmail.value = data.email || '';
                inputNombre.value = data.nombre || '';
                inputApodo.value = data.apodo || '';

                if (data.foto_perfil) {
                    imgPreview.src = data.foto_perfil.startsWith('http') 
                        ? data.foto_perfil 
                        : `${MEDIA_BASE}${data.foto_perfil}`;
                }
            } else if (respuesta.status === 401) {
                // Token caducado
                limpiarSesion();
                window.location.href = "../Login/login.html";
            }
        } catch (error) {
            console.error("Error al cargar perfil:", error);
            mostrarMensaje("Error de conexión al servidor", "error");
        }
    }

    cargarPerfil();

    inputFoto.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            archivoFotoNuevo = file;
            const url = URL.createObjectURL(file);
            imgPreview.src = url;
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        btnGuardar.disabled = true;
        btnGuardar.innerText = "Guardando...";
        mensajeEstado.className = "mensaje-estado"; 

        const formData = new FormData();
        formData.append('nombre', inputNombre.value);
        formData.append('apodo', inputApodo.value);
        if (archivoFotoNuevo) {
            formData.append('foto_perfil', archivoFotoNuevo);
        }

        try {
            const respuesta = await fetch(API_PERFIL, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (respuesta.ok) {
                mostrarMensaje("¡Perfil actualizado con éxito!", "exito");
                archivoFotoNuevo = null; 
            } else {
                mostrarMensaje("Error al actualizar los datos.", "error");
            }
        } catch (error) {
            mostrarMensaje("Error de conexión.", "error");
        } finally {
            btnGuardar.disabled = false;
            btnGuardar.innerText = "Guardar Cambios";
        }
    });

    if(btnLogout) {
        btnLogout.addEventListener('click', () => {
            limpiarSesion();
            window.location.href = "../Login/login.html";
        });
    }

    function mostrarMensaje(texto, tipo) {
        mensajeEstado.innerText = texto;
        mensajeEstado.className = `mensaje-estado ${tipo}`;
        setTimeout(() => { mensajeEstado.className = "mensaje-estado"; }, 4000);
    }

    function limpiarSesion() {
        localStorage.clear();
        sessionStorage.clear();
    }
});