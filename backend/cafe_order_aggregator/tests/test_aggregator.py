"""Tests for aggregation job logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from psycopg import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from cafe_order_aggregator.aggregator import connect_with_retry, run_aggregation


class TestConnectWithRetry:
    """Tests for connect_with_retry function."""

    @pytest.mark.asyncio
    async def test_successful_connection_first_attempt(self):
        """Test successful connection on first attempt."""
        mock_connection = MagicMock()
        connect_fn = AsyncMock(return_value=mock_connection)

        result = await connect_with_retry(connect_fn, "test_service")

        assert result == mock_connection
        connect_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_connection_after_retry(self):
        """Test successful connection after failed attempts."""
        mock_connection = MagicMock()
        connect_fn = AsyncMock(side_effect=[OperationalError("Connection failed"), mock_connection])

        with patch("cafe_order_aggregator.aggregator.asyncio.sleep", new_callable=AsyncMock):
            result = await connect_with_retry(connect_fn, "test_service", max_retries=3)

        assert result == mock_connection
        assert connect_fn.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self):
        """Test that exception is raised after all retries fail."""
        connect_fn = AsyncMock(side_effect=OperationalError("Connection failed"))

        with patch("cafe_order_aggregator.aggregator.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OperationalError):
                await connect_with_retry(connect_fn, "test_service", max_retries=3)

        assert connect_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_handles_redis_connection_error(self):
        """Test handling of Redis connection errors."""
        mock_connection = MagicMock()
        connect_fn = AsyncMock(side_effect=[RedisConnectionError("Redis error"), mock_connection])

        with patch("cafe_order_aggregator.aggregator.asyncio.sleep", new_callable=AsyncMock):
            result = await connect_with_retry(connect_fn, "Redis", max_retries=3)

        assert result == mock_connection

    @pytest.mark.asyncio
    async def test_handles_os_error(self):
        """Test handling of OS errors."""
        mock_connection = MagicMock()
        connect_fn = AsyncMock(side_effect=[OSError("Network error"), mock_connection])

        with patch("cafe_order_aggregator.aggregator.asyncio.sleep", new_callable=AsyncMock):
            result = await connect_with_retry(connect_fn, "test_service", max_retries=3)

        assert result == mock_connection

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that backoff increases exponentially."""
        connect_fn = AsyncMock(side_effect=OperationalError("Connection failed"))

        with patch(
            "cafe_order_aggregator.aggregator.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            with pytest.raises(OperationalError):
                await connect_with_retry(
                    connect_fn, "test_service", max_retries=3, initial_backoff=1.0
                )

        # Should sleep with exponential backoff: 1.0, 2.0 (no sleep after last attempt)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @pytest.mark.asyncio
    async def test_no_sleep_on_first_attempt_success(self):
        """Test that no sleep occurs on successful first attempt."""
        connect_fn = AsyncMock(return_value=MagicMock())

        with patch(
            "cafe_order_aggregator.aggregator.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await connect_with_retry(connect_fn, "test_service")

        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_retry(self):
        """Test with single retry allowed."""
        connect_fn = AsyncMock(side_effect=OperationalError("Connection failed"))

        with patch("cafe_order_aggregator.aggregator.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OperationalError):
                await connect_with_retry(connect_fn, "test_service", max_retries=1)

        assert connect_fn.call_count == 1


class TestRunAggregation:
    """Tests for run_aggregation function."""

    @pytest.mark.asyncio
    async def test_run_aggregation_with_provided_connections(
        self, mock_redis, mock_db, sample_orders
    ):
        """Test run_aggregation with provided db and redis connections."""
        db_conn, _ = mock_db

        with patch(
            "cafe_order_aggregator.aggregator.get_orders_for_hour",
            new_callable=AsyncMock,
            return_value=sample_orders,
        ):
            with patch(
                "cafe_order_aggregator.aggregator.get_orders_last_30_days",
                new_callable=AsyncMock,
                return_value=sample_orders,
            ):
                with patch(
                    "cafe_order_aggregator.aggregator.get_recent_orders",
                    new_callable=AsyncMock,
                    return_value=sample_orders,
                ):
                    result = await run_aggregation(db=db_conn, redis=mock_redis)

        assert "hourly_metrics" in result
        assert "top5_drinks" in result
        assert "recent_orders_count" in result
        assert result["recent_orders_count"] == 5

    @pytest.mark.asyncio
    async def test_run_aggregation_updates_hourly_metrics(self, mock_redis, mock_db, sample_orders):
        """Test that run_aggregation updates hourly metrics."""
        db_conn, _ = mock_db

        with patch(
            "cafe_order_aggregator.aggregator.get_orders_for_hour",
            new_callable=AsyncMock,
            return_value=sample_orders,
        ):
            with patch(
                "cafe_order_aggregator.aggregator.get_orders_last_30_days",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "cafe_order_aggregator.aggregator.get_recent_orders",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    result = await run_aggregation(db=db_conn, redis=mock_redis)

        assert result["hourly_metrics"]["order_count"] == 5
        assert result["hourly_metrics"]["revenue"] == 24.75

    @pytest.mark.asyncio
    async def test_run_aggregation_updates_top5_drinks(self, mock_redis, mock_db, sample_orders):
        """Test that run_aggregation updates top5 drinks."""
        db_conn, _ = mock_db

        with patch(
            "cafe_order_aggregator.aggregator.get_orders_for_hour",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "cafe_order_aggregator.aggregator.get_orders_last_30_days",
                new_callable=AsyncMock,
                return_value=sample_orders,
            ):
                with patch(
                    "cafe_order_aggregator.aggregator.get_recent_orders",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    result = await run_aggregation(db=db_conn, redis=mock_redis)

        assert "cappuccino" in result["top5_drinks"]

    @pytest.mark.asyncio
    async def test_run_aggregation_does_not_close_provided_connections(
        self, mock_redis, mock_db, sample_orders
    ):
        """Test that provided connections are not closed."""
        db_conn, _ = mock_db

        with patch(
            "cafe_order_aggregator.aggregator.get_orders_for_hour",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "cafe_order_aggregator.aggregator.get_orders_last_30_days",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "cafe_order_aggregator.aggregator.get_recent_orders",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    await run_aggregation(db=db_conn, redis=mock_redis)

        # Provided connections should not be closed
        mock_redis.close.assert_not_called()
        db_conn.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_aggregation_creates_connections_if_not_provided(self):
        """Test that connections are created if not provided."""
        mock_db_conn = AsyncMock()
        mock_redis_conn = AsyncMock()

        with patch(
            "cafe_order_aggregator.aggregator.connect_with_retry",
            new_callable=AsyncMock,
            side_effect=[mock_db_conn, mock_redis_conn],
        ) as mock_connect:
            with patch(
                "cafe_order_aggregator.aggregator.get_orders_for_hour",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "cafe_order_aggregator.aggregator.get_orders_last_30_days",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    with patch(
                        "cafe_order_aggregator.aggregator.get_recent_orders",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        await run_aggregation()

        assert mock_connect.call_count == 2

    @pytest.mark.asyncio
    async def test_run_aggregation_closes_created_connections(self):
        """Test that created connections are closed after aggregation."""
        mock_db_conn = AsyncMock()
        mock_redis_conn = AsyncMock()

        with patch(
            "cafe_order_aggregator.aggregator.connect_with_retry",
            new_callable=AsyncMock,
            side_effect=[mock_db_conn, mock_redis_conn],
        ):
            with patch(
                "cafe_order_aggregator.aggregator.get_orders_for_hour",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "cafe_order_aggregator.aggregator.get_orders_last_30_days",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    with patch(
                        "cafe_order_aggregator.aggregator.get_recent_orders",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        await run_aggregation()

        mock_db_conn.close.assert_called_once()
        mock_redis_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_aggregation_with_empty_data(self, mock_redis, mock_db):
        """Test run_aggregation with no orders."""
        db_conn, _ = mock_db

        with patch(
            "cafe_order_aggregator.aggregator.get_orders_for_hour",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "cafe_order_aggregator.aggregator.get_orders_last_30_days",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "cafe_order_aggregator.aggregator.get_recent_orders",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    result = await run_aggregation(db=db_conn, redis=mock_redis)

        assert result["hourly_metrics"]["order_count"] == 0
        assert result["hourly_metrics"]["revenue"] == 0.0
        assert result["top5_drinks"] == []
        assert result["recent_orders_count"] == 0
