"""Safe URL fetching with SSRF protection."""
import ipaddress
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
        """Check if IP is in blocked ranges using ipaddress module."""
        try:
            ip_obj = ipaddress.ip_address(ip)

            # Check reserved/private ranges using ipaddress module
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or \
               ip_obj.is_reserved or ip_obj.is_multicast:
                return True

            # Additional check for AWS metadata endpoint (169.254.169.254)
            if ip == "169.254.169.254":
                return True

            # Legacy pattern matching as fallback
            for pattern in BLOCKED_IP_PATTERNS:
                if ip.startswith(pattern):
                    return True

            return False
        except ValueError:
            # Invalid IP format - block it to be safe
            return True

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
        Resolve hostname to ALL addresses and validate each.
        Prevents DNS rebinding attacks by checking all resolved IPs.
        Returns (is_allowed, error_message)
        """
        try:
            # Get ALL resolved addresses (not just first one)
            addr_infos = socket.getaddrinfo(hostname, None)

            if not addr_infos:
                return False, f"Cannot resolve hostname: {hostname}"

            # Extract unique IP addresses
            resolved_ips = {addr[4][0] for addr in addr_infos}

            # Validate each resolved IP
            for ip in resolved_ips:
                if URLFetcher._is_blocked_ip(ip):
                    return False, f"Access to {ip} resolved from {hostname} is blocked (private/reserved network)"

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
        Manually handles redirects with re-validation of each hop.

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
        # Prepare headers
        if headers is None:
            headers = {}

        # Add User-Agent
        if "User-Agent" not in headers:
            headers["User-Agent"] = "MCP-Server-Builder/1.0"

        # Manual redirect handling to validate each hop
        current_url = url
        redirect_count = 0

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,  # Manually handle redirects
                limits=httpx.Limits(
                    max_redirects=MAX_REDIRECTS,
                    max_connections=10,
                ),
            ) as client:
                while redirect_count <= MAX_REDIRECTS:
                    # Validate URL format for this hop
                    is_valid, error = URLFetcher._validate_url(current_url)
                    if not is_valid:
                        raise SSRFException(f"Invalid redirect URL: {error}")

                    parsed = urlparse(current_url)
                    hostname = parsed.hostname

                    if not hostname:
                        raise SSRFException("Cannot extract hostname from URL")

                    # Re-validate IP for this hop (prevents DNS rebinding)
                    is_allowed, error = URLFetcher._resolve_and_check_ip(hostname)
                    if not is_allowed:
                        raise SSRFException(f"Redirect to blocked destination: {error}")

                    # Make request without auto-following
                    response = await client.request(
                        method,
                        current_url,
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

                    # Handle redirects manually
                    if response.is_redirect:
                        redirect_count += 1
                        redirect_location = response.headers.get("location")

                        if not redirect_location:
                            raise SSRFException("Redirect without Location header")

                        # Resolve relative URLs
                        from urllib.parse import urljoin
                        current_url = urljoin(current_url, redirect_location)
                        continue

                    # Not a redirect - process response
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

                # Too many redirects
                raise SSRFException(f"Too many redirects (max {MAX_REDIRECTS})")

        except SSRFException:
            raise
        except httpx.RequestError as e:
            raise httpx.RequestError(f"Request failed: {str(e)}")
        except Exception as e:
            raise httpx.RequestError(f"Unexpected error: {str(e)}")
