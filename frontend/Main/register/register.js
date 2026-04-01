// ─── CONFIG ──────────────────────────────────────────────────────────────────
const API = 'http://localhost:8000/api';

// ─── ELEMENTOS ───────────────────────────────────────────────────────────────
const form      = document.querySelector('.register-form');
const btnReg    = form.querySelector('.btn-register');
const inputUser = document.getElementById('username');
const inputMail = document.getElementById('mail');
const inputPass = document.getElementById('password');
const inputPass2= document.getElementById('password2');

// ─── MENSAJE DE ERROR/ÉXITO ──────────────────────────────────────────────────
function mostrarMensaje(texto, tipo = 'error') {
    let msg = document.getElementById('register-msg');
    if (!msg) {
        msg = document.createElement('p');
        msg.id = 'register-msg';
        form.insertBefore(msg, btnReg);
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

    const username  = inputUser.value.trim();
    const email     = inputMail.value.trim();
    const password  = inputPass.value;
    const password2 = inputPass2.value;

    if (!username || !email || !password || !password2) {
        mostrarMensaje('Rellena todos los campos.');
        return;
    }

    if (password !== password2) {
        mostrarMensaje('Las contraseñas no coinciden.');
        return;
    }

    if (password.length < 8) {
        mostrarMensaje('La contraseña debe tener al menos 8 caracteres.');
        return;
    }

    btnReg.disabled = true;
    btnReg.textContent = 'Creando cuenta...';

    try {
        const res = await fetch(`${API}/auth/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, password2 }),
        });

        const data = await res.json();

        if (!res.ok) {
            mostrarMensaje(data.error || 'Error al crear la cuenta.');
            // Solo rehabilitamos el botón si hay error
            btnReg.disabled = false;
            btnReg.textContent = 'Crear Cuenta';
            return;
        }

        // Guardar sesión directamente tras registrarse
        sessionStorage.setItem('access',   data.access);
        sessionStorage.setItem('refresh',  data.refresh);
        sessionStorage.setItem('username', data.username);
        sessionStorage.setItem('email',    data.email);

        // Redirección instantánea sin setTimeout
        window.location.href = '../login/login.html';

    } catch (err) {
        console.error(err);
        mostrarMensaje('No se pudo conectar con el servidor.');
        // Solo rehabilitamos el botón si hay error crítico
        btnReg.disabled = false;
        btnReg.textContent = 'Crear Cuenta';
    }
});