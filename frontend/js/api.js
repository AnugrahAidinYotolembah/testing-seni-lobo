// ==============================================
// API Client — Arsip Digital Komunitas Seni Lobo Palu
// ==============================================

const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : '/api';

// ── Token Management ──
function getToken() {
    return localStorage.getItem('lobo_token');
}

function setToken(token) {
    localStorage.setItem('lobo_token', token);
}

function removeToken() {
    localStorage.removeItem('lobo_token');
    localStorage.removeItem('lobo_user');
}

function getUser() {
    const u = localStorage.getItem('lobo_user');
    return u ? JSON.parse(u) : null;
}

function setUser(user) {
    localStorage.setItem('lobo_user', JSON.stringify(user));
}

function isLoggedIn() {
    return !!getToken();
}

function logout() {
    removeToken();
    window.location.href = 'login.html';
}

// ── Fetch Wrapper ──
async function apiFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // Remove Content-Type for FormData
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401 && endpoint !== '/auth/login' && endpoint !== '/auth/register') {
        const isPublicPage = window.location.pathname.endsWith('index.html') || 
                             window.location.pathname === '/' || 
                             window.location.pathname.endsWith('/') ||
                             window.location.pathname.endsWith('login.html');
        removeToken();
        if (!isPublicPage) {
            window.location.href = 'login.html';
        }
        return null;
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || 'API Error');
    }

    return data;
}

// ── Auth API ──
async function apiLogin(email, password) {
    const data = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
    });
    if (data && data.token) {
        setToken(data.token);
        setUser(data.user);
    }
    return data;
}

async function apiRegister(email, password, fullName, role = 'user') {
    const data = await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: fullName, role }),
    });
    if (data && data.token) {
        setToken(data.token);
        setUser(data.user);
    }
    return data;
}

async function apiGoogleLogin(credential) {
    const data = await apiFetch('/auth/google-login', {
        method: 'POST',
        body: JSON.stringify({ credential }),
    });
    if (data && data.token) {
        setToken(data.token);
        setUser(data.user);
    }
    return data;
}

async function apiGetMe() {
    return await apiFetch('/auth/me');
}

async function apiForgotPassword(email) {
    return await apiFetch('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
    });
}

async function apiResetPassword(token, newPassword) {
    return await apiFetch('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token, new_password: newPassword }),
    });
}

async function apiResetPasswordDirect(email, newPassword) {
    return await apiFetch('/auth/reset-password-direct', {
        method: 'POST',
        body: JSON.stringify({ email, new_password: newPassword }),
    });
}

// ── Collections API ──
async function apiGetCollections(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page);
    if (params.limit) query.set('limit', params.limit);
    if (params.category) query.set('category', params.category);
    if (params.user_id) query.set('user_id', params.user_id);
    if (params.sort_by) query.set('sort_by', params.sort_by);
    if (params.sort_order) query.set('sort_order', params.sort_order);
    return await apiFetch(`/collections?${query.toString()}`);
}

async function apiGetCollectionStats() {
    return await apiFetch('/collections/stats');
}

async function apiCreateCollection(data) {
    return await apiFetch('/collections', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

async function apiUpdateCollection(id, data) {
    return await apiFetch(`/collections/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

async function apiDeleteCollection(id) {
    return await apiFetch(`/collections/${id}`, {
        method: 'DELETE',
    });
}

// ── Users API ──
async function apiGetUsers() {
    return await apiFetch('/users');
}

async function apiGetUserStats() {
    return await apiFetch('/users/stats');
}

// ── Upload API ──
async function apiUploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    return await apiFetch('/upload', {
        method: 'POST',
        body: formData,
    });
}

// ── AI API ──
async function apiAiChat(message, history = []) {
    return await apiFetch('/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ message, history }),
    });
}

// ── Auth Guard ──
function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

function requireAdmin() {
    const user = getUser();
    if (!user || user.role !== 'admin') {
        window.location.href = 'user-home.html';
        return false;
    }
    return true;
}

// ── Utility ──
function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const now = new Date();
    const d = new Date(dateStr);
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
    return formatDate(dateStr);
}
