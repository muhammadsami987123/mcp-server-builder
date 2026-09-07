"""Project management and file generation."""
import io
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.models.mcp import MCPServerDesign

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages MCP server projects."""

    @staticmethod
    def create_zip(files: Dict[str, str], project_name: str) -> io.BytesIO:
        """Create a ZIP file from project files."""
        logger.info(f"Creating ZIP for project: {project_name}")

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath, content in files.items():
                # Add file to ZIP
                zf.writestr(filepath, content)

            # Add a MANIFEST file with metadata
            manifest = {
                "project_name": project_name,
                "generated_at": datetime.utcnow().isoformat(),
                "generator": "MCP Server Builder",
                "files_count": len(files),
            }
            zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))

        zip_buffer.seek(0)
        logger.info(f"ZIP created successfully: {project_name} ({zip_buffer.getbuffer().nbytes} bytes)")

        return zip_buffer

    @staticmethod
    def save_project_locally(
        files: Dict[str, str],
        base_path: Path,
        project_name: str
    ) -> Path:
        """Save project files to local filesystem."""
        project_dir = base_path / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        for filepath, content in files.items():
            file_path = project_dir / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        logger.info(f"Project saved to {project_dir}")
        return project_dir

    @staticmethod
    def create_project_metadata(
        design: MCPServerDesign,
        files: Dict[str, str],
        validation_result: Optional[Dict] = None
    ) -> Dict:
        """Create project metadata."""
        return {
            "server_name": design.server_name,
            "server_description": design.server_description,
            "version": design.version,
            "api_base_url": design.api_base_url,
            "source_api_name": design.source_api_name,
            "tools_count": len(design.tools),
            "files_count": len(files),
            "generated_at": datetime.utcnow().isoformat(),
            "authentication": {
                "required": design.authentication_config is not None,
                "type": design.authentication_config.get("type") if design.authentication_config else None,
            },
            "validation": validation_result or {},
        }

    @staticmethod
    def list_files_in_zip(zip_buffer: io.BytesIO) -> List[Dict]:
        """List all files in a ZIP buffer."""
        files_info = []

        with zipfile.ZipFile(zip_buffer, "r") as zf:
            for info in zf.filelist:
                files_info.append({
                    "name": info.filename,
                    "size": info.file_size,
                    "compressed_size": info.compress_size,
                })

        return files_info

    @staticmethod
    def extract_file_from_zip(zip_buffer: io.BytesIO, filepath: str) -> str:
        """Extract a single file from ZIP."""
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            return zf.read(filepath).decode("utf-8")

    @staticmethod
    def merge_files(
        base_files: Dict[str, str],
        additional_files: Dict[str, str]
    ) -> Dict[str, str]:
        """Merge two file dictionaries."""
        result = base_files.copy()
        result.update(additional_files)
        return result

    @staticmethod
    def get_file_tree(files: Dict[str, str]) -> Dict:
        """Create a tree structure of files."""
        tree = {}

        for filepath in sorted(files.keys()):
            parts = filepath.split("/")
            current = tree

            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Add file
            filename = parts[-1]
            current[filename] = {"type": "file", "size": len(files[filepath])}

        return tree

    @staticmethod
    def count_lines_of_code(files: Dict[str, str]) -> Dict[str, int]:
        """Count lines of code in generated files."""
        counts = {
            "total": 0,
            "python": 0,
            "markdown": 0,
            "json": 0,
            "yaml": 0,
            "text": 0,
        }

        for filepath, content in files.items():
            lines = len(content.split("\n"))
            counts["total"] += lines

            if filepath.endswith(".py"):
                counts["python"] += lines
            elif filepath.endswith(".md"):
                counts["markdown"] += lines
            elif filepath.endswith(".json"):
                counts["json"] += lines
            elif filepath.endswith((".yaml", ".yml")):
                counts["yaml"] += lines
            else:
                counts["text"] += lines

        return counts

    @staticmethod
    def validate_file_structure(files: Dict[str, str]) -> List[str]:
        """Validate that file structure makes sense."""
        issues = []

        # Check for duplicate files
        seen = set()
        for filepath in files:
            if filepath in seen:
                issues.append(f"Duplicate file: {filepath}")
            seen.add(filepath)

        # Check for required files
        required = ["src/server.py", "requirements.txt", "README.md"]
        for required_file in required:
            if required_file not in files:
                issues.append(f"Missing required file: {required_file}")

        # Check for empty critical files
        critical_files = ["src/server.py", "src/config.py", "requirements.txt"]
        for filepath in critical_files:
            if filepath in files:
                if not files[filepath].strip():
                    issues.append(f"Empty critical file: {filepath}")

        return issues
