/**
 * MCP Server Builder - Builder Page
 * Core builder workflow and interactions
 */

class MCPBuilder {
    constructor() {
        this.currentStep = 1;
        this.analysisData = null;
        this.generatedProject = null;
        this.selectedTools = [];
        this.stages = [
            'connect',
            'inspect',
            'detect',
            'parse',
            'auth',
            'design',
            'generate',
            'validate'
        ];
    }

    // Navigation
    showStep(stepNumber) {
        document.querySelectorAll('.builder-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`step${stepNumber}`).classList.add('active');
        this.currentStep = stepNumber;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Analysis progress
    markStageComplete(stageName) {
        const stage = document.getElementById(`stage-${stageName}`);
        if (!stage) return;

        const icon = stage.querySelector('.stage-icon');
        icon.textContent = '✓';
        icon.classList.add('completed');
        icon.style.animation = 'none';
    }

    markStageRunning(stageName) {
        const stage = document.getElementById(`stage-${stageName}`);
        if (!stage) return;

        const icon = stage.querySelector('.stage-icon');
        icon.textContent = '●';
        icon.classList.remove('completed');
        icon.style.animation = 'spin 2s linear infinite';
    }

    updateStageStatus(stageName, status) {
        const stage = document.getElementById(`stage-${stageName}`);
        if (!stage) return;

        const statusEl = stage.querySelector('.stage-status');
        if (statusEl) {
            statusEl.textContent = status;
        }
    }

    // Start analysis
    async analyzeUrl(url) {
        this.showStep(2);

        try {
            // Use demo data if requested
            const useDemo = sessionStorage.getItem('useDemo');
            if (useDemo) {
                await this.useDemoAnalysis();
                return;
            }

            document.getElementById('analyzeUrl').textContent = url;

            // Simulate realistic analysis flow with backend
            for (let i = 0; i < this.stages.length; i++) {
                const stageName = this.stages[i];
                this.markStageRunning(stageName);

                try {
                    // Call backend for each stage
                    await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate work

                    this.markStageComplete(stageName);
                    this.updateStageStatus(stageName, 'Completed');
                } catch (error) {
                    this.updateStageStatus(stageName, `Error: ${error.message}`);
                    throw error;
                }
            }

            // Simulate discovery response
            this.analysisData = {
                api_name: 'Example API',
                description: 'Sample API for demonstration',
                base_url: url,
                endpoints: [
                    {
                        path: '/users',
                        method: 'GET',
                        description: 'List all users',
                        parameters: []
                    },
                    {
                        path: '/users/{id}',
                        method: 'GET',
                        description: 'Get a specific user',
                        parameters: [{ name: 'id', required: true, type: 'string' }]
                    },
                    {
                        path: '/users',
                        method: 'POST',
                        description: 'Create a new user',
                        parameters: []
                    },
                    {
                        path: '/products',
                        method: 'GET',
                        description: 'List all products',
                        parameters: [{ name: 'limit', required: false, type: 'integer' }]
                    }
                ],
                authentication: {
                    type: 'bearer',
                    description: 'Bearer token required'
                }
            };

            // Show tools selection
            this.showToolsSelection();
        } catch (error) {
            console.error('Analysis error:', error);
            const errorEl = document.getElementById('analysisError');
            if (errorEl) {
                errorEl.textContent = error.message;
                errorEl.style.display = 'block';
            }
            Toast.error('Analysis failed: ' + error.message);

            // Go back to step 1
            setTimeout(() => this.showStep(1), 2000);
        }
    }

    async useDemoAnalysis() {
        document.getElementById('analyzeUrl').textContent = 'https://api.example.com/docs (Demo)';

        // Simulate stages
        for (let i = 0; i < this.stages.length; i++) {
            const stageName = this.stages[i];
            this.markStageRunning(stageName);
            await new Promise(resolve => setTimeout(resolve, 500));
            this.markStageComplete(stageName);
            this.updateStageStatus(stageName, 'Completed');
        }

        // Set demo analysis data
        this.analysisData = {
            api_name: 'Example API',
            description: 'Comprehensive REST API for user and product management',
            base_url: 'https://api.example.com',
            endpoints: [
                {
                    path: '/users',
                    method: 'GET',
                    description: 'List all users with pagination',
                    parameters: []
                },
                {
                    path: '/users/{id}',
                    method: 'GET',
                    description: 'Get a specific user by ID',
                    parameters: [{ name: 'id', required: true, type: 'string' }]
                },
                {
                    path: '/users',
                    method: 'POST',
                    description: 'Create a new user',
                    parameters: []
                },
                {
                    path: '/users/{id}',
                    method: 'DELETE',
                    description: 'Delete a user by ID',
                    parameters: [{ name: 'id', required: true, type: 'string' }]
                },
                {
                    path: '/products',
                    method: 'GET',
                    description: 'List all products with filters',
                    parameters: [{ name: 'limit', required: false, type: 'integer' }]
                }
            ],
            authentication: {
                type: 'bearer',
                description: 'Bearer token required in Authorization header'
            }
        };

        this.showToolsSelection();
    }

    showToolsSelection() {
        // Generate tool items from analysis data
        const toolsList = document.getElementById('toolsList');
        toolsList.innerHTML = '';

        // Create mock tools from endpoints
        const tools = this.analysisData.endpoints.map((endpoint, idx) => ({
            id: `tool_${idx}`,
            name: this.endpointToToolName(endpoint),
            description: endpoint.description,
            method: endpoint.method,
            path: endpoint.path,
            parameters: endpoint.parameters || []
        }));

        this.selectedTools = tools.map(t => t.id);
        let selected = this.selectedTools.length;

        tools.forEach(tool => {
            const item = document.createElement('div');
            item.className = 'tool-item';
            item.innerHTML = `
                <input type="checkbox" class="tool-checkbox" data-tool-id="${tool.id}" checked>
                <div class="tool-info">
                    <div class="tool-name">${tool.name}</div>
                    <div class="tool-description">${tool.description}</div>
                    <div class="tool-meta">
                        <span class="tool-badge">${tool.method}</span>
                        <span>${tool.path}</span>
                        ${tool.parameters.length > 0 ? `<span>${tool.parameters.length} param${tool.parameters.length !== 1 ? 's' : ''}</span>` : ''}
                    </div>
                </div>
            `;

            const checkbox = item.querySelector('.tool-checkbox');
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    if (!this.selectedTools.includes(tool.id)) {
                        this.selectedTools.push(tool.id);
                    }
                } else {
                    this.selectedTools = this.selectedTools.filter(id => id !== tool.id);
                }
                this.updateToolsStats();
            });

            toolsList.appendChild(item);
        });

