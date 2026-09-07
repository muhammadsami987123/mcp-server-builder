/**
 * MCP Server Builder - Project Detail Page
 * Display a specific project's details
 */

class ProjectViewer {
    constructor() {
        this.project = null;
        this.currentFile = null;
    }

    loadProject() {
        const projectData = sessionStorage.getItem('currentProject');
        if (!projectData) {
            window.location.href = '/history';
            return;
        }

        this.project = JSON.parse(projectData);
        this.displayProject();
    }

    displayProject() {
        if (!this.project) return;

        // Update header
        document.getElementById('projectName').textContent = this.project.name;
        document.getElementById('projectDescription').textContent =
            this.project.project?.description || 'API-generated MCP Server';

        // Update stats
        document.getElementById('projectTools').textContent = this.project.tools;
        document.getElementById('projectValidation').textContent = '✓';
        document.getElementById('projectAuthStatus').textContent = '✓';

        // Display content
        this.displayValidation();
        this.displayFileTree();
        this.displayToolsExplorer();
        this.displayReadme();
    }

    displayValidation() {
        const container = document.getElementById('validationContent');
        const validation = this.project.project?.validation;

        if (!validation) {
            container.innerHTML = '<p>No validation data available</p>';
            return;
        }

        let html = `
            <div class="validation-summary">
                <div class="validation-summary-item">
                    ✓ <strong>${validation.checks_passed}</strong> checks passed
                </div>
                <div class="validation-summary-item">
                    ${validation.warnings > 0 ? '⚠' : '○'} <strong>${validation.warnings}</strong> warnings
                </div>
                <div class="validation-summary-item">
                    ${validation.errors > 0 ? '✗' : '○'} <strong>${validation.errors}</strong> errors
                </div>
            </div>
        `;

        if (validation.items) {
            validation.items.forEach(item => {
                const icon = item.type === 'success' ? '✓' : item.type === 'warning' ? '⚠' : '✗';
                html += `
                    <div class="validation-item validation-${item.type}">
                        <div class="validation-icon">${icon}</div>
                        <div class="validation-content">
                            <div class="validation-title">${item.title}</div>
                            <div class="validation-message">${item.message}</div>
                        </div>
                    </div>
                `;
            });
        }

        container.innerHTML = html;
    }

    displayFileTree() {
        const container = document.getElementById('fileTreeContainer');
        const files = this.project.project?.files;

        if (!files) {
            container.innerHTML = '<p class="text-secondary">No files available</p>';
            return;
        }

        container.innerHTML = '';

        // Build folder structure
        const folders = {};
        files.forEach(file => {
            const parts = file.path.split('/');
            let current = folders;

            for (let i = 0; i < parts.length - 1; i++) {
                if (!current[parts[i]]) {
                    current[parts[i]] = { _files: [] };
                }
                current = current[parts[i]];
            }

            current._files.push(file);
        });

        this.renderFileTree(folders, container, 0);
    }

    renderFileTree(folders, container, level) {
        Object.keys(folders).sort().forEach(name => {
            if (name === '_files') return;

            const folder = folders[name];
            const folderEl = document.createElement('div');
            folderEl.className = 'file-tree-folder';

            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'file-tree-toggle';
            toggleBtn.textContent = '▼ ' + name;

            const childrenEl = document.createElement('div');
            childrenEl.className = 'file-tree-children';

            toggleBtn.addEventListener('click', () => {
                childrenEl.classList.toggle('hidden');
                toggleBtn.textContent = childrenEl.classList.contains('hidden') ? '▶ ' + name : '▼ ' + name;
            });

            folderEl.appendChild(toggleBtn);
            folderEl.appendChild(childrenEl);

            this.renderFileTree(folder, childrenEl, level + 1);

            container.appendChild(folderEl);
        });

        if (folders._files) {
            folders._files.forEach(file => {
                const fileEl = document.createElement('div');
                fileEl.className = 'file-tree-item';
                fileEl.innerHTML = `
                    <span class="file-tree-icon">📄</span>
                    <span class="file-tree-name">${file.name}</span>
                `;

                fileEl.addEventListener('click', (e) => {
                    this.selectFile(file, e.currentTarget);
                });

                container.appendChild(fileEl);
            });
        }
    }

    selectFile(file, element) {
        // Update active state
        document.querySelectorAll('.file-tree-item').forEach(el => {
            el.classList.remove('active');
        });
        element.classList.add('active');

        // Display file content
        const fileContents = this.project.project?.fileContents || {};
        const content = fileContents[file.path] || '# File content not available';

        document.getElementById('codeFilename').textContent = file.path;
        document.getElementById('codeContent').textContent = content;

        // Highlight syntax
        if (typeof hljs !== 'undefined') {
            document.getElementById('codeContent').className = `language-${file.type}`;
            hljs.highlightElement(document.getElementById('codeContent'));
        }

        // Update metadata
        this.displayFileMetadata(file, content);
    }

