"""Configuration file loader for API Mesh Gateway."""

from typing import List
from pathlib import Path
import json
import yaml

from apimesh.core import RouteConfig, ServiceConfig


class ConfigLoader:
    """Load gateway configuration from file."""

    @staticmethod
    def load(config_path: str) -> tuple[dict[str, ServiceConfig], List[RouteConfig]]:
        """Load configuration from YAML or JSON file.

        Returns:
            Tuple of (services dict, routes list)
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            if path.suffix in (".yaml", ".yml"):
                config_data = yaml.safe_load(f)
            elif path.suffix == ".json":
                config_data = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {path.suffix}")

        return ConfigLoader._parse_config(config_data)

    @staticmethod
    def _parse_config(data: dict) -> tuple[dict[str, ServiceConfig], list[RouteConfig]]:
        """Parse configuration data into objects."""
        services = {}
        routes = []

        # Parse services
        for name, svc_data in data.get("services", {}).items():
            # Only include keys that are present in the data
            service_kwargs = {
                "name": name,
                "hosts": svc_data.get("hosts", ["localhost"]),
                "port": svc_data.get("port", 8000),
                "path_prefix": svc_data.get("path_prefix", "/"),
                "weight": svc_data.get("weight", 1),
                "timeout": svc_data.get("timeout", 30.0),
                "max_retries": svc_data.get("max_retries", 3),
            }
            if svc_data.get("health_check_path"):
                service_kwargs["health_check_path"] = svc_data["health_check_path"]

            service = ServiceConfig(**service_kwargs)
            services[name] = service

        # Parse routes
        for route_data in data.get("routes", []):
            route_kwargs = {
                "path_pattern": route_data.get("path_pattern", "/"),
                "service_name": route_data.get("service_name", ""),
                "methods": route_data.get("methods", ["GET"]),
                "auth_required": route_data.get("auth_required", False),
            }
            if route_data.get("cache_ttl") is not None:
                route_kwargs["cache_ttl"] = route_data["cache_ttl"]
            if route_data.get("rate_limit") is not None:
                route_kwargs["rate_limit"] = route_data["rate_limit"]

            route = RouteConfig(**route_kwargs)
            routes.append(route)

        return services, routes

    @staticmethod
    def generate_sample(path: str = "gateway_config.yaml"):
        """Generate a sample configuration file."""
        sample = {
            "services": {
                "api": {
                    "hosts": ["localhost"],
                    "port": 8001,
                    "path_prefix": "/api/v1",
                    "weight": 1,
                    "timeout": 30.0,
                    "max_retries": 3,
                },
                "auth": {
                    "hosts": ["localhost"],
                    "port": 8002,
                    "path_prefix": "/auth",
                    "weight": 1,
                    "timeout": 10.0,
                },
            },
            "routes": [
                {
                    "path_pattern": "/api",
                    "service_name": "api",
                    "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "cache_ttl": 60,
                    "auth_required": True,
                },
                {
                    "path_pattern": "/auth",
                    "service_name": "auth",
                    "methods": ["POST"],
                    "auth_required": False,
                },
            ],
        }

        with open(path, "w") as f:
            if path.endswith(".json"):
                json.dump(sample, f, indent=2)
            else:
                yaml.dump(sample, f, default_flow_style=False)

        return path
