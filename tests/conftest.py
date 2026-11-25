#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for GESTIA tests.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from starlette.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import AgentContext
from agents.chief import ChiefAgent
from agents.specialists.administrativo import AdministrativoAgent
from agents.specialists.contable import ContableAgent
from agents.specialists.mercantil import MercantilAgent
from agents.specialists.personal import PersonalAgent
from web.main import app


# ============================================================
# SESSION SCOPE FIXTURES
# ============================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def client_data() -> dict:
    """Load cliente_ejemplo metadata."""
    metadata_path = Path(__file__).parent.parent / "cliente_ejemplo" / "metadata.json"
    with open(metadata_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


# ============================================================
# AGENT FIXTURES
# ============================================================

@pytest.fixture
def agent_context() -> AgentContext:
    """Standard agent context for testing."""
    return AgentContext(
        user_id="test_user",
        tenant_id="tech-solutions-sl",
        metadata={"test": True},
    )


@pytest.fixture
def mercantil_agent() -> MercantilAgent:
    return MercantilAgent()


@pytest.fixture
def administrativo_agent() -> AdministrativoAgent:
    return AdministrativoAgent()


@pytest.fixture
def contable_agent() -> ContableAgent:
    return ContableAgent()


@pytest.fixture
def personal_agent() -> PersonalAgent:
    return PersonalAgent()


@pytest.fixture
def chief_agent() -> ChiefAgent:
    return ChiefAgent()


# ============================================================
# MOCK FIXTURES
# ============================================================

@pytest.fixture
def mock_docling_response() -> dict:
    """Mock Docling OCR response."""
    return {
        "text": "Sample document text for testing",
        "tables": [
            {"headers": ["Col1", "Col2"], "rows": [["A", "1"], ["B", "2"]]}
        ],
        "metadata": {"pages": 1, "language": "es"},
    }


@pytest.fixture
def mock_embedding_response() -> dict:
    """Mock embedding service response."""
    return {
        "embeddings": [[0.1] * 384],
        "model": "all-MiniLM-L6-v2",
    }


@pytest.fixture
def mock_api_response() -> dict:
    """Mock internal API response."""
    return {"status": "ok", "data": {}}


# ============================================================
# TEMP FILE FIXTURES
# ============================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing."""
    return b"%PDF-1.4\n%Test PDF content\n%%EOF"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def assert_agent_response(response, expected_agent: str = None, success: bool = True):
    """Assert standard agent response structure."""
    assert hasattr(response, "agent")
    assert hasattr(response, "success")
    assert hasattr(response, "response")
    assert hasattr(response, "data")
    assert response.success == success
    if expected_agent:
        assert response.agent == expected_agent
    assert isinstance(response.response, str)
    assert len(response.response) > 0
    assert isinstance(response.data, dict)


def assert_structured_response(response, required_fields: list = None):
    """Assert structured specialist response."""
    assert_agent_response(response)
    default_fields = ["action", "domain", "confidence", "summary", "next_steps", "documents_needed", "deadlines", "citations"]
    fields = required_fields or default_fields
    for field in fields:
        assert field in response.data, f"Missing field: {field}"


# ============================================================
# PYTEST CONFIGURATION
# ============================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "agents: Agent tests")
    config.addinivalue_line("markers", "web: Web UI tests")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on path."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)