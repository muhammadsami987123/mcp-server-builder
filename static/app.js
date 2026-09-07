/**
 * MCP Server Builder - Main Application
 * Core logic, utilities, and home page interactions
 */

const API_BASE = 'http://localhost:8000';

// Toast notification system
class Toast {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.getElementById('toast');
        if (!toast) return;

        toast.textContent = message;
        toast.className = `toast show ${type}`;

        setTimeout(() => {
            toast.classList.remove('show');
        }, duration);
    }

    static success(message) {
        this.show(message, 'success');
    }

    static error(message) {
        this.show(message, 'error');
    }

    static warning(message) {
        this.show(message, 'warning');
    }
}

// API utility functions
class API {
    static async fetch(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const error = await response.json().catch(() => ({
                    detail: response.statusText
                }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    static post(endpoint, data) {
        return this.fetch(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    static get(endpoint) {
        return this.fetch(endpoint);
    }

    static async downloadZip(endpoint, filename = 'mcp-server.zip') {
        const url = `${API_BASE}${endpoint}`;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const blob = await response.blob();
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
        } catch (error) {
            console.error('Download error:', error);
            Toast.error('Failed to download file');
        }
    }
}

// URL validation
class URLValidator {
    static isValid(url) {
        try {
            const parsed = new URL(url);
            if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
                return false;
            }
            return true;
        } catch {
            return false;
        }
    }

    static normalize(url) {
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }
        return url;
    }
}

// Local storage helper
class Storage {
    static setJSON(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('localStorage not available');
        }
    }

    static getJSON(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            console.warn('localStorage not available');
            return defaultValue;
        }
    }

    static remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.warn('localStorage not available');
        }
    }
}

// Mobile menu toggle
function initMobileMenu() {
    const toggle = document.querySelector('.navbar-toggle');
    const menu = document.querySelector('.navbar-menu');

    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            menu.classList.toggle('active');
        });

        // Close menu on link click
        menu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                menu.classList.remove('active');
            });
        });
    }
}

// Home page specific functions
function initHomePage() {
    const heroInput = document.getElementById('heroUrlInput');
    const heroSubmitBtn = document.getElementById('heroSubmitBtn');
    const demoBtn = document.getElementById('demoBtn');

    if (heroSubmitBtn) {
        heroSubmitBtn.addEventListener('click', () => {
            const url = heroInput.value.trim();

            if (!url) {
                Toast.warning('Please enter a URL');
                return;
            }

            if (!URLValidator.isValid(url)) {
                Toast.error('Please enter a valid URL');
                return;
            }

            // Save URL to session and redirect to builder
            sessionStorage.setItem('initialUrl', URLValidator.normalize(url));
            window.location.href = '/builder';
        });

        heroInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                heroSubmitBtn.click();
            }
        });
    }

    if (demoBtn) {
        demoBtn.addEventListener('click', () => {
            sessionStorage.setItem('useDemo', 'true');
            window.location.href = '/builder';
        });
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initHomePage();

    // Syntax highlighting initialization
    if (typeof hljs !== 'undefined') {
        document.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });
    }
});
