"""Tests for API Mesh Gateway."""

import pytest
from apimesh.circuit import CircuitBreaker, CircuitBreakerConfig, CircuitState
from apimesh.limiter import SlidingWindowRateLimiter, RateLimitConfig
from apimesh.ai import TrafficPredictor, SmartLoadBalancer
from apimesh.cache import CacheManager


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_starts_closed(self):
        """Circuit breaker should start in closed state."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_calls(self):
        """Successful calls should keep circuit closed."""
        breaker = CircuitBreaker("test")
        result = await breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_async_calls(self):
        """Async function calls should work."""
        breaker = CircuitBreaker("test")

        async def async_func():
            return "async success"

        result = await breaker.call(async_func)
        assert result == "async success"

    @pytest.mark.asyncio
    async def test_opens_after_failures(self):
        """Circuit should open after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert breaker.state == CircuitState.OPEN

        with pytest.raises(Exception, match="OPEN"):
            await breaker.call(lambda: "should fail")


class TestRateLimiter:
    """Test rate limiter functionality."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Should allow requests within limit."""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)

        for _ in range(10):
            allowed, _ = await limiter.is_allowed("client1")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        """Should block requests over limit."""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)

        for _ in range(5):
            await limiter.is_allowed("client1")

        allowed, info = await limiter.is_allowed("client1")
        assert allowed is False
        assert info["remaining"] == 0

    @pytest.mark.asyncio
    async def test_different_clients(self):
        """Different clients should have separate limits."""
        config = RateLimitConfig(max_requests=2, window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)

        assert await limiter.is_allowed("client1")
        assert await limiter.is_allowed("client1")
        assert not (await limiter.is_allowed("client1"))[0]

        assert await limiter.is_allowed("client2")
        assert await limiter.is_allowed("client2")


class TestTrafficPredictor:
    """Test AI traffic predictor."""

    def test_initial_state(self):
        """Predictor should have reasonable defaults."""
        predictor = TrafficPredictor()
        assert predictor.predict_load() == "medium"
        assert predictor.predict_next_ttl() == 300

    def test_records_requests(self):
        """Predictor should record request data."""
        predictor = TrafficPredictor()

        for _ in range(20):
            predictor.record_request(50.0, 200)

        assert predictor.predict_load() in ["low", "medium"]

        for _ in range(20):
            predictor.record_request(300.0, 500)

        assert predictor.predict_load() in ["medium", "high"]


class TestSmartLoadBalancer:
    """Test smart load balancer."""

    def test_single_instance(self):
        """Should return single instance."""
        predictor = TrafficPredictor()
        balancer = SmartLoadBalancer(predictor)

        instances = [{"host": "host1", "port": 8000, "weight": 1}]
        selected = balancer.select_instance(instances)

        assert selected == instances[0]

    def test_selects_from_multiple(self):
        """Should select from multiple instances."""
        predictor = TrafficPredictor()
        balancer = SmartLoadBalancer(predictor)

        instances = [
            {"host": "host1", "port": 8000, "weight": 1},
            {"host": "host2", "port": 8000, "weight": 1},
        ]
        selected = balancer.select_instance(instances)

        assert selected in instances

    def test_tracks_connections(self):
        """Should track connection counts."""
        predictor = TrafficPredictor()
        balancer = SmartLoadBalancer(predictor)

        balancer.record_connection("host1", 8000)
        balancer.record_connection("host1", 8000)
        balancer.record_connection("host2", 8000)

        stats = balancer.get_stats()
        assert stats["connections"]["host1:8000"] == 2
        assert stats["connections"]["host2:8000"] == 1


class TestCacheManager:
    """Test cache manager."""

    @pytest.mark.asyncio
    async def test_disabled_cache(self):
        """Should handle disabled cache gracefully."""
        manager = CacheManager()
        manager.enabled = False

        result = await manager.get("test_key")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