    displayFileMetadata(file, content) {
        const metadata = document.getElementById('fileMetadata');
        const lines = (content || '').split('\n').length;

        metadata.innerHTML = `
            <div class="metadata-item">
                <div class="metadata-label">File</div>
                <div class="metadata-value">${file.path}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Type</div>
                <div class="metadata-value">${file.type}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Lines</div>
                <div class="metadata-value">${lines}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Size</div>
                <div class="metadata-value">~${(content || '').length} bytes</div>
            </div>
        `;
    }

    displayToolsExplorer() {
        const container = document.getElementById('toolsExplorer');

        // Sample tools - in real implementation would come from project data
        const tools = [
            {
                name: 'list_users',
                description: 'List all users from the API',
                method: 'GET',
                path: '/users',
                input_schema: { limit: 'integer', offset: 'integer' },
                output: 'Array of user objects'
            },
            {
                name: 'get_user',
                description: 'Get a specific user by ID',
                method: 'GET',
                path: '/users/{id}',
                input_schema: { id: 'string' },
                output: 'User object'
            },
            {
                name: 'create_user',
                description: 'Create a new user',
                method: 'POST',
                path: '/users',
                input_schema: { name: 'string', email: 'string' },
                output: 'Created user object'
            },
            {
                name: 'delete_user',
                description: 'Delete a user by ID',
                method: 'DELETE',
                path: '/users/{id}',
                input_schema: { id: 'string' },
                output: 'Confirmation message'
            },
            {
                name: 'list_products',
                description: 'List all products',
                method: 'GET',
                path: '/products',
                input_schema: { limit: 'integer' },
                output: 'Array of product objects'
            }
        ];

        container.innerHTML = tools.map(tool => `
            <div class="tool-explorer-item">
                <div class="tool-explorer-header">
                    <div class="tool-explorer-name">${tool.name}</div>
                    <div class="tool-explorer-meta">
                        <span class="tool-badge">${tool.method}</span>
                        <span>${tool.path}</span>
                    </div>
                </div>
                <div class="tool-explorer-description">${tool.description}</div>
                <div class="tool-explorer-section">
                    <div class="tool-explorer-section-title">Input Parameters</div>
                    <div class="tool-explorer-params">
                        ${Object.entries(tool.input_schema).map(([name, type]) => `
                            <div class="param-item">
                                <span class="param-name">${name}</span>
                                <span class="param-type">${type}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="tool-explorer-section">
                    <div class="tool-explorer-section-title">Output</div>
                    <div>${tool.output}</div>
                </div>
            </div>
        `).join('');
    }

    displayReadme() {
        const container = document.getElementById('readmeContent');
        const readme = this.project.project?.readme ||
            `# ${this.project.name}

Generated MCP server.

## Installation

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Running

\`\`\`bash
python src/server.py
\`\`\``;

        container.textContent = readme;

        if (typeof hljs !== 'undefined') {
            container.className = 'language-markdown';
            hljs.highlightElement(container);
        }
    }
}

// Initialize
const projectViewer = new ProjectViewer();

document.addEventListener('DOMContentLoaded', () => {
    projectViewer.loadProject();

    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            button.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });

    // Copy code button
    const copyCodeBtn = document.getElementById('copyCodeBtn');
    if (copyCodeBtn) {
        copyCodeBtn.addEventListener('click', () => {
            const code = document.getElementById('codeContent').textContent;
            navigator.clipboard.writeText(code).then(() => {
                Toast.success('Code copied to clipboard');
            });
        });
    }

    // Download button
    const downloadProjectBtn = document.getElementById('downloadProjectBtn');
    if (downloadProjectBtn) {
        downloadProjectBtn.addEventListener('click', () => {
            Toast.success('Download started');
            const projectId = sessionStorage.getItem('currentProjectId');
            API.downloadZip(`/api/project/${projectId}/download`, 'mcp-server.zip');
        });
    }

    // Tools search
    const toolsSearchViewer = document.getElementById('toolsSearchViewer');
    if (toolsSearchViewer) {
        toolsSearchViewer.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            document.querySelectorAll('.tool-explorer-item').forEach(item => {
                const name = item.querySelector('.tool-explorer-name').textContent.toLowerCase();
                const desc = item.querySelector('.tool-explorer-description').textContent.toLowerCase();
                const matches = name.includes(query) || desc.includes(query);
                item.style.display = matches ? '' : 'none';
            });
        });
    }

    // Mobile menu
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
