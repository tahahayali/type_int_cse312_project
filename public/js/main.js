document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const loginMessage = document.getElementById('login-message');
    const registerMessage = document.getElementById('register-message');
    const userInfo = document.getElementById('user-info');
    const usernameDisplay = document.getElementById('username-display');
    const logoutBtn = document.getElementById('logout-btn');
    const playBtn = document.getElementById('play-btn');
    const gameContainer = document.getElementById('game-container');
    const authContainer = document.querySelector('.auth-container');

    // Check if user is already logged in
    checkAuthStatus();

    // Event Listeners
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    logoutBtn.addEventListener('submit', handleLogout);
    playBtn.addEventListener('click', startGame);

    // Functions
    async function handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                loginMessage.textContent = 'Login successful!';
                loginMessage.className = 'message success';
                showUserInfo(username);
            } else {
                loginMessage.textContent = data.error || 'Login failed';
                loginMessage.className = 'message error';
            }

        } catch (error) {
            loginMessage.textContent = 'An error occurred. Please try again.';
            loginMessage.className = 'message error';
            console.error('Login error:', error);
        }
    }

    async function handleRegister(e) {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const confirmPassword = document.getElementById('register-confirm-password').value;

        if (password !== confirmPassword) {
            registerMessage.textContent = 'Passwords do not match!';
            registerMessage.className = 'message error';
            return;
        }

        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                registerMessage.textContent = 'Registration successful! You can now login.';
                registerMessage.className = 'message success';
                // Clear form
                registerForm.reset();
            } else {
                registerMessage.textContent = data.error || 'Registration failed';
                registerMessage.className = 'message error';
            }

        } catch (error) {
            registerMessage.textContent = 'An error occurred. Please try again.';
            registerMessage.className = 'message error';
            console.error('Registration error:', error);
        }
    }

    async function handleLogout() {
        try {
            const response = await fetch('/logout', {
                method: 'GET'
            });

            if (response.ok) {
                showLoginRegister();
            }

        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    async function checkAuthStatus() {
        try {
            // This is a placeholder - you might need to implement a /check-auth endpoint
            // For now, we'll just check if there's a username cookie or similar
            const authCookie = document.cookie.includes('auth');

            if (authCookie) {
                // For testing, just show the user as logged in
                showUserInfo('TestUser');
            } else {
                showLoginRegister();
            }

        } catch (error) {
            console.error('Auth check error:', error);
            showLoginRegister();
        }
    }

    function showUserInfo(username) {
        authContainer.style.display = 'none';
        userInfo.style.display = 'block';
        usernameDisplay.textContent = username;
    }

    function showLoginRegister() {
        authContainer.style.display = 'flex';
        userInfo.style.display = 'none';
        gameContainer.style.display = 'none';
    }

    function startGame() {
        gameContainer.style.display = 'block';
        // Here you would initialize your Phaser game
        console.log('Starting game...');
    }
});