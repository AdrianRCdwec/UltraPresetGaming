// ─── CONFIG ──────────────────────────────────────────────────────────────────
const API = 'http://localhost:8000/api';

// ─── ELEMENTOS ───────────────────────────────────────────────────────────────
const form     = document.querySelector('.login-form');
const btnLogin = form.querySelector('.btn-login');
const inputUser = document.getElementById('username');
const inputPass = document.getElementById('password');

// ─── MENSAJE DE ERROR/ÉXITO ──────────────────────────────────────────────────
function mostrarMensaje(texto, tipo = 'error') {
    let msg = document.getElementById('login-msg');
    if (!msg) {
        msg = document.createElement('p');
        msg.id = 'login-msg';
        form.insertBefore(msg, btnLogin);
    }
    msg.textContent = texto;
    msg.style.cssText = `
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 12px;
        text-align: center;
        background: ${tipo === 'error' ? '#fde8e8' : '#e8f5e9'};
        color:      ${tipo === 'error' ? '#c0392b' : '#2e7d32'};
        border:     1px solid ${tipo === 'error' ? '#f5c6c6' : '#c8e6c9'};
    `;
}

// ─── SUBMIT ──────────────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = inputUser.value.trim();
    const password = inputPass.value;

    if (!username || !password) {
        mostrarMensaje('Rellena todos los campos.');
        return;
    }

    btnLogin.disabled = true;
    btnLogin.textContent = 'Entrando...';

    try {
        const res = await fetch(`${API}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        const data = await res.json();

        if (!res.ok) {
            mostrarMensaje(data.error || 'Error al iniciar sesión.');
            return;
        }

        // Guardar sesión en memoria
        sessionStorage.setItem('access',   data.access);
        sessionStorage.setItem('refresh',  data.refresh);
        sessionStorage.setItem('username', data.username);
        sessionStorage.setItem('email',    data.email);

        mostrarMensaje(`¡Bienvenido, ${data.username}!`, 'ok');

        // Redirigir a inicio tras 1 segundo
        setTimeout(() => {
            window.location.href = '../Proyecto_5_pagina.html';
        }, 1000);

    } catch (err) {
        mostrarMensaje('No se pudo conectar con el servidor.');
    } finally {
        btnLogin.disabled = false;
        btnLogin.textContent = 'Iniciar Sesión';
    }
});