"""Example API specifications and generated projects for demo purposes."""
from app.models.api import (
    APIRepresentation, Endpoint, Parameter, SecurityScheme, Response
)


def get_example_weather_api() -> APIRepresentation:
    """Get example weather API specification."""
    return APIRepresentation(
        name="OpenWeather API",
        description="Simple weather data API for demonstration",
        version="2.5",
        base_url="https://api.openweathermap.org/data/2.5",
        source_url="https://api.openweathermap.org/data/2.5",
        authentication_required=True,
        authentication_type="api_key",
        endpoints=[
            Endpoint(
                path="/weather",
                method="GET",
                summary="Get current weather",
                description="Get current weather data for a location",
                parameters=[
                    Parameter(name="q", in_="query", description="City name", required=True),
                    Parameter(name="units", in_="query", description="Temperature units (metric/imperial)", required=False),
                    Parameter(name="appid", in_="query", description="API key", required=True),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Successful response",
                        schema={
                            "type": "object",
                            "properties": {
                                "temp": {"type": "number"},
                                "feels_like": {"type": "number"},
                                "humidity": {"type": "integer"},
                            }
                        }
                    )
                ]
            ),
            Endpoint(
                path="/forecast",
                method="GET",
                summary="Get weather forecast",
                description="Get 5-day weather forecast",
                parameters=[
                    Parameter(name="q", in_="query", description="City name", required=True),
                    Parameter(name="cnt", in_="query", description="Number of forecasts", required=False),
                    Parameter(name="appid", in_="query", description="API key", required=True),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Successful response",
                        schema={"type": "object"}
                    )
                ]
            ),
        ],
        security_schemes={
            "api_key": SecurityScheme(
                type="apiKey",
                description="OpenWeather API key",
            )
        },
        tags={
            "weather": "Weather data endpoints",
            "forecast": "Forecast endpoints",
        }
    )


def get_example_github_api() -> APIRepresentation:
    """Get example GitHub API specification."""
    return APIRepresentation(
        name="GitHub API",
        description="GitHub REST API v3 (simplified example)",
        version="3.0",
        base_url="https://api.github.com",
        source_url="https://api.github.com",
        authentication_required=True,
        authentication_type="bearer",
        endpoints=[
            Endpoint(
                path="/users/{username}",
                method="GET",
                summary="Get user information",
                description="Get public profile information for a GitHub user",
                parameters=[
                    Parameter(name="username", in_="path", description="GitHub username", required=True),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="User object",
                        schema={
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "login": {"type": "string"},
                                "name": {"type": "string"},
                                "public_repos": {"type": "integer"},
                            }
                        }
                    )
                ]
            ),
            Endpoint(
                path="/users/{username}/repos",
                method="GET",
                summary="List user repositories",
                description="List all public repositories for a GitHub user",
                parameters=[
                    Parameter(name="username", in_="path", description="GitHub username", required=True),
                    Parameter(name="sort", in_="query", description="Sort by (created/updated/pushed/full_name)", required=False),
                    Parameter(name="per_page", in_="query", description="Results per page", required=False),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Array of repository objects",
                        schema={"type": "array"}
                    )
                ]
            ),
            Endpoint(
                path="/repos/{owner}/{repo}",
                method="GET",
                summary="Get repository information",
                description="Get information about a specific repository",
                parameters=[
                    Parameter(name="owner", in_="path", description="Repository owner", required=True),
                    Parameter(name="repo", in_="path", description="Repository name", required=True),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Repository object",
                        schema={"type": "object"}
                    )
                ]
            ),
            Endpoint(
                path="/repos/{owner}/{repo}/issues",
                method="GET",
                summary="List repository issues",
                description="List all issues in a repository",
                parameters=[
                    Parameter(name="owner", in_="path", description="Repository owner", required=True),
                    Parameter(name="repo", in_="path", description="Repository name", required=True),
                    Parameter(name="state", in_="query", description="Filter by state (open/closed/all)", required=False),
                    Parameter(name="per_page", in_="query", description="Results per page", required=False),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Array of issue objects",
                        schema={"type": "array"}
                    )
                ]
            ),
            Endpoint(
                path="/repos/{owner}/{repo}/issues/{issue_number}",
                method="GET",
                summary="Get issue details",
                description="Get detailed information about a specific issue",
                parameters=[
                    Parameter(name="owner", in_="path", description="Repository owner", required=True),
                    Parameter(name="repo", in_="path", description="Repository name", required=True),
                    Parameter(name="issue_number", in_="path", description="Issue number", required=True),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Issue object",
                        schema={"type": "object"}
                    )
                ]
            ),
        ],
        security_schemes={
            "bearer": SecurityScheme(
                type="http",
                scheme="bearer",
                description="GitHub personal access token",
            )
        },
        tags={
            "users": "User endpoints",
            "repos": "Repository endpoints",
            "issues": "Issue tracking endpoints",
        }
    )


def get_example_stripe_api() -> APIRepresentation:
    """Get example Stripe API specification."""
    return APIRepresentation(
        name="Stripe API",
        description="Stripe payment processing API (simplified example)",
        version="2023-08-16",
        base_url="https://api.stripe.com/v1",
        source_url="https://api.stripe.com/v1",
        authentication_required=True,
        authentication_type="api_key",
        endpoints=[
            Endpoint(
                path="/customers",
                method="GET",
                summary="List customers",
                description="Get a list of customers",
                parameters=[
                    Parameter(name="limit", in_="query", description="Number of results", required=False),
                    Parameter(name="starting_after", in_="query", description="Pagination cursor", required=False),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="List of customers",
                        schema={"type": "object"}
                    )
                ]
            ),
            Endpoint(
                path="/customers",
                method="POST",
                summary="Create customer",
                description="Create a new customer",
                parameters=[
                    Parameter(name="email", in_="formData", description="Customer email", required=False),
                    Parameter(name="name", in_="formData", description="Customer name", required=False),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Created customer",
                        schema={"type": "object"}
                    )
                ]
            ),
            Endpoint(
                path="/charges",
                method="GET",
                summary="List charges",
                description="Get a list of charges",
                parameters=[
                    Parameter(name="limit", in_="query", description="Number of results", required=False),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="List of charges",
                        schema={"type": "object"}
                    )
                ]
            ),
            Endpoint(
                path="/charges",
                method="POST",
                summary="Create charge",
                description="Create a new charge",
                parameters=[
                    Parameter(name="amount", in_="formData", description="Amount in cents", required=True),
                    Parameter(name="currency", in_="formData", description="Currency code", required=True),
                    Parameter(name="customer", in_="formData", description="Customer ID", required=False),
                ],
                responses=[
                    Response(
                        status_code="200",
                        description="Created charge",
                        schema={"type": "object"}
                    )
                ]
            ),
        ],
        security_schemes={
            "api_key": SecurityScheme(
                type="apiKey",
                description="Stripe API key (Bearer or Basic auth)",
            )
        },
        tags={
            "customers": "Customer management",
            "charges": "Payment charges",
        }
    )
