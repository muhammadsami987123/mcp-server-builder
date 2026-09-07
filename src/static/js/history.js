/**
 * MCP Server Builder - History Page
 * Display and manage previous generated projects
 */

class HistoryManager {
    constructor() {
        this.projects = [];
        this.filteredProjects = [];
    }

    loadProjects() {
        this.projects = Storage.getJSON('mcpHistory', []);
        this.filteredProjects = [...this.projects];
        this.render();
    }

    searchProjects(query) {
        query = query.toLowerCase().trim();

        if (!query) {
            this.filteredProjects = [...this.projects];
        } else {
            this.filteredProjects = this.projects.filter(project => {
                return (
                    project.name.toLowerCase().includes(query) ||
                    project.url.toLowerCase().includes(query)
                );
            });
        }

        this.render();
    }

    deleteProject(projectId) {
        if (confirm('Are you sure you want to delete this project?')) {
            this.projects = this.projects.filter(p => p.id !== projectId);
            Storage.setJSON('mcpHistory', this.projects);
            this.loadProjects();
            Toast.success('Project deleted');
        }
    }

    clearAllProjects() {
        if (confirm('Are you sure you want to clear all projects? This cannot be undone.')) {
            this.projects = [];
            Storage.setJSON('mcpHistory', []);
            this.loadProjects();
            Toast.success('All projects cleared');
        }
    }

    downloadProject(projectId) {
        const project = this.projects.find(p => p.id === projectId);
        if (project) {
            Toast.success('Download started');
            // In real implementation, would trigger actual download
            API.downloadZip(`/api/project/${projectId}/download`, `${project.name}.zip`);
        }
    }

    viewProject(projectId) {
        const project = this.projects.find(p => p.id === projectId);
        if (project) {
            // Store in session and redirect
            sessionStorage.setItem('currentProjectId', projectId);
            sessionStorage.setItem('currentProject', JSON.stringify(project));
            window.location.href = `/project/${projectId}`;
        }
    }

    formatDate(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;

        // Within 1 hour
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return minutes === 0 ? 'Just now' : `${minutes}m ago`;
        }

        // Within 24 hours
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        }

        // Within 7 days
        if (diff < 604800000) {
            const days = Math.floor(diff / 86400000);
            return days === 1 ? 'Yesterday' : `${days}d ago`;
        }

        // Format as date
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    }

    render() {
        const container = document.getElementById('historyContent');

        if (this.projects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📜</div>
                    <h3>No Projects Yet</h3>
                    <p>Start by building your first MCP server</p>
                    <a href="/builder" class="btn btn-primary">Build Server</a>
                </div>
            `;
            return;
        }

        if (this.filteredProjects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <h3>No Results</h3>
                    <p>Try a different search term</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '<div class="history-list-container"></div>';
        const listContainer = container.querySelector('.history-list-container');

        this.filteredProjects.forEach(project => {
            const card = document.createElement('div');
            card.className = 'history-card';

            card.innerHTML = `
                <div class="history-card-title">${project.name}</div>
                <div class="history-card-meta">
                    <span>${project.tools} tools</span>
                    <span>${this.formatDate(project.timestamp)}</span>
                </div>
                <div class="history-card-url" title="${project.url}">${project.url}</div>
                <div class="history-card-actions">
                    <button class="btn btn-secondary view-btn" data-project-id="${project.id}">
                        View
                    </button>
                    <button class="btn btn-secondary download-btn" data-project-id="${project.id}">
                        📦
                    </button>
                    <button class="btn btn-secondary delete-btn" data-project-id="${project.id}">
                        🗑
                    </button>
                </div>
            `;

            card.querySelector('.view-btn').addEventListener('click', () => {
                this.viewProject(project.id);
            });

            card.querySelector('.download-btn').addEventListener('click', () => {
                this.downloadProject(project.id);
            });

            card.querySelector('.delete-btn').addEventListener('click', () => {
                this.deleteProject(project.id);
            });

            listContainer.appendChild(card);
        });
    }
}

// Initialize
const historyManager = new HistoryManager();

document.addEventListener('DOMContentLoaded', () => {
    historyManager.loadProjects();

    // Search functionality
    const historySearch = document.getElementById('historySearch');
    if (historySearch) {
        historySearch.addEventListener('input', (e) => {
            historyManager.searchProjects(e.target.value);
        });
    }

    // Clear history button
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', () => {
            historyManager.clearAllProjects();
        });
    }

    // Initialize mobile menu
    const toggle = document.querySelector('.navbar-toggle');
    const menu = document.querySelector('.navbar-menu');

    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            menu.classList.toggle('active');
        });

        menu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                menu.classList.remove('active');
            });
        });
    }
});
