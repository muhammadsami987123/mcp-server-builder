"""Static validation of a GeneratedMCPServer -- no generated code is ever executed."""

from __future__ import annotations

import ast
import re

from app.models.mcp import GeneratedMCPServer, ValidationCheck, ValidationResult

_REQUIRED_FILES = (
    "src/server.py",
    "src/config.py",
    "src/client.py",
    "requirements.txt",
    ".env.example",
)

_ENV_VAR_PATTERN = re.compile(r"os\.(?:environ\.get|getenv)\(\s*['\"]([A-Z0-9_]+)['\"]")


def _file_map(server: GeneratedMCPServer) -> dict[str, str]:
    return {f.path: f.content for f in server.files}


def _check_required_files(files: dict[str, str]) -> list[ValidationCheck]:
    checks = []
    for path in _REQUIRED_FILES:
        present = path in files
        checks.append(
            ValidationCheck(
                name=f"required_file:{path}",
                passed=present,
                message="present" if present else f"required file '{path}' is missing",
                severity="error",
            )
        )
    return checks


def _check_python_syntax(server: GeneratedMCPServer) -> list[ValidationCheck]:
    checks = []
    for f in server.files:
        if not f.path.endswith(".py"):
            continue
        try:
            ast.parse(f.content, filename=f.path)
        except SyntaxError as exc:
            checks.append(
                ValidationCheck(
                    name=f"python_syntax:{f.path}",
                    passed=False,
                    message=f"{f.path}: SyntaxError: {exc.msg} (line {exc.lineno})",
                    severity="error",
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name=f"python_syntax:{f.path}",
                    passed=True,
                    message="valid Python syntax",
                    severity="error",
                )
            )
    return checks


def _check_mcp_server_init(files: dict[str, str]) -> ValidationCheck:
    server_src = files.get("src/server.py", "")
    passed = "FastMCP(" in server_src
    return ValidationCheck(
        name="mcp_server_initialization",
        passed=passed,
        message="MCP server instantiated via FastMCP(...)" if passed else "src/server.py does not instantiate FastMCP",
        severity="error",
    )


def _check_tool_registration(files: dict[str, str]) -> ValidationCheck:
    combined = "\n".join(files.values())
    passed = "@mcp.tool(" in combined
    return ValidationCheck(
        name="mcp_tool_registration",
        passed=passed,
        message="at least one @mcp.tool() registration found" if passed else "no @mcp.tool() registration found in any file",
        severity="error",
    )


def _check_requirements(files: dict[str, str]) -> ValidationCheck:
    content = files.get("requirements.txt", "")
    non_empty = bool(content.strip())
    has_mcp = bool(re.search(r"(?m)^mcp\b", content))
    passed = non_empty and has_mcp
    if not non_empty:
        message = "requirements.txt is empty"
    elif not has_mcp:
        message = "requirements.txt does not include the 'mcp' package"
    else:
        message = "requirements.txt present and includes 'mcp'"
    return ValidationCheck(name="requirements_txt", passed=passed, message=message, severity="error")


def _check_env_vars(files: dict[str, str]) -> ValidationCheck:
    config_src = files.get("src/config.py", "")
    env_example = files.get(".env.example")
    needed = set(_ENV_VAR_PATTERN.findall(config_src))
    if env_example is None:
        # required-files check already reports this as an error; don't double-fail.
        return ValidationCheck(
            name="env_example_vars",
            passed=True,
            message="skipped: .env.example not present",
            severity="warning",
        )
    missing = sorted(v for v in needed if v not in env_example)
    passed = not missing
    message = "all referenced env vars documented in .env.example" if passed else (
        f".env.example is missing: {', '.join(missing)}"
    )
    return ValidationCheck(name="env_example_vars", passed=passed, message=message, severity="error")


def _check_input_schemas(files: dict[str, str], tool_count: int) -> ValidationCheck:
    models_src = files.get("src/models.py")
    if models_src is None:
        return ValidationCheck(
            name="tool_input_schemas",
            passed=True,
            message="skipped: src/models.py not present",
            severity="warning",
        )
    try:
        tree = ast.parse(models_src, filename="src/models.py")
    except SyntaxError:
        # already reported by the syntax check; don't double-report as a hard failure here.
        return ValidationCheck(
            name="tool_input_schemas",
            passed=False,
            message="src/models.py could not be parsed",
            severity="warning",
        )
    class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    passed = class_count > 0 or tool_count == 0
    message = (
        f"{class_count} tool input model(s) defined"
        if passed
        else "no Pydantic input models found in src/models.py"
    )
    return ValidationCheck(name="tool_input_schemas", passed=passed, message=message, severity="warning")


def _check_oauth_note(files: dict[str, str]) -> ValidationCheck | None:
    combined = "\n".join(files.values())
    if "oauth" not in combined.lower():
        return None
    return ValidationCheck(
        name="oauth_manual_credentials",
        passed=True,
        message="OAuth2 authentication detected -- this API requires manually obtained credentials/tokens",
        severity="warning",
    )


def validate_generated_server(server: GeneratedMCPServer) -> ValidationResult:
    files = _file_map(server)

    checks: list[ValidationCheck] = []
    checks.extend(_check_required_files(files))
    checks.extend(_check_python_syntax(server))
    checks.append(_check_mcp_server_init(files))
    checks.append(_check_tool_registration(files))
    checks.append(_check_requirements(files))
    checks.append(_check_env_vars(files))
    checks.append(_check_input_schemas(files, server.tool_count))

    oauth_check = _check_oauth_note(files)
    if oauth_check is not None:
        checks.append(oauth_check)

    errors = [c.message for c in checks if c.severity == "error" and not c.passed]
    warnings = [c.message for c in checks if c.severity == "warning" and not c.passed]
    passed = not errors

    return ValidationResult(passed=passed, checks=checks, errors=errors, warnings=warnings)
