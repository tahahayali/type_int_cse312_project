/*  public/js/main.js  */
document.addEventListener('DOMContentLoaded', () => {
    // ───── DOM refs ─────
    const loginForm        = document.getElementById('login-form');
    const registerForm     = document.getElementById('register-form');
    const loginMsg         = document.getElementById('login-message');
    const registerMsg      = document.getElementById('register-message');
    const userInfoWrapper  = document.getElementById('user-info');
    const usernameDisplay  = document.getElementById('username-display');
    const logoutBtn        = document.getElementById('logout-btn');
    const playBtn          = document.getElementById('play-btn');
    const authContainer    = document.querySelector('.auth-container');

    const LS_KEY = 'tag_username';

    /* initial state */
    checkAuthStatus();

    /* ─── listeners ─── */
    loginForm   .addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    logoutBtn   .addEventListener('click',  handleLogout);
    playBtn     .addEventListener('click',  startGame);

    /* ─── handlers ─── */
    async function handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;

        try {
            const res  = await fetch('/login', {
                method : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body   : JSON.stringify({ username, password })
            });
            const data = await res.json();

            if (res.ok) {
                localStorage.setItem(LS_KEY, username);
                loginMsg.textContent = 'Login successful!';
                loginMsg.className   = 'message success';
                checkAuthStatus();
            } else {
                loginMsg.textContent = data.error || 'Login failed';
                loginMsg.className   = 'message error';
            }
        } catch (err) {
            loginMsg.textContent = 'Network error – try again.';
            loginMsg.className   = 'message error';
            console.error(err);
        }
    }

    async function handleRegister(e) {
        e.preventDefault();
        const username = document.getElementById('register-username').value.trim();
        const password = document.getElementById('register-password').value;
        const confirm  = document.getElementById('register-confirm-password').value;

        if (password !== confirm) {
            registerMsg.textContent = 'Passwords do not match!';
            registerMsg.className   = 'message error';
            return;
        }

        try {
            const res  = await fetch('/register', {
                method : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body   : JSON.stringify({ username, password })
            });
            const data = await res.json();

            if (res.ok) {
                registerMsg.textContent = 'Registered! Now log in.';
                registerMsg.className   = 'message success';
                registerForm.reset();
            } else {
                registerMsg.textContent = data.error || 'Registration failed';
                registerMsg.className   = 'message error';
            }
        } catch (err) {
            registerMsg.textContent = 'Network error – try again.';
            registerMsg.className   = 'message error';
            console.error(err);
        }
    }

    async function handleLogout() {
        try {
            await fetch('/logout');
        } finally {
            localStorage.removeItem(LS_KEY);
         // disconnect any existing socket when we leave the game page
           if (window.network && window.network.socket) {
               window.network.socket.disconnect();
           }
            showLoginView();
        }
    }

    async function checkAuthStatus() {
        try {
            const res = await fetch('/api/current-user');
            if (res.ok) {
                const { username } = await res.json();
                localStorage.setItem(LS_KEY, username);
                showUserView(username);
            } else {
                showLoginView();
            }
        } catch (err) {
            console.error(err);
            showLoginView();
        }
    }

    /* ─── view switches ─── */
    function showUserView(username) {
        authContainer      .style.display = 'none';
        userInfoWrapper    .style.display = 'block';
        usernameDisplay.textContent = username;
    }
    function showLoginView() {
        authContainer      .style.display = 'flex';
        userInfoWrapper    .style.display = 'none';
    }

    /* ─── launch game ─── */
    function startGame() {
        window.location.href = '/game';   // game page will read localStorage
    }
});
