"""Analyze and normalize API representations."""
from typing import Dict, List

from app.models.api import APIRepresentation, Endpoint


class APIAnalyzer:
    """Analyze and provide insights about discovered APIs."""

    @staticmethod
    def analyze(api: APIRepresentation) -> Dict:
        """
        Analyze API and return insights.

        Returns:
            Dictionary with analysis results
        """
        return {
            "name": api.name,
            "description": api.description,
            "version": api.version,
            "base_url": api.base_url,
            "endpoint_count": len(api.endpoints),
            "endpoints": [
                APIAnalyzer._endpoint_summary(e) for e in api.endpoints
            ],
            "authentication": {
                "required": api.authentication_required,
                "type": api.authentication_type,
                "schemes": list(api.security_schemes.keys()),
            },
            "tags": api.tags,
            "methods": APIAnalyzer._get_methods_summary(api.endpoints),
        }

    @staticmethod
    def _endpoint_summary(endpoint: Endpoint) -> Dict:
        """Summarize single endpoint."""
        return {
            "path": endpoint.path,
            "method": endpoint.method,
            "summary": endpoint.summary or endpoint.description or "No description",
            "parameters_count": len(endpoint.parameters),
            "requires_body": endpoint.request_body is not None,
            "has_responses": len(endpoint.responses) > 0,
        }

    @staticmethod
    def _get_methods_summary(endpoints: List[Endpoint]) -> Dict[str, int]:
        """Count endpoints by HTTP method."""
        methods = {}
        for endpoint in endpoints:
            methods[endpoint.method] = methods.get(endpoint.method, 0) + 1
        return methods

    @staticmethod
    def filter_endpoints(
        api: APIRepresentation,
        method: str = None,
        tag: str = None,
        search: str = None,
    ) -> List[Endpoint]:
        """
        Filter endpoints by criteria.

        Args:
            api: APIRepresentation to filter
            method: Filter by HTTP method (e.g., "GET")
            tag: Filter by tag
            search: Search in path, summary, description

        Returns:
            Filtered list of endpoints
        """
        endpoints = api.endpoints

        if method:
            endpoints = [e for e in endpoints if e.method == method.upper()]

        if tag:
            endpoints = [e for e in endpoints if tag in e.tags]

        if search:
            search_lower = search.lower()
            endpoints = [
                e for e in endpoints
                if (
                    search_lower in e.path.lower() or
                    (e.summary and search_lower in e.summary.lower()) or
                    (e.description and search_lower in e.description.lower())
                )
            ]

        return endpoints

    @staticmethod
    def suggest_tool_endpoints(api: APIRepresentation, max_tools: int = 10) -> List[Endpoint]:
        """
        Suggest endpoints that would make good MCP tools.

        Prioritizes:
        - GET endpoints (data retrieval)
        - Endpoints with clear summaries
        - Non-authentication endpoints
        - Endpoints from core tags
        """
        # Sort by quality
        ranked = []

        for endpoint in api.endpoints:
            score = 0

            # Method score
            if endpoint.method == "GET":
                score += 3
            elif endpoint.method in ["POST", "PUT", "PATCH"]:
                score += 2
            else:
                score += 1

            # Summary quality
            if endpoint.summary:
                score += 2
            elif endpoint.description:
                score += 1

            # Path relevance (exclude auth, login, etc.)
            path_lower = endpoint.path.lower()
            if any(x in path_lower for x in ["auth", "login", "token", "key"]):
                score -= 5

            # Tag relevance
            if endpoint.tags:
                score += 1

            ranked.append((score, endpoint))

        # Sort by score descending
        ranked.sort(key=lambda x: x[0], reverse=True)

        # Return top endpoints
        return [e for _, e in ranked[:max_tools]]
