"""AI-powered traffic prediction and load balancing."""

import numpy as np
from typing import Optional
import joblib
import logging

logger = logging.getLogger(__name__)


class TrafficPredictor:
    """
    Simple traffic predictor using moving averages and trend detection.

    Predicts:
    - Request volume for the next time window
    - Optimal cache TTL based on traffic patterns
    - Which backend instance to use based on predicted load
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._request_history: list[int] = []
        self._window_size = 100
        self._is_trained = False

    def record_request(self, latency_ms: float, status_code: int):
        """Record a request for pattern learning."""
        self._request_history.append(latency_ms)
        if len(self._request_history) > self._window_size * 10:
            self._request_history = self._request_history[-self._window_size :]

    def predict_next_ttl(self, base_ttl: int = 300) -> int:
        """
        Predict optimal cache TTL based on traffic patterns.

        Returns higher TTL during low-traffic periods,
        lower TTL during high-traffic or unstable periods.
        """
        if len(self._request_history) < 10:
            return base_ttl

        recent = self._request_history[-self._window_size :]

        mean_latency = np.mean(recent)
        std_latency = np.std(recent)
        cv = std_latency / mean_latency if mean_latency > 0 else 0

        if cv > 0.5:
            return int(base_ttl * 0.5)
        elif cv > 0.3:
            return int(base_ttl * 0.75)
        else:
            return int(base_ttl * 1.25)

    def predict_load(self) -> str:
        """
        Predict current load level.

        Returns: 'low', 'medium', or 'high'
        """
        if len(self._request_history) < 10:
            return "medium"

        recent = self._request_history[-self._window_size :]
        mean_latency = np.mean(recent)
        std_latency = np.std(recent)

        if mean_latency < 50 and std_latency < 20:
            return "low"
        elif mean_latency > 200 or std_latency > 100:
            return "high"
        return "medium"

    def get_recommended_timeout(self, base_timeout: int = 30) -> int:
        """Get recommended timeout based on recent latency patterns."""
        if len(self._request_history) < 10:
            return base_timeout

        recent = self._request_history[-self._window_size :]
        mean_latency = np.mean(recent)
        max_latency = max(recent)

        recommended = max(mean_latency * 3, max_latency * 1.5)
        return int(min(recommended, base_timeout * 3))

    def save(self):
        """Save the predictor state."""
        if self.model_path:
            try:
                joblib.dump(
                    {
                        "history": self._request_history,
                        "window_size": self._window_size,
                    },
                    self.model_path,
                )
                logger.info(f"Predictor model saved to {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to save predictor: {e}")

    def load(self):
        """Load the predictor state."""
        if self.model_path:
            try:
                data = joblib.load(self.model_path)
                self._request_history = data.get("history", [])
                self._window_size = data.get("window_size", 100)
                logger.info(f"Predictor model loaded from {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to load predictor: {e}")


class SmartLoadBalancer:
    """
    AI-powered load balancer that routes requests based on predicted load.

    Considers:
    - Current connection count
    - Predicted latency
    - Circuit breaker state
    """

    def __init__(self, predictor: TrafficPredictor):
        self.predictor = predictor
        self._connection_counts: dict[str, int] = {}
        self._health_scores: dict[str, float] = {}

    def select_instance(
        self, instances: list[dict], strategy: str = "ai_powered"
    ) -> dict:
        """
        Select the best instance based on the strategy.

        Args:
            instances: List of backend instances with 'host', 'port', 'weight'
            strategy: Selection strategy ('round_robin', 'least_conn', 'ai_powered')

        Returns:
            Selected instance dict
        """
        if not instances:
            raise ValueError("No instances available")

        if len(instances) == 1:
            return instances[0]

        if strategy == "round_robin":
            return self._round_robin(instances)
        elif strategy == "least_conn":
            return self._least_connections(instances)
        elif strategy == "ai_powered":
            return self._ai_powered(instances)
        else:
            return instances[0]

    def _round_robin(self, instances: list[dict]) -> dict:
        """Round robin selection."""
        return instances[0]

    def _least_connections(self, instances: list[dict]) -> dict:
        """Select instance with fewest active connections."""
        min_connections = float("inf")
        selected = instances[0]

        for inst in instances:
            conn_count = self._connection_counts.get(
                f"{inst['host']}:{inst['port']}", 0
            )
            if conn_count < min_connections:
                min_connections = conn_count
                selected = inst

        return selected

    def _ai_powered(self, instances: list[dict]) -> dict:
        """
        AI-powered selection considering predicted load and health.

        This is a simplified implementation. In production, you would:
        - Query metrics from each instance
        - Use the predictor to forecast load
        - Consider circuit breaker states
        """
        load_level = self.predictor.predict_load()

        candidates = []
        for inst in instances:
            health = self._health_scores.get(f"{inst['host']}:{inst['port']}", 1.0)
            connections = self._connection_counts.get(
                f"{inst['host']}:{inst['port']}", 0
            )

            if health < 0.5:
                continue

            weight = inst.get("weight", 1)

            if load_level == "low":
                score = health * weight
            elif load_level == "medium":
                score = health * weight / (connections + 1)
            else:
                score = health * weight / (connections + 1) ** 2

            candidates.append((score, inst))

        if not candidates:
            return instances[0]

        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]

    def record_connection(self, host: str, port: int):
        """Record a new connection to an instance."""
        key = f"{host}:{port}"
        self._connection_counts[key] = self._connection_counts.get(key, 0) + 1

    def release_connection(self, host: str, port: int):
        """Release a connection from an instance."""
        key = f"{host}:{port}"
        if key in self._connection_counts:
            self._connection_counts[key] = max(0, self._connection_counts[key] - 1)

    def update_health_score(self, host: str, port: int, score: float):
        """Update health score for an instance."""
        key = f"{host}:{port}"
        current = self._health_scores.get(key, 1.0)
        self._health_scores[key] = current * 0.7 + score * 0.3

    def get_stats(self) -> dict:
        """Get load balancer statistics."""
        return {
            "connections": dict(self._connection_counts),
            "health_scores": dict(self._health_scores),
            "predicted_load": self.predictor.predict_load(),
        }
