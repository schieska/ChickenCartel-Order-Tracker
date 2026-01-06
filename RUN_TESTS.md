# How to Run Tests

## Prerequisites

1. **Install Python 3.9 or higher**
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Verify Python is installed**
   ```bash
   python --version
   # Should show Python 3.9.x or higher
   ```

## Step-by-Step Instructions

### Option 1: Using Virtual Environment (Recommended)

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **Linux/Mac:**
     ```bash
     source venv/bin/activate
     ```

3. **Install test dependencies:**
   ```bash
   pip install -r requirements_test.txt
   ```

4. **Run all tests:**
   ```bash
   pytest
   ```

### Option 2: Install Dependencies Globally (Not Recommended)

1. **Install test dependencies:**
   ```bash
   pip install -r requirements_test.txt
   ```

2. **Run all tests:**
   ```bash
   pytest
   ```

## Test Commands

### Run All Tests
```bash
pytest
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Specific Test File
```bash
# Test config flow
pytest tests/test_config_flow.py

# Test coordinator
pytest tests/test_coordinator.py

# Test sensor
pytest tests/test_sensor.py

# Test constants
pytest tests/test_const.py

# Test initialization
pytest tests/test_init.py
```

### Run Specific Test Class
```bash
pytest tests/test_config_flow.py::TestValidateOrderId
```

### Run Specific Test Function
```bash
pytest tests/test_config_flow.py::TestValidateOrderId::test_valid_uuid
```

### Run Tests with Coverage Report
```bash
# Install coverage tool first
pip install pytest-cov

# Run tests with coverage
pytest --cov=custom_components.chickencartel --cov-report=html

# View coverage report
# Open htmlcov/index.html in your browser
```

### Run Tests and Stop on First Failure
```bash
pytest -x
```

### Run Tests and Show Print Statements
```bash
pytest -s
```

## Troubleshooting

### Issue: "pytest: command not found"
**Solution:** Make sure pytest is installed:
```bash
pip install pytest
```

### Issue: "ModuleNotFoundError: No module named 'homeassistant'"
**Solution:** Install Home Assistant test dependencies:
```bash
pip install -r requirements_test.txt
```

### Issue: Import errors
**Solution:** Make sure you're running tests from the project root directory:
```bash
cd C:\Users\gvroi\local\ChickenCartel-Order-Tracker
pytest
```

### Issue: Permission errors on Windows
**Solution:** Run PowerShell as Administrator, or use:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: SocketBlockedError on Windows
**Problem:** Home Assistant tests require socket access for the event loop, which conflicts with pytest-socket on Windows.

**Solutions:**
1. **Use WSL (Windows Subsystem for Linux)** - Recommended:
   ```bash
   # Install WSL if not already installed
   wsl --install
   
   # Then run tests in WSL
   wsl
   cd /mnt/c/Users/gvroi/local/ChickenCartel-Order-Tracker
   pip install -r requirements_test.txt
   pytest
   ```

2. **Use Docker** (if available):
   ```bash
   docker run -it -v ${PWD}:/app python:3.11 bash
   cd /app
   pip install -r requirements_test.txt
   pytest
   ```

3. **Run on Linux/Mac** - Tests work best on Unix-like systems

**Note:** This is a known limitation of Home Assistant's test framework on Windows. The tests are designed to run in CI/CD environments (typically Linux) and may have issues on Windows due to event loop socket requirements.

## Expected Output

When tests run successfully, you should see output like:
```
============================= test session starts ==============================
platform win32 -- Python 3.11.x, pytest-7.4.0, pytest-asyncio-0.21.0
collected 25 items

tests/test_config_flow.py ..........                                    [ 40%]
tests/test_const.py .....                                               [ 60%]
tests/test_coordinator.py ...........                                  [ 88%]
tests/test_init.py ...                                                 [100%]

============================= 25 passed in 2.34s ==============================
```

## Quick Start (Copy-Paste)

For Windows PowerShell:
```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements_test.txt

# Run tests
pytest -v
```
