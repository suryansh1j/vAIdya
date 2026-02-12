// ==================== Authentication Module ====================

const AUTH_API = '/api/v1/auth';
const TOKEN_KEY = 'vaidya_token';
const USER_KEY = 'vaidya_user';

class AuthManager {
    constructor() {
        this.token = localStorage.getItem(TOKEN_KEY);
        this.user = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    }

    isAuthenticated() {
        return !!this.token;
    }

    getToken() {
        return this.token;
    }

    getUser() {
        return this.user;
    }

    async login(username, password) {
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch(`${AUTH_API}/login`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                // Handle FastAPI validation errors (422)
                if (Array.isArray(error.detail)) {
                    const messages = error.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
                    throw new Error(messages);
                }
                throw new Error(error.detail || 'Login failed');
            }

            const data = await response.json();
            this.token = data.access_token;
            this.user = { username };

            localStorage.setItem(TOKEN_KEY, this.token);
            localStorage.setItem(USER_KEY, JSON.stringify(this.user));

            return data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    async register(username, email, password, fullName = '') {
        try {
            const response = await fetch(`${AUTH_API}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                    full_name: fullName
                })
            });

            if (!response.ok) {
                const error = await response.json();
                // Handle FastAPI validation errors (422)
                if (Array.isArray(error.detail)) {
                    const messages = error.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
                    throw new Error(messages);
                }
                throw new Error(error.detail || 'Registration failed');
            }

            const data = await response.json();

            // Auto-login after registration
            await this.login(username, password);

            return data;
        } catch (error) {
            console.error('Registration error:', error);
            throw error;
        }
    }

    async getCurrentUser() {
        if (!this.token) return null;

        try {
            const response = await fetch(`${AUTH_API}/me`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    this.logout();
                }
                throw new Error('Failed to get user info');
            }

            const user = await response.json();
            this.user = user;
            localStorage.setItem(USER_KEY, JSON.stringify(user));

            return user;
        } catch (error) {
            console.error('Get user error:', error);
            return null;
        }
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    }

    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`
        };
    }
}

// Create global auth instance
window.authManager = new AuthManager();

// ==================== Auth UI Handlers ====================

document.addEventListener('DOMContentLoaded', () => {
    const authModal = document.getElementById('authModal');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const closeBtn = document.querySelector('.close');
    const showRegisterBtn = document.getElementById('showRegister');
    const showLoginBtn = document.getElementById('showLogin');
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const userDisplay = document.getElementById('userDisplay');

    // Check authentication on load
    if (authManager.isAuthenticated()) {
        updateUIForAuthenticatedUser();
        authManager.getCurrentUser().then(user => {
            if (user) {
                userDisplay.textContent = user.username || user.email;
            }
        });
    } else {
        showAuthModal();
    }

    // Modal controls
    closeBtn.onclick = () => {
        if (authManager.isAuthenticated()) {
            authModal.classList.remove('active');
        }
    };

    window.onclick = (event) => {
        if (event.target === authModal && authManager.isAuthenticated()) {
            authModal.classList.remove('active');
        }
    };

    // Switch between login and register
    showRegisterBtn.onclick = () => {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        document.getElementById('authTitle').textContent = 'Register for vAIdya';
    };

    showLoginBtn.onclick = () => {
        registerForm.style.display = 'none';
        loginForm.style.display = 'block';
        document.getElementById('authTitle').textContent = 'Login to vAIdya';
    };

    // Login handler
    loginBtn.onclick = async () => {
        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value;

        if (!username || !password) {
            showToast('Please enter username and password', 'error');
            return;
        }

        loginBtn.disabled = true;
        loginBtn.textContent = 'Logging in...';

        try {
            await authManager.login(username, password);
            showToast('Login successful!', 'success');
            authModal.classList.remove('active');
            updateUIForAuthenticatedUser();
            userDisplay.textContent = username;

            // Clear form
            document.getElementById('loginUsername').value = '';
            document.getElementById('loginPassword').value = '';
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login';
        }
    };

    // Register handler
    registerBtn.onclick = async () => {
        const username = document.getElementById('regUsername').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;
        const fullName = document.getElementById('regFullName').value.trim();

        if (!username || !email || !password) {
            showToast('Please fill in all required fields', 'error');
            return;
        }

        if (password.length < 6) {
            showToast('Password must be at least 6 characters', 'error');
            return;
        }

        registerBtn.disabled = true;
        registerBtn.textContent = 'Registering...';

        try {
            await authManager.register(username, email, password, fullName);
            showToast('Registration successful!', 'success');
            authModal.classList.remove('active');
            updateUIForAuthenticatedUser();
            userDisplay.textContent = username;

            // Clear form
            document.getElementById('regUsername').value = '';
            document.getElementById('regEmail').value = '';
            document.getElementById('regPassword').value = '';
            document.getElementById('regFullName').value = '';
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            registerBtn.disabled = false;
            registerBtn.textContent = 'Register';
        }
    };

    // Logout handler
    logoutBtn.onclick = () => {
        authManager.logout();
        showToast('Logged out successfully', 'info');
        updateUIForUnauthenticatedUser();
        showAuthModal();
    };

    // Enter key support
    document.getElementById('loginPassword').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') loginBtn.click();
    });

    document.getElementById('regPassword').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') registerBtn.click();
    });
});

function showAuthModal() {
    document.getElementById('authModal').classList.add('active');
}

function updateUIForAuthenticatedUser() {
    document.getElementById('userDisplay').style.display = 'inline';
    document.getElementById('logoutBtn').style.display = 'inline-block';
}

function updateUIForUnauthenticatedUser() {
    document.getElementById('userDisplay').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
    document.getElementById('userDisplay').textContent = '';
}

// ==================== Toast Notifications ====================

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Make showToast globally available
window.showToast = showToast;
