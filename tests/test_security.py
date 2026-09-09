"""SSRF protection tests for app.services.url_fetcher."""

from __future__ import annotations

import socket

import httpx
import pytest
import respx

from app.services.url_fetcher import SSRFError, safe_fetch, validate_url_format


class TestValidateUrlFormat:
    def test_empty_url_rejected(self):
        ok, reason = validate_url_format("")
        assert ok is False
        assert reason

    def test_non_http_scheme_rejected(self):
        ok, reason = validate_url_format("ftp://example.com/file")
        assert ok is False

    def test_no_hostname_rejected(self):
        ok, reason = validate_url_format("http:///just-a-path")
        assert ok is False

    def test_localhost_hostname_rejected(self):
        ok, reason = validate_url_format("http://localhost/")
        assert ok is False

    def test_metadata_hostname_rejected(self):
        ok, reason = validate_url_format("http://169.254.169.254/latest/meta-data/")
        assert ok is False

    def test_too_long_url_rejected(self):
        ok, reason = validate_url_format("https://example.com/" + "a" * 3000)
        assert ok is False

    def test_valid_https_url_accepted(self):
        ok, reason = validate_url_format("https://api.example.com/openapi.json")
        assert ok is True
        assert reason is None


class TestSafeFetchBlocksPrivateNetworks:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:9000/",
            "http://10.1.2.3/",
            "http://192.168.1.1/",
            "http://169.254.169.254/",
            "http://localhost/",
        ],
    )
    async def test_blocked_address_raises_ssrf_error(self, url):
        with pytest.raises(SSRFError):
            await safe_fetch(url)


class TestDnsRebinding:
    async def test_hostname_resolving_to_private_ip_is_blocked(self, monkeypatch):
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 0))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        with pytest.raises(SSRFError):
            await safe_fetch("http://evil-rebinding.example.com/")

    async def test_hostname_resolving_to_link_local_is_blocked(self, monkeypatch):
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.10.10", 0))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        with pytest.raises(SSRFError):
            await safe_fetch("http://sneaky.example.com/")


class TestInvalidUrlStrings:
    @pytest.mark.parametrize(
        "bad_url",
        ["not a url", "", "javascript:alert(1)", "file:///etc/passwd", "ftp://example.com/x"],
    )
    async def test_invalid_url_strings_rejected(self, bad_url):
        with pytest.raises(SSRFError):
            await safe_fetch(bad_url)


class TestRedirectToBlockedIP:
    async def test_redirect_chain_to_blocked_ip_is_rejected(self, monkeypatch):
        def fake_getaddrinfo(host, port, *args, **kwargs):
            if host == "public.example.com":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
            if host == "internal.example.com":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
            raise socket.gaierror("unknown host")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        with respx.mock(assert_all_called=False) as mock:
            mock.get("http://public.example.com/").mock(
                return_value=httpx.Response(
                    302, headers={"location": "http://internal.example.com/secret"}
                )
            )
            with pytest.raises(SSRFError):
                await safe_fetch("http://public.example.com/")


class TestOversizedResponse:
    async def test_oversized_response_raises(self, monkeypatch):
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        big_body = b"x" * (2 * 1024 * 1024)  # 2MB, well over our 1KB test cap

        with respx.mock(assert_all_called=False) as mock:
            mock.get("http://big.example.com/").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "text/plain"}, content=big_body
                )
            )
            with pytest.raises(SSRFError):
                await safe_fetch("http://big.example.com/", max_size=1024)
