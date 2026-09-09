"""Lightweight project models used for history/listing endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    id: str
    server_name: str
    source_url: str
    tool_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectSummary(BaseModel):
    id: str
    server_name: str
    tool_count: int
    created_at: datetime
    status: str


class HistoryResponse(BaseModel):
    projects: list[ProjectSummary] = Field(default_factory=list)
    total: int
