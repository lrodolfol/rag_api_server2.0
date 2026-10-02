"""Shared test configuration.

Sets hermetic environment variables so the test suite never depends on a real
``.env`` file or on actual secrets. Values use ``setdefault`` so an explicitly
provided environment variable still wins.
"""

import os

_TEST_ENVIRONMENT: dict[str, str] = {
    "ENVIRONMENT": "dev",
    "OPEN_IA_API_KEY": "test-openai-key",
    "DATA_BASE_HOST": "localhost",
    "DATA_BASE_PASSWORD": "test-db-password",
    "REDIS_PASSWORD": "test-redis-password",
    "CLOUD_ACCESS_KEY": "test-access-key",
    "CLOUD_SECRET_KEY": "test-secret-key",
}

for _key, _value in _TEST_ENVIRONMENT.items():
    os.environ.setdefault(_key, _value)
