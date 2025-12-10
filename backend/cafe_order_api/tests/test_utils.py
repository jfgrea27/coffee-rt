"""Tests for utility functions."""

from unittest.mock import AsyncMock, patch

import pytest
from psycopg import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from cafe_order_api.utils import connect_with_retry


@pytest.mark.asyncio
async def test_successful_connection_first_attempt():
    """Test successful connection on the first attempt."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(return_value=mock_connection)

    result = await connect_with_retry(connect_fn, "test_service")

    assert result == mock_connection
    connect_fn.assert_called_once()


@pytest.mark.asyncio
async def test_successful_connection_after_retry():
    """Test successful connection after initial failures."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(side_effect=[OperationalError("Connection refused"), mock_connection])

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock):
        result = await connect_with_retry(
            connect_fn, "test_service", max_retries=3, initial_backoff=0.1
        )

    assert result == mock_connection
    assert connect_fn.call_count == 2


@pytest.mark.asyncio
async def test_returns_tuple_after_all_retries_exhausted():
    """Test that (None, exception) is returned after all retries fail."""
    error = OperationalError("Connection refused")
    connect_fn = AsyncMock(side_effect=error)

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock):
        result = await connect_with_retry(
            connect_fn, "test_service", max_retries=3, initial_backoff=0.1
        )

    assert isinstance(result, tuple)
    assert result[0] is None
    assert result[1] == error
    assert connect_fn.call_count == 3


@pytest.mark.asyncio
async def test_handles_operational_error():
    """Test that OperationalError triggers retry."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(side_effect=[OperationalError("DB error"), mock_connection])

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock):
        result = await connect_with_retry(
            connect_fn, "test_service", max_retries=2, initial_backoff=0.1
        )

    assert result == mock_connection
    assert connect_fn.call_count == 2


@pytest.mark.asyncio
async def test_handles_redis_connection_error():
    """Test that RedisConnectionError triggers retry."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(side_effect=[RedisConnectionError("Redis error"), mock_connection])

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock):
        result = await connect_with_retry(
            connect_fn, "test_service", max_retries=2, initial_backoff=0.1
        )

    assert result == mock_connection
    assert connect_fn.call_count == 2


@pytest.mark.asyncio
async def test_handles_os_error():
    """Test that OSError triggers retry."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(side_effect=[OSError("Network error"), mock_connection])

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock):
        result = await connect_with_retry(
            connect_fn, "test_service", max_retries=2, initial_backoff=0.1
        )

    assert result == mock_connection
    assert connect_fn.call_count == 2


@pytest.mark.asyncio
async def test_exponential_backoff():
    """Test that backoff increases exponentially."""
    connect_fn = AsyncMock(side_effect=OperationalError("Connection refused"))
    sleep_times = []

    async def mock_sleep(duration):
        sleep_times.append(duration)

    with patch("cafe_order_api.utils.asyncio.sleep", side_effect=mock_sleep):
        await connect_with_retry(connect_fn, "test_service", max_retries=4, initial_backoff=1.0)

    # Should have 3 sleeps (not after the last attempt)
    assert len(sleep_times) == 3
    # Exponential backoff: 1, 2, 4
    assert sleep_times[0] == 1.0
    assert sleep_times[1] == 2.0
    assert sleep_times[2] == 4.0


@pytest.mark.asyncio
async def test_no_sleep_on_first_attempt_success():
    """Test that no sleep occurs when first attempt succeeds."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(return_value=mock_connection)

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await connect_with_retry(connect_fn, "test_service")

    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_no_sleep_after_last_attempt():
    """Test that no sleep occurs after the last failed attempt."""
    connect_fn = AsyncMock(side_effect=OperationalError("Connection refused"))

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await connect_with_retry(connect_fn, "test_service", max_retries=2, initial_backoff=1.0)

    # Only 1 sleep (after first attempt, not after second/last)
    assert mock_sleep.call_count == 1


@pytest.mark.asyncio
async def test_logs_warning_on_retry():
    """Test that warnings are logged on retry attempts."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(side_effect=[OperationalError("Connection refused"), mock_connection])

    with (
        patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock),
        patch("cafe_order_api.utils.logger") as mock_logger,
    ):
        await connect_with_retry(connect_fn, "test_service", max_retries=3, initial_backoff=1.0)

    mock_logger.warning.assert_called_once()
    call_args = mock_logger.warning.call_args[0][0]
    assert "test_service" in call_args
    assert "attempt 1/3" in call_args
    assert "Retrying in 1.0s" in call_args


@pytest.mark.asyncio
async def test_logs_error_on_final_failure():
    """Test that error is logged when all retries fail."""
    connect_fn = AsyncMock(side_effect=OperationalError("Connection refused"))

    with (
        patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock),
        patch("cafe_order_api.utils.logger") as mock_logger,
    ):
        await connect_with_retry(connect_fn, "test_service", max_retries=2, initial_backoff=1.0)

    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args[0][0]
    assert "test_service" in call_args
    assert "after 2 attempts" in call_args


@pytest.mark.asyncio
async def test_default_parameters():
    """Test default parameter values."""
    connect_fn = AsyncMock(side_effect=OperationalError("Connection refused"))
    sleep_times = []

    async def mock_sleep(duration):
        sleep_times.append(duration)

    with patch("cafe_order_api.utils.asyncio.sleep", side_effect=mock_sleep):
        await connect_with_retry(connect_fn, "test_service")

    # Default max_retries=3, so 2 sleeps
    assert len(sleep_times) == 2
    # Default initial_backoff=1.0
    assert sleep_times[0] == 1.0
    assert sleep_times[1] == 2.0


@pytest.mark.asyncio
async def test_single_retry():
    """Test with max_retries=1 (no retries, single attempt)."""
    connect_fn = AsyncMock(side_effect=OperationalError("Connection refused"))

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await connect_with_retry(connect_fn, "test_service", max_retries=1)

    assert isinstance(result, tuple)
    assert result[0] is None
    connect_fn.assert_called_once()
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_unexpected_exception_not_caught():
    """Test that unexpected exceptions are not caught and propagate."""
    connect_fn = AsyncMock(side_effect=ValueError("Unexpected error"))

    with pytest.raises(ValueError, match="Unexpected error"):
        await connect_with_retry(connect_fn, "test_service")


@pytest.mark.asyncio
async def test_mixed_exceptions_before_success():
    """Test handling multiple different exception types before success."""
    mock_connection = AsyncMock()
    connect_fn = AsyncMock(
        side_effect=[
            OperationalError("DB error"),
            RedisConnectionError("Redis error"),
            mock_connection,
        ]
    )

    with patch("cafe_order_api.utils.asyncio.sleep", new_callable=AsyncMock):
        result = await connect_with_retry(
            connect_fn, "test_service", max_retries=5, initial_backoff=0.1
        )

    assert result == mock_connection
    assert connect_fn.call_count == 3
