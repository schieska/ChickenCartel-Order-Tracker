# Testing Guide

This directory contains tests for the ChickenCartel Order Tracker integration.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements_test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Test config flow
pytest tests/test_config_flow.py

# Test coordinator
pytest tests/test_coordinator.py

# Test sensor
pytest tests/test_sensor.py

# Test constants
pytest tests/test_const.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=custom_components.chickencartel --cov-report=html
```

## Test Structure

- `test_config_flow.py` - Tests for configuration flow and order ID validation
- `test_coordinator.py` - Tests for the data update coordinator and API interactions
- `test_sensor.py` - Tests for the sensor entity
- `test_const.py` - Tests for constants and configuration values
- `test_init.py` - Tests for integration setup and teardown
- `conftest.py` - Shared pytest fixtures

## Writing New Tests

When adding new functionality, make sure to:

1. Add tests for new functions/methods
2. Test both success and error cases
3. Use appropriate fixtures from `conftest.py`
4. Mock external dependencies (API calls, Home Assistant components)
5. Follow the existing test naming conventions

## Continuous Integration

These tests can be integrated into CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements_test.txt
      - run: pytest
```
