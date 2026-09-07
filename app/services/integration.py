"""Integration service that orchestrates the entire MCP generation pipeline."""
import io
import json
import logging
from typing import Dict, Optional, Tuple

from app.models.api import APIRepresentation
from app.models.mcp import MCPServerDesign, MCPProject
from app.services.mcp_designer import MCPDesigner
from app.services.mcp_generator import MCPServerGenerator
from app.services.validator import MCPServerValidator
from app.services.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class MCPGenerationPipeline:
    """Orchestrates the complete MCP generation pipeline."""

    def __init__(self):
        """Initialize the pipeline."""
        self.designer = MCPDesigner()
        self.generator = MCPServerGenerator()
        self.validator = MCPServerValidator()
        self.project_manager = ProjectManager()

    def generate_complete_project(
        self,
        api: APIRepresentation,
        api_discovery_report: Optional[Dict] = None
    ) -> Tuple[MCPServerDesign, Dict[str, str], Dict]:
        """
        Generate a complete MCP server project from an API.

        Args:
            api: Normalized API representation
            api_discovery_report: Raw discovery report for metadata

        Returns:
            Tuple of (MCPServerDesign, files_dict, validation_result)
        """
        logger.info(f"Starting MCP generation pipeline for {api.name}")

        # Step 1: Design MCP tools
        logger.info("Step 1: Designing MCP tools...")
        design = self.designer.design_tools(api)

        # Step 2: Generate server files
        logger.info("Step 2: Generating server files...")
        files = self.generator.generate_project(design)

        # Step 3: Validate generated project
        logger.info("Step 3: Validating generated project...")
        validation_result = self.validator.validate_project(files, design)

        logger.info("MCP generation pipeline completed")

        return design, files, validation_result.to_dict()

    def create_download_zip(
        self,
        files: Dict[str, str],
        project_name: str
    ) -> io.BytesIO:
        """
        Create a downloadable ZIP file.

        Args:
            files: Generated project files
            project_name: Name for the ZIP

        Returns:
            BytesIO buffer containing the ZIP
        """
        return self.project_manager.create_zip(files, project_name)

    def get_project_summary(
        self,
        design: MCPServerDesign,
        files: Dict[str, str],
        validation_result: Dict
    ) -> Dict:
        """
        Create a summary of the generated project.

        Args:
            design: MCPServerDesign
            files: Generated files
            validation_result: Validation report

        Returns:
            Project summary dictionary
        """
        loc = self.project_manager.count_lines_of_code(files)
        file_tree = self.project_manager.get_file_tree(files)
        file_issues = self.project_manager.validate_file_structure(files)

        return {
            "project_name": design.server_name,
            "description": design.server_description,
            "version": design.version,
            "source_api": design.source_api_name,
            "api_base_url": design.api_base_url,
            "tools": {
                "total": len(design.tools),
                "by_category": self._count_tools_by_category(design),
                "list": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "method": t.method,
                        "path": t.path,
                        "category": t.category,
                    }
                    for t in design.tools
                ]
            },
            "files": {
                "total_files": len(files),
                "lines_of_code": loc,
                "tree": file_tree,
                "issues": file_issues,
            },
            "validation": validation_result,
            "download": {
                "format": "zip",
                "recommended_filename": f"{design.server_name}.zip",
            },
        }

    @staticmethod
    def _count_tools_by_category(design: MCPServerDesign) -> Dict[str, int]:
        """Count tools by category."""
        categories = {}
        for tool in design.tools:
            category = tool.category or "uncategorized"
            categories[category] = categories.get(category, 0) + 1
        return categories

    def get_tool_documentation(self, design: MCPServerDesign) -> str:
        """
        Generate tool documentation in Markdown format.

        Args:
            design: MCPServerDesign

        Returns:
            Markdown documentation string
        """
        doc = f"# {design.server_name} - Tools Documentation\n\n"
        doc += f"{design.server_description}\n\n"
        doc += f"**Total Tools:** {len(design.tools)}\n\n"

        # Group by category
        categories = {}
        for tool in design.tools:
            cat = tool.category or "Other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tool)

        for category, tools in sorted(categories.items()):
            doc += f"## {category.replace('_', ' ').title()}\n\n"

            for tool in tools:
                doc += f"### `{tool.name}`\n"
                doc += f"{tool.description}\n\n"
                doc += f"**HTTP:** `{tool.method} {tool.path}`\n\n"

                if tool.input_schema.properties:
                    doc += "**Parameters:**\n\n"
                    for param_name, param_schema in tool.input_schema.properties.items():
                        required = "✓" if param_name in tool.input_schema.required else "○"
                        doc += f"- `{param_name}` ({param_schema.get('type', 'unknown')}) [{required}] - {param_schema.get('description', 'No description')}\n"
                    doc += "\n"

        return doc

    def create_project_metadata(
        self,
        design: MCPServerDesign,
        files: Dict[str, str],
        api_discovery_report: Optional[Dict] = None
    ) -> MCPProject:
        """
        Create a complete MCPProject object.

        Args:
            design: MCPServerDesign
            files: Generated files
            api_discovery_report: API discovery report

        Returns:
            MCPProject object
        """
        import uuid
        from datetime import datetime

        validation = self.validator.validate_project(files, design)

        return MCPProject(
            project_id=str(uuid.uuid4()),
            name=design.server_name,
            description=design.server_description,
            source_url=design.api_base_url,
            source_api_name=design.source_api_name,
            created_at=datetime.utcnow().isoformat(),
            discovery_report=api_discovery_report or {},
            design=design,
            generated_files=[
                {
                    "path": path,
                    "content": content,
                    "file_type": "text",
                }
                for path, content in files.items()
            ],
            status="completed",
            error_message=None,
        )

    def regenerate_with_options(
        self,
        api: APIRepresentation,
        design: MCPServerDesign,
        options: Dict
    ) -> Tuple[MCPServerDesign, Dict[str, str], Dict]:
        """
        Regenerate with user options.

        Args:
            api: Original API representation
            design: Original design
            options: Regeneration options (tool selection, naming style, etc.)

        Returns:
            Updated design, files, and validation result
        """
        logger.info("Regenerating with custom options...")

        # Apply options to design
        if "selected_tools" in options:
            # Filter tools
            tool_names = set(options["selected_tools"])
            design.tools = [t for t in design.tools if t.name in tool_names]

        if "server_name" in options:
            design.server_name = options["server_name"]

        if "server_description" in options:
            design.server_description = options["server_description"]

        # Regenerate files
        files = self.generator.generate_project(design)

        # Revalidate
        validation_result = self.validator.validate_project(files, design)

        return design, files, validation_result.to_dict()


class GenerationStatus:
    """Track generation progress."""

    def __init__(self):
        """Initialize status tracker."""
        self.stages = {
            "api_discovery": {"status": "pending", "message": ""},
            "api_analysis": {"status": "pending", "message": ""},
            "tool_design": {"status": "pending", "message": ""},
            "code_generation": {"status": "pending", "message": ""},
            "validation": {"status": "pending", "message": ""},
        }

    def update(self, stage: str, status: str, message: str = ""):
        """Update stage status."""
        if stage in self.stages:
            self.stages[stage]["status"] = status
            self.stages[stage]["message"] = message
            logger.info(f"Stage {stage}: {status} - {message}")

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return self.stages

    def is_complete(self) -> bool:
        """Check if all stages are complete."""
        return all(s["status"] in ["completed", "skipped"] for s in self.stages.values())

    def has_errors(self) -> bool:
        """Check if any stage has errors."""
        return any(s["status"] == "error" for s in self.stages.values())
