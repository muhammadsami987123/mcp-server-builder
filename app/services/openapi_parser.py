"""Parse OpenAPI/Swagger specifications."""
import json
from typing import Any, Dict, List, Optional

import yaml
from app.models.api import (
    APIRepresentation,
    Endpoint,
    Parameter,
    RequestBody,
    Response,
    SecurityScheme,
)


class OpenAPIParser:
    """Parse OpenAPI 3.0 and Swagger 2.0 specifications."""

    @staticmethod
    def parse_spec(
        spec_content: str,
        spec_type: str = "json",
        source_url: str = "",
    ) -> tuple[bool, Optional[APIRepresentation], Optional[Dict[str, Any]], List[str]]:
        """
        Parse OpenAPI/Swagger specification.

        Args:
            spec_content: Raw specification content
            spec_type: "json" or "yaml"
            source_url: URL where spec was found

        Returns:
            (success, APIRepresentation, raw_spec, errors)
        """
        errors = []

        # Parse spec content
        try:
            if spec_type == "yaml":
                spec = yaml.safe_load(spec_content)
            else:
                spec = json.loads(spec_content)

            if not spec or not isinstance(spec, dict):
                return False, None, None, ["Invalid specification: not a valid object"]

        except json.JSONDecodeError as e:
            return False, None, None, [f"JSON parsing error: {str(e)}"]
        except yaml.YAMLError as e:
            return False, None, None, [f"YAML parsing error: {str(e)}"]
        except Exception as e:
            return False, None, None, [f"Parsing error: {str(e)}"]

        # Detect version
        version = None
        if "openapi" in spec:
            version = "openapi3"
        elif "swagger" in spec:
            version = "swagger2"
        else:
            return False, None, spec, ["Cannot detect OpenAPI/Swagger version"]

        # Parse based on version
        try:
            if version == "openapi3":
                api = OpenAPIParser._parse_openapi3(spec, source_url)
            else:
                api = OpenAPIParser._parse_swagger2(spec, source_url)

            return True, api, spec, errors
        except Exception as e:
            errors.append(f"Parsing failed: {str(e)}")
            return False, None, spec, errors

    @staticmethod
    def _parse_openapi3(spec: Dict[str, Any], source_url: str) -> APIRepresentation:
        """Parse OpenAPI 3.0 specification."""
        info = spec.get("info", {})
        servers = spec.get("servers", [])

        # Extract base URL
        base_url = None
        if servers:
            base_url = servers[0].get("url", "")

        # Parse security schemes
        security_schemes = {}
        components = spec.get("components", {})
        if "securitySchemes" in components:
            for name, scheme in components["securitySchemes"].items():
                security_schemes[name] = SecurityScheme(**scheme)

        # Parse endpoints
        endpoints = []
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
                    continue

                # Parse parameters
                parameters = []
                for param in operation.get("parameters", []):
                    try:
                        parameters.append(Parameter(**param))
                    except Exception:
                        pass

                # Parse request body
                request_body = None
                if "requestBody" in operation:
                    try:
                        request_body = RequestBody(**operation["requestBody"])
                    except Exception:
                        pass

                # Parse responses
                responses = []
                for status_code, response_obj in operation.get("responses", {}).items():
                    try:
                        resp = Response(
                            status_code=status_code,
                            description=response_obj.get("description"),
                            content=response_obj.get("content"),
                        )
                        responses.append(resp)
                    except Exception:
                        pass

                endpoint = Endpoint(
                    path=path,
                    method=method.upper(),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    operation_id=operation.get("operationId"),
                    tags=operation.get("tags", []),
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses,
                    security=operation.get("security"),
                )
                endpoints.append(endpoint)

        # Check authentication requirement
        global_security = spec.get("security", [])
        auth_required = bool(global_security)
        auth_type = None

        if security_schemes:
            for name, scheme in security_schemes.items():
                if scheme.type == "http":
                    auth_type = scheme.scheme
                elif scheme.type == "apiKey":
                    auth_type = "api_key"
                elif scheme.type == "oauth2":
                    auth_type = "oauth2"
                elif scheme.type == "openIdConnect":
                    auth_type = "openid_connect"

        return APIRepresentation(
            name=info.get("title", "API"),
            description=info.get("description"),
            version=info.get("version"),
            base_url=base_url,
            source_url=source_url,
            endpoints=endpoints,
            security_schemes=security_schemes,
            tags={tag.get("name"): tag.get("description", "") for tag in spec.get("tags", [])},
            servers=servers,
            authentication_required=auth_required,
            authentication_type=auth_type,
        )

    @staticmethod
    def _parse_swagger2(spec: Dict[str, Any], source_url: str) -> APIRepresentation:
        """Parse Swagger 2.0 specification."""
        info = spec.get("info", {})

        # Extract base URL
        scheme = spec.get("schemes", ["https"])[0]
        host = spec.get("host", "")
        base_path = spec.get("basePath", "")
        base_url = f"{scheme}://{host}{base_path}" if host else None

        # Parse security schemes
        security_schemes = {}
        for name, scheme_obj in spec.get("securityDefinitions", {}).items():
            security_schemes[name] = SecurityScheme(**scheme_obj)

        # Parse endpoints
        endpoints = []
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
                    continue

                # Parse parameters
                parameters = []
                for param in operation.get("parameters", []):
                    try:
                        param_dict = dict(param)
                        param_dict["in"] = param_dict.pop("in")
                        parameters.append(Parameter(**param_dict))
                    except Exception:
                        pass

                # Parse request body from consumes and parameters
                request_body = None
                if operation.get("consumes"):
                    request_body = RequestBody(
                        description=None,
                        required=False,
                        content={
                            ct: {} for ct in operation["consumes"]
                        }
                    )

                # Parse responses
                responses = []
                for status_code, response_obj in operation.get("responses", {}).items():
                    try:
                        resp = Response(
                            status_code=status_code,
                            description=response_obj.get("description"),
                            schema=response_obj.get("schema"),
                        )
                        responses.append(resp)
                    except Exception:
                        pass

                endpoint = Endpoint(
                    path=path,
                    method=method.upper(),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    operation_id=operation.get("operationId"),
                    tags=operation.get("tags", []),
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses,
                    security=operation.get("security"),
                )
                endpoints.append(endpoint)

        # Check authentication
        global_security = spec.get("security", [])
        auth_required = bool(global_security)
        auth_type = None

        if security_schemes:
            for name, scheme in security_schemes.items():
                if scheme.type == "basic":
                    auth_type = "basic"
                elif scheme.type == "apiKey":
                    auth_type = "api_key"
                elif scheme.type == "oauth2":
                    auth_type = "oauth2"

        return APIRepresentation(
            name=info.get("title", "API"),
            description=info.get("description"),
            version=info.get("version"),
            base_url=base_url,
            source_url=source_url,
            endpoints=endpoints,
            security_schemes=security_schemes,
            tags={tag.get("name"): tag.get("description", "") for tag in spec.get("tags", [])},
            authentication_required=auth_required,
            authentication_type=auth_type,
        )
