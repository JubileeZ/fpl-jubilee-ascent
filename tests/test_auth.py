import json
import pytest
from unittest.mock import AsyncMock, patch

def mock_is_jwt_expired(token):
    return token == "expired_token"

@pytest.fixture(autouse=True)
def mock_dependencies(tmp_path):
    cache_path = tmp_path / "session_token.json"
    with patch("clients.fpl_auth.is_jwt_expired", side_effect=mock_is_jwt_expired), \
         patch("clients.fpl_auth.TOKEN_CACHE_PATH", cache_path):
        yield cache_path

@pytest.mark.asyncio
async def test_get_jwt_token_valid_cache(mock_dependencies):
    cache_path = mock_dependencies
    with patch.dict("os.environ", {}, clear=True):
        cache_path.write_text(json.dumps({"token": "valid_cached_token", "cached_at": 100}))
        from clients.fpl_auth import get_jwt_token
        token = await get_jwt_token()
        assert token == "valid_cached_token"

@pytest.mark.asyncio
async def test_get_jwt_token_no_auth_raises_value_error(mock_dependencies):
    with patch.dict("os.environ", {}, clear=True):
        from clients.fpl_auth import get_jwt_token
        with pytest.raises(ValueError, match="FPL authentication missing"):
            await get_jwt_token()

@pytest.mark.asyncio
async def test_get_jwt_token_fallback_to_playwright(mock_dependencies):
    mock_login = AsyncMock(return_value="playwright_token")
    with patch.dict("os.environ", {"FPL_EMAIL": "test@test.com", "FPL_PASSWORD": "pass"}, clear=True), \
         patch("clients.fpl_auth.async_login", mock_login):
        from clients.fpl_auth import get_jwt_token
        token = await get_jwt_token()
        assert token == "playwright_token"
        mock_login.assert_called_once()
