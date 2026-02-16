"""Conftest for opinto_ohjaus tests.

Registers the 'req' marker so tests can run standalone without
the root tests/conftest.py enforcement hook.
"""


def pytest_configure(config):
    config.addinivalue_line("markers", "req: Requirement traceability marker")
    config.addinivalue_line("markers", "integration: Integration test requiring API keys")