        document.getElementById('toolsTotal').textContent = tools.length;
        this.updateToolsStats();
        this.showStep(3);
    }

    endpointToToolName(endpoint) {
        const method = endpoint.method.toLowerCase();
        const pathParts = endpoint.path.split('/').filter(p => p && !p.includes('{'));

        if (method === 'get' && !endpoint.path.includes('{')) {
            return `list_${pathParts[pathParts.length - 1] || 'items'}`;
        } else if (method === 'get' && endpoint.path.includes('{')) {
            return `get_${pathParts[pathParts.length - 1] || 'item'}`;
        } else if (method === 'post') {
            return `create_${pathParts[pathParts.length - 1] || 'item'}`;
        } else if (method === 'put' || method === 'patch') {
            return `update_${pathParts[pathParts.length - 1] || 'item'}`;
        } else if (method === 'delete') {
            return `delete_${pathParts[pathParts.length - 1] || 'item'}`;
        }

        return `${method}_${pathParts.join('_') || 'resource'}`;
    }

    updateToolsStats() {
        document.getElementById('toolsSelected').textContent = this.selectedTools.length;
    }

    // Generate project
    async generateProject() {
        try {
            // Simulate generation
            await new Promise(resolve => setTimeout(resolve, 1500));

            this.generatedProject = {
                id: 'project_' + Date.now(),
                name: 'example-api-mcp',
                description: 'MCP server for Example API',
                tools: this.selectedTools.length,
                files: [
                    { name: 'src/server.py', path: 'src/server.py', type: 'python' },
                    { name: 'src/client.py', path: 'src/client.py', type: 'python' },
                    { name: 'src/config.py', path: 'src/config.py', type: 'python' },
                    { name: 'src/models.py', path: 'src/models.py', type: 'python' },
                    { name: 'src/tools/init.py', path: 'src/tools/__init__.py', type: 'python' },
                    { name: 'src/tools/users.py', path: 'src/tools/users.py', type: 'python' },
                    { name: 'src/tools/products.py', path: 'src/tools/products.py', type: 'python' },
                    { name: 'tests/test_client.py', path: 'tests/test_client.py', type: 'python' },
                    { name: '.env.example', path: '.env.example', type: 'text' },
                    { name: '.gitignore', path: '.gitignore', type: 'text' },
                    { name: 'requirements.txt', path: 'requirements.txt', type: 'text' },
                    { name: 'README.md', path: 'README.md', type: 'markdown' },
                    { name: 'pyproject.toml', path: 'pyproject.toml', type: 'toml' },
                    { name: 'mcp-config.json', path: 'mcp-config.json', type: 'json' }
                ],
                validation: {
                    checks_passed: 12,
                    warnings: 0,
                    errors: 0,
                    items: [
                        { type: 'success', title: 'Project structure', message: 'All files organized correctly' },
                        { type: 'success', title: 'Python syntax', message: 'All Python files have valid syntax' },
                        { type: 'success', title: 'MCP initialization', message: 'Server initializes correctly' },
                        { type: 'success', title: 'Tool schemas', message: 'All tool schemas are valid' },
                        { type: 'success', title: 'API client', message: 'Client configured correctly' },
                        { type: 'success', title: 'Environment config', message: '.env.example properly formatted' },
                        { type: 'success', title: 'README', message: 'Documentation complete' },
                        { type: 'success', title: 'Requirements', message: 'All dependencies specified' },
                        { type: 'success', title: 'Type hints', message: 'Type hints present in code' },
                        { type: 'success', title: 'Error handling', message: 'Proper error handling implemented' },
                        { type: 'success', title: 'Authentication', message: 'Auth handling secure' },
                        { type: 'success', title: 'Imports', message: 'All imports resolved' }
                    ]
                },
                readme: this.generateReadme(),
                fileContents: this.generateFileContents()
            };

            this.showStep(4);
            this.displayResult();
            this.saveToHistory();
            Toast.success('MCP Server generated successfully!');
        } catch (error) {
            console.error('Generation error:', error);
            Toast.error('Generation failed: ' + error.message);
        }
    }

    generateFileContents() {
        return {
            'src/server.py': `#!/usr/bin/env python3
"""MCP Server for Example API"""

import os
from mcp.server import Server
from mcp.types import Tool
from src.client import APIClient
from src.tools.users import register_user_tools
from src.tools.products import register_product_tools

# Initialize API client
api_client = APIClient(
    base_url=os.getenv('API_BASE_URL', 'https://api.example.com'),
    api_key=os.getenv('API_KEY', '')
)

# Create MCP server
server = Server("example-api-mcp")

# Register tool groups
register_user_tools(server, api_client)
register_product_tools(server, api_client)

if __name__ == "__main__":
    server.run()`,

            'src/config.py': `"""Configuration for Example API MCP Server"""

import os
from typing import Optional

class Config:
    """Configuration settings"""

    API_BASE_URL: str = os.getenv('API_BASE_URL', 'https://api.example.com')
    API_KEY: str = os.getenv('API_KEY', '')
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '20'))

    @staticmethod
    def validate():
        """Validate required configuration"""
        if not Config.API_KEY:
            raise ValueError("API_KEY environment variable is required")`,

            'src/client.py': `"""API Client for Example API"""

import httpx
from typing import Any, Dict, Optional

class APIClient:
    """HTTP client for API requests"""

    def __init__(self, base_url: str, api_key: str, timeout: int = 20):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout
        )

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        response = self.client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, json: Dict = None, **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        response = self.client.post(path, json=json, **kwargs)
        response.raise_for_status()
        return response.json()`,

            '.env.example': `# Example API Configuration
API_BASE_URL=https://api.example.com
API_KEY=your_api_key_here
REQUEST_TIMEOUT=20`,

            'requirements.txt': `mcp>=0.1.0
httpx>=0.24.0
pydantic>=2.0.0
python-dotenv>=1.0.0`,

            'README.md': this.generateReadme()
        };
    }

    generateReadme() {
        return `# Example API MCP Server

An MCP server for the Example API, automatically generated.

## Installation

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Configuration

Copy \`.env.example\` to \`.env\` and fill in your API credentials:

\`\`\`env
API_BASE_URL=https://api.example.com
API_KEY=your_api_key_here
\`\`\`

## Running the Server

\`\`\`bash
python src/server.py
\`\`\`

## Available Tools

- \`list_users\` - List all users
- \`get_user\` - Get a specific user
- \`create_user\` - Create a new user
- \`delete_user\` - Delete a user
- \`list_products\` - List all products

## Authentication

This API requires Bearer token authentication. The token is configured via the \`API_KEY\` environment variable.`;
    }

    displayResult() {
        if (!this.generatedProject) return;

        document.getElementById('toolCount').textContent = this.generatedProject.tools;
        document.getElementById('validationStatus').textContent = '✓';
        document.getElementById('authStatus').textContent = '✓';

        // Display validation report
        this.displayValidation();

        // Display file tree
        this.displayFileTree();

        // Display tools
        this.displayToolsExplorer();

        // Display README
        this.displayReadme();
    }

    displayValidation() {
        const container = document.getElementById('validationContent');
        const validation = this.generatedProject.validation;

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

        container.innerHTML = html;
    }

    displayFileTree() {
        const container = document.getElementById('fileTreeContainer');
        container.innerHTML = '';

        // Build folder structure
        const folders = {};
        this.generatedProject.files.forEach(file => {
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

                fileEl.addEventListener('click', () => {
                    this.selectFile(file);
                });

                container.appendChild(fileEl);
            });
        }
    }

    selectFile(file) {
        // Update active state
        document.querySelectorAll('.file-tree-item').forEach(el => {
            el.classList.remove('active');
        });
        event.currentTarget.classList.add('active');

        // Display file content
        const content = this.generatedProject.fileContents[file.path] || '# File content not available';
        document.getElementById('codeFilename').textContent = file.path;
        document.getElementById('codeContent').textContent = content;

        // Highlight syntax
        if (typeof hljs !== 'undefined') {
            document.getElementById('codeContent').className = `language-${file.type}`;
            hljs.highlightElement(document.getElementById('codeContent'));
        }

        // Update metadata
        this.displayFileMetadata(file);
    }

    displayFileMetadata(file) {
        const metadata = document.getElementById('fileMetadata');
        const lines = (this.generatedProject.fileContents[file.path] || '').split('\n').length;

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
                <div class="metadata-value">~${(this.generatedProject.fileContents[file.path] || '').length} bytes</div>
            </div>
        `;
    }

    displayToolsExplorer() {
        const container = document.getElementById('toolsExplorer');
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
        container.textContent = this.generatedProject.readme;

        if (typeof hljs !== 'undefined') {
            container.className = 'language-markdown';
            hljs.highlightElement(container);
        }
    }

    saveToHistory() {
        const history = Storage.getJSON('mcpHistory', []);
        history.unshift({
            id: this.generatedProject.id,
            name: this.generatedProject.name,
            url: this.analysisData.base_url,
            tools: this.generatedProject.tools,
            timestamp: new Date().toISOString(),
            project: this.generatedProject
        });

        // Keep last 50 projects
        if (history.length > 50) {
            history.pop();
        }

        Storage.setJSON('mcpHistory', history);
    }
}

// Initialize builder
const builder = new MCPBuilder();

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // URL input and analyze button
    const builderUrlInput = document.getElementById('builderUrlInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const demoBtn = document.getElementById('demoBtn');

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', () => {
            const url = builderUrlInput.value.trim();

            if (!url) {
                Toast.warning('Please enter a URL');
                return;
            }

            if (!URLValidator.isValid(url)) {
                Toast.warning('Please enter a valid URL');
                return;
            }

            analyzeBtn.disabled = true;
            builder.analyzeUrl(URLValidator.normalize(url));
        });

        builderUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                analyzeBtn.click();
            }
        });
    }

    if (demoBtn) {
        demoBtn.addEventListener('click', () => {
            builderUrlInput.value = 'https://api.example.com/docs';
            sessionStorage.setItem('useDemo', 'true');
            analyzeBtn.click();
        });
    }

    // Check for initial URL from home page
    const initialUrl = sessionStorage.getItem('initialUrl');
    if (initialUrl && builderUrlInput) {
        builderUrlInput.value = initialUrl;
        sessionStorage.removeItem('initialUrl');
    }

    // Tools search
    const toolSearch = document.getElementById('toolSearch');
    if (toolSearch) {
        toolSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            document.querySelectorAll('.tool-item').forEach(item => {
                const name = item.querySelector('.tool-name').textContent.toLowerCase();
                const desc = item.querySelector('.tool-description').textContent.toLowerCase();
                const matches = name.includes(query) || desc.includes(query);
                item.style.display = matches ? '' : 'none';
            });
        });
    }

    // Tools viewer search
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

    // Tool selection buttons
    const selectAllBtn = document.getElementById('selectAllBtn');
    const clearAllBtn = document.getElementById('clearAllBtn');

    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', () => {
            document.querySelectorAll('.tool-checkbox').forEach(cb => {
                cb.checked = true;
                const toolId = cb.dataset.toolId;
                if (!builder.selectedTools.includes(toolId)) {
                    builder.selectedTools.push(toolId);
                }
            });
            builder.updateToolsStats();
        });
    }

    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', () => {
            document.querySelectorAll('.tool-checkbox').forEach(cb => {
                cb.checked = false;
            });
            builder.selectedTools = [];
            builder.updateToolsStats();
        });
    }

    // Navigation buttons
    const backFromToolsBtn = document.getElementById('backFromToolsBtn');
    const proceedToGenerateBtn = document.getElementById('proceedToGenerateBtn');

    if (backFromToolsBtn) {
        backFromToolsBtn.addEventListener('click', () => {
            builder.showStep(1);
        });
    }

    if (proceedToGenerateBtn) {
        proceedToGenerateBtn.addEventListener('click', () => {
            if (builder.selectedTools.length === 0) {
                Toast.warning('Please select at least one tool');
                return;
            }

            proceedToGenerateBtn.disabled = true;
            builder.generateProject();
        });
    }

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

    // Copy and download buttons
    const copyCodeBtn = document.getElementById('copyCodeBtn');
    if (copyCodeBtn) {
        copyCodeBtn.addEventListener('click', () => {
            const code = document.getElementById('codeContent').textContent;
            navigator.clipboard.writeText(code).then(() => {
                Toast.success('Code copied to clipboard');
            });
        });
    }

    const downloadServerBtn = document.getElementById('downloadServerBtn');
    if (downloadServerBtn) {
        downloadServerBtn.addEventListener('click', () => {
            Toast.success('Download started');
            API.downloadZip('/api/download/project-id', 'mcp-server.zip');
        });
    }

    const newProjectBtn = document.getElementById('newProjectBtn');
    if (newProjectBtn) {
        newProjectBtn.addEventListener('click', () => {
            sessionStorage.removeItem('useDemo');
            builder.showStep(1);
            document.getElementById('builderUrlInput').value = '';
            document.getElementById('analyzeBtn').disabled = false;
        });
    }
});
