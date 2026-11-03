"""Unit tests for Hugging Face Inference API client and JSON parsing helpers."""

from unittest.mock import MagicMock, patch

from generation.hf_client import (
    _extract_json_from_text,
    _strip_json_block,
    call_hf_chat_completion,
    check_hf_connection,
    generate_json_response,
)


def test_strip_json_block() -> None:
    """Test stripping markdown code blocks from JSON text."""
    raw_md = '```json\n{"answer": "Test"}\n```'
    assert _strip_json_block(raw_md) == '{"answer": "Test"}'

    plain = '{"answer": "Test"}'
    assert _strip_json_block(plain) == '{"answer": "Test"}'


def test_extract_json_from_text() -> None:
    """Test extracting JSON object embedded inside prose."""
    prose = 'Result:\n```json\n{"score": 0.95, "status": "ok"}\n```\nDone!'
    extracted = _extract_json_from_text(prose)
    assert '{"score": 0.95, "status": "ok"}' in extracted


def test_call_hf_chat_completion_success() -> None:
    """Test successful chat completion call to HuggingFace Inference API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"answer": "Grounded answer"}'}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        result = call_hf_chat_completion(
            system_prompt="System instructions",
            user_message="User question",
            api_key="hf_test_token",
        )
        assert result == '{"answer": "Grounded answer"}'


def test_generate_json_response_parsed() -> None:
    """Test generating and parsing structured JSON from HuggingFace response."""
    with patch(
        "generation.hf_client.call_hf_chat_completion",
        return_value='```json\n{"answer": "Port risk high", "confidence": "high"}\n```',
    ):
        data = generate_json_response(
            system_prompt="System",
            user_message="User",
            api_key="hf_test_token",
        )
        assert data["answer"] == "Port risk high"
        assert data["confidence"] == "high"


def test_check_hf_connection_helper() -> None:
    """Test testing HuggingFace API connectivity helper."""
    with patch(
        "generation.hf_client.call_hf_chat_completion",
        return_value="OK",
    ):
        success, msg = check_hf_connection("hf_test_token")
        assert success is True
        assert "connected" in msg
