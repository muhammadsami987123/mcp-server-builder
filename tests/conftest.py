"""Shared pytest fixtures: isolated storage dirs (never touch real app/data),
demo OpenAPI fixture, and a DNS-fake so unit tests never depend on real network
resolution while still exercising url_fetcher's SSRF logic."""

from __future__ import annotations

import json
import socket

import pytest

from app import config


@pytest.fixture
def tmp_data_dirs(tmp_path, monkeypatch):
    """Redirect config.DATA_DIR/PROJECTS_DIR/GENERATED_DIR at a tmp_path so no
    test ever writes into the real app/data directory."""
    data_dir = tmp_path / "data"
    projects_dir = data_dir / "projects"
    generated_dir = tmp_path / "generated-projects"
    data_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(config, "GENERATED_DIR", generated_dir)

    return {"data_dir": data_dir, "projects_dir": projects_dir, "generated_dir": generated_dir}


@pytest.fixture
def demo_spec() -> dict:
    with open(config.DEMO_SPEC_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def fake_public_dns(monkeypatch):
    """Make socket.getaddrinfo resolve ANY hostname to a public IP, so
    url_fetcher's SSRF resolution check passes without real DNS lookups in
    tests that aren't specifically exercising the private/blocked-IP path."""

    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
