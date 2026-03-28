"""Tests for configuration loader."""

import pytest
import tempfile
import os

from apimesh.config_loader import ConfigLoader


class TestConfigLoader:
    """Test configuration file loader."""

    def test_load_yaml_config(self, tmp_path):
        """Test loading YAML configuration."""
        config_content = """
services:
  api:
    hosts:
      - localhost
      - 127.0.0.1
    port: 8001
    path_prefix: /api/v1
    timeout: 30.0
    weight: 1
    max_retries: 3
  auth:
    hosts:
      - localhost
    port: 8002
    path_prefix: /auth

routes:
  - path_pattern: /api
    service_name: api
    methods:
      - GET
      - POST
      - PUT
      - DELETE
    cache_ttl: 60
    auth_required: true
  - path_pattern: /auth
    service_name: auth
    methods:
      - POST
    auth_required: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        services, routes = ConfigLoader.load(str(config_file))

        assert "api" in services
        assert "auth" in services
        assert services["api"].hosts == ["localhost", "127.0.0.1"]
        assert services["api"].port == 8001
        assert services["api"].path_prefix == "/api/v1"
        assert services["api"].max_retries == 3

        assert len(routes) == 2
        assert routes[0].path_pattern == "/api"
        assert routes[0].service_name == "api"
        assert routes[0].auth_required is True
        assert routes[0].cache_ttl == 60

    def test_load_json_config(self, tmp_path):
        """Test loading JSON configuration."""
        config_content = """{
  "services": {
    "api": {
      "hosts": ["localhost"],
      "port": 8001,
      "path_prefix": "/api"
    }
  },
  "routes": [
    {
      "path_pattern": "/api",
      "service_name": "api",
      "methods": ["GET", "POST"]
    }
  ]
}"""
        config_file = tmp_path / "config.json"
        config_file.write_text(config_content)

        services, routes = ConfigLoader.load(str(config_file))

        assert "api" in services
        assert services["api"].port == 8001
        assert len(routes) == 1

    def test_file_not_found(self):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load("/nonexistent/config.yaml")

    def test_generate_sample_yaml(self, tmp_path):
        """Test generating sample YAML config."""
        sample_file = tmp_path / "sample.yaml"
        ConfigLoader.generate_sample(str(sample_file))

        assert sample_file.exists()

        services, routes = ConfigLoader.load(str(sample_file))
        assert "api" in services
        assert "auth" in services
        assert len(routes) > 0

    def test_generate_sample_json(self, tmp_path):
        """Test generating sample JSON config."""
        sample_file = tmp_path / "sample.json"
        ConfigLoader.generate_sample(str(sample_file))

        assert sample_file.exists()

        services, routes = ConfigLoader.load(str(sample_file))
        assert "api" in services


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
