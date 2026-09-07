"""Safe URL fetching with SSRF protection."""
import re
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx
from app.config import (
    BLOCKED_IP_PATTERNS,
    MAX_REDIRECTS,
    MAX_RESPONSE_SIZE,
    REQUEST_TIMEOUT,
)


class SSRFException(Exception):
    """Raised when SSRF protection blocks a request."""
    pass


class URLFetcher:
    """Safely fetch URLs with SSRF protection."""

    @staticmethod
    def _is_blocked_ip(ip: str) -> bool:
        """Check if IP is in blocked ranges."""
        for pattern in BLOCKED_IP_PATTERNS:
            if ip.startswith(pattern):
                return True
        return False

    @staticmethod
    def _validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL format and scheme.
        Returns (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False, f"Invalid scheme: {parsed.scheme}. Only HTTP/HTTPS allowed."

            # Prefer HTTPS
            if parsed.scheme != "https":
                return True, "Warning: Using HTTP instead of HTTPS"

            if not parsed.netloc:
                return False, "Invalid URL: no hostname"

            return True, None
        except Exception as e:
            return False, f"URL validation error: {str(e)}"

    @staticmethod
    def _resolve_and_check_ip(hostname: str) -> Tuple[bool, Optional[str]]:
        """
        Resolve hostname and check if IP is blocked.
        Returns (is_allowed, error_message)
        """
        try:
            # Resolve hostname to IP
            ip = socket.gethostbyname(hostname)

            # Check for blocked IPs
            if URLFetcher._is_blocked_ip(ip):
                return False, f"Access to {ip} is blocked (private/reserved network)"

            return True, None
        except socket.gaierror:
            return False, f"Cannot resolve hostname: {hostname}"
        except socket.error as e:
            return False, f"Socket error resolving {hostname}: {str(e)}"
        except Exception as e:
            return False, f"Error resolving {hostname}: {str(e)}"

    @staticmethod
    async def fetch(
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        timeout: int = REQUEST_TIMEOUT,
    ) -> str:
        """
        Safely fetch URL content with SSRF protection.

        Args:
            url: URL to fetch
            method: HTTP method (GET, POST, etc.)
            headers: Optional headers
            timeout: Request timeout in seconds

        Returns:
            Response content as string

        Raises:
            SSRFException: If SSRF protection blocks the request
            httpx.RequestError: If request fails
        """
        # Validate URL format
        is_valid, error = URLFetcher._validate_url(url)
        if not is_valid:
            raise SSRFException(error)

        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            raise SSRFException("Cannot extract hostname from URL")

        # Resolve and check IP
        is_allowed, error = URLFetcher._resolve_and_check_ip(hostname)
        if not is_allowed:
            raise SSRFException(error)

        # Prepare headers
        if headers is None:
            headers = {}

        # Add User-Agent
        if "User-Agent" not in headers:
            headers["User-Agent"] = "MCP-Server-Builder/1.0"

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                limits=httpx.Limits(
                    max_redirects=MAX_REDIRECTS,
                    max_connections=10,
                ),
            ) as client:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                )

                # Check response size
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > MAX_RESPONSE_SIZE:
                            raise httpx.RequestError(
                                f"Response too large: {content_length} > {MAX_RESPONSE_SIZE}"
                            )
                    except ValueError:
                        pass

                # Raise for status
                response.raise_for_status()

                # Read content with size limit
                content = b""
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    content += chunk
                    if len(content) > MAX_RESPONSE_SIZE:
                        raise httpx.RequestError(
                            f"Response too large: exceeded {MAX_RESPONSE_SIZE} bytes"
                        )

                return content.decode("utf-8", errors="ignore")

        except SSRFException:
            raise
        except httpx.RequestError as e:
            raise httpx.RequestError(f"Request failed: {str(e)}")
        except Exception as e:
            raise httpx.RequestError(f"Unexpected error: {str(e)}")
