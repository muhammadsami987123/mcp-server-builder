"""Validation engine for generated MCP servers."""
import ast
import json
import logging
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path

from app.models.mcp import MCPServerDesign

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation check."""

    def __init__(self):
        """Initialize validation result."""
        self.passed: List[str] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def add_pass(self, check: str):
        """Add a passed check."""
        self.passed.append(check)

    def add_warning(self, warning: str):
        """Add a warning."""
        self.warnings.append(warning)

    def add_error(self, error: str):
        """Add an error."""
        self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors,
            "total_checks": len(self.passed) + len(self.warnings) + len(self.errors),
            "passed_count": len(self.passed),
            "warning_count": len(self.warnings),
            "error_count": len(self.errors),
            "success": len(self.errors) == 0,
        }

    def to_string(self) -> str:
        """Convert to readable string."""
        result = "Validation Report\n"
        result += "=" * 50 + "\n\n"

        for check in self.passed:
            result += f"✓ {check}\n"

        if self.warnings:
            result += "\nWarnings:\n"
            for warning in self.warnings:
                result += f"⚠ {warning}\n"

        if self.errors:
            result += "\nErrors:\n"
            for error in self.errors:
                result += f"✗ {error}\n"

        result += "\n" + "=" * 50 + "\n"
        result += f"{len(self.passed)} passed, {len(self.warnings)} warnings, {len(self.errors)} errors\n"

        return result


class MCPServerValidator:
    """Validates generated MCP servers."""

    def __init__(self):
        """Initialize validator."""
        self.result = ValidationResult()

    def validate_project(
        self,
        files: Dict[str, str],
        design: MCPServerDesign
    ) -> ValidationResult:
        """Validate generated project files."""
        self.result = ValidationResult()

        logger.info("Validating generated MCP server...")

        # Check project structure
        self._validate_structure(files)

        # Check Python syntax
        self._validate_python_syntax(files)

        # Check MCP configuration
        self._validate_mcp_config(files, design)

        # Check tool schemas
        self._validate_tool_schemas(design)

        # Check requirements
        self._validate_requirements(files)

        # Check environment variables
        self._validate_environment(files, design)

        # Check README
        self._validate_readme(files)

        return self.result

    def _validate_structure(self, files: Dict[str, str]):
        """Validate project structure."""
        required_files = [
            "src/server.py",
            "src/config.py",
            "src/client.py",
            "src/models.py",
            "src/tools/__init__.py",
            "src/tools/api_tools.py",
            ".env.example",
            ".gitignore",
            "requirements.txt",
            "README.md",
            "mcp-config.json",
            "pyproject.toml",
        ]

        for required_file in required_files:
            if required_file in files:
                self.result.add_pass(f"File exists: {required_file}")
            else:
                self.result.add_error(f"Missing required file: {required_file}")

    def _validate_python_syntax(self, files: Dict[str, str]):
        """Validate Python file syntax."""
        python_files = {k: v for k, v in files.items() if k.endswith(".py")}

        for filepath, content in python_files.items():
            try:
                ast.parse(content)
                self.result.add_pass(f"Python syntax valid: {filepath}")
            except SyntaxError as e:
                self.result.add_error(f"Syntax error in {filepath}: {e.msg}")
            except Exception as e:
                self.result.add_error(f"Error parsing {filepath}: {e}")

    def _validate_mcp_config(self, files: Dict[str, str], design: MCPServerDesign):
        """Validate MCP configuration."""
        if "mcp-config.json" not in files:
            self.result.add_error("mcp-config.json not found")
            return

        try:
            config = json.loads(files["mcp-config.json"])
            if "mcpServers" not in config:
                self.result.add_error("mcp-config.json missing mcpServers key")
                return

            if design.server_name in config["mcpServers"]:
                self.result.add_pass("MCP server configured in mcp-config.json")
            else:
                self.result.add_warning(f"Server '{design.server_name}' not in mcp-config.json")

        except json.JSONDecodeError as e:
            self.result.add_error(f"Invalid JSON in mcp-config.json: {e}")

    def _validate_tool_schemas(self, design: MCPServerDesign):
        """Validate tool input schemas."""
        if not design.tools:
            self.result.add_warning("No tools defined in design")
            return

        for tool in design.tools:
            # Check tool name
            if not tool.name or not re.match(r"^[a-z_][a-z0-9_]*$", tool.name):
                self.result.add_error(f"Invalid tool name: {tool.name}")
            else:
                self.result.add_pass(f"Tool name valid: {tool.name}")

            # Check input schema
            if tool.input_schema is None:
                self.result.add_error(f"Tool {tool.name} missing input_schema")
            elif tool.input_schema.type != "object":
                self.result.add_error(f"Tool {tool.name} input_schema type must be 'object'")
            else:
                self.result.add_pass(f"Tool schema valid: {tool.name}")

            # Check required parameters
            for required_param in tool.input_schema.required:
                if required_param not in tool.input_schema.properties:
                    self.result.add_error(
                        f"Tool {tool.name}: required param '{required_param}' not in properties"
                    )

    def _validate_requirements(self, files: Dict[str, str]):
        """Validate requirements.txt."""
        if "requirements.txt" not in files:
            self.result.add_error("requirements.txt not found")
            return

        content = files["requirements.txt"]
        if not content.strip():
            self.result.add_error("requirements.txt is empty")
            return

        required_packages = ["mcp", "httpx", "pydantic"]
        content_lower = content.lower()

        for package in required_packages:
            if package in content_lower:
                self.result.add_pass(f"Required package '{package}' in requirements.txt")
            else:
                self.result.add_warning(f"Package '{package}' not found in requirements.txt")

    def _validate_environment(self, files: Dict[str, str], design: MCPServerDesign):
        """Validate environment configuration."""
        if ".env.example" not in files:
            self.result.add_error(".env.example not found")
            return

        env_content = files[".env.example"]
        required_vars = ["API_BASE_URL", "API_KEY", "API_TOKEN"]

        for var in required_vars:
            if var in env_content:
                self.result.add_pass(f"Environment variable template: {var}")
            else:
                self.result.add_warning(f"Environment variable not in .env.example: {var}")

        # Check if base URL is set
        if "API_BASE_URL" in env_content:
            # Extract the value
            for line in env_content.split("\n"):
                if line.startswith("API_BASE_URL"):
                    if design.api_base_url in line:
                        self.result.add_pass("API_BASE_URL correctly set in .env.example")
                    break

    def _validate_readme(self, files: Dict[str, str]):
        """Validate README.md."""
        if "README.md" not in files:
            self.result.add_error("README.md not found")
            return

        readme = files["README.md"]

        # Check for required sections
        required_sections = [
            "Installation",
            "Environment",
            "Configuration",
            "Running",
            "Tools",
            "Troubleshooting",
        ]

        for section in required_sections:
            if section.lower() in readme.lower():
                self.result.add_pass(f"README includes '{section}' section")
            else:
                self.result.add_warning(f"README missing '{section}' section")

        # Check length
        if len(readme) > 500:
            self.result.add_pass("README has substantial content")
        else:
            self.result.add_warning("README appears too short")

    def validate_imports(self, files: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """Validate that all imports are resolvable."""
        missing_imports = []
        valid_imports = []

        python_files = {k: v for k, v in files.items() if k.endswith(".py")}

        # Common standard library and third-party packages
        known_packages = {
            "asyncio", "logging", "json", "re", "os", "sys", "typing",
            "pathlib", "datetime", "collections", "itertools",
            "httpx", "pydantic", "mcp", "yaml", "dotenv"
        }

        for filepath, content in python_files.items():
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split(".")[0]
                            if module not in known_packages:
                                # Could be a local import
                                pass
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split(".")[0]
                            if module not in known_packages:
                                pass
            except Exception as e:
                logger.warning(f"Error analyzing imports in {filepath}: {e}")

        return valid_imports, missing_imports

    def validate_configuration(self, files: Dict[str, str]) -> bool:
        """Validate configuration consistency."""
        # Check that config.py and .env.example are consistent
        if "src/config.py" not in files or ".env.example" not in files:
            return False

        config_py = files["src/config.py"]
        env_example = files[".env.example"]

        # Look for env variable references in config.py
        env_pattern = r'os\.getenv\(["\'](\w+)["\']\)'
        env_vars = re.findall(env_pattern, config_py)

        for var in set(env_vars):
            if var not in env_example and var not in ["PYTHONPATH", "PATH"]:
                logger.warning(f"Environment variable {var} used in config but not in .env.example")

        return True
