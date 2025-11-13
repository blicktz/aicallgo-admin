# Cold Call Dialer - Testing Strategy

**Version**: 1.0
**Date**: 2025-11-12

---

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Unit Testing](#unit-testing)
3. [Integration Testing](#integration-testing)
4. [End-to-End Testing](#end-to-end-testing)
5. [Load Testing](#load-testing)
6. [Browser Compatibility Testing](#browser-compatibility-testing)
7. [Test Data & Fixtures](#test-data--fixtures)
8. [CI/CD Integration](#cicd-integration)

---

## Testing Overview

### Testing Pyramid

```
                /\
               /  \
              / E2E \          ← 10% (Full user flows)
             /______\
            /        \
           /  Integ   \        ← 30% (API, services)
          /____________\
         /              \
        /      Unit      \     ← 60% (Functions, classes)
       /________________\
```

### Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Outcall-agent cold_call module | 90%+ | TBD |
| Admin-board components | 80%+ | TBD |
| API endpoints | 95%+ | TBD |
| Critical paths | 100% | TBD |

### Testing Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| **pytest** | Unit & integration testing | `pip install pytest` |
| **pytest-asyncio** | Async test support | `pip install pytest-asyncio` |
| **pytest-cov** | Coverage reporting | `pip install pytest-cov` |
| **pytest-mock** | Mocking framework | `pip install pytest-mock` |
| **responses** | HTTP mocking | `pip install responses` |
| **factory-boy** | Test data factories | `pip install factory-boy` |
| **playwright** | E2E browser testing | `pip install playwright` |
| **locust** | Load testing | `pip install locust` |

---

## Unit Testing

### Outcall-Agent Unit Tests

**Location**: `services/outcall-agent/tests/unit/cold_call/`

#### Test: Models Validation

**File**: `test_models.py`

```python
import pytest
from pydantic import ValidationError
from app.cold_call.models import ColdCallInitiateRequest

def test_valid_phone_number():
    """Test valid E.164 phone number."""
    request = ColdCallInitiateRequest(
        to_phone="+15551234567",
        from_phone="+15559876543",
        provider="twilio"
    )
    assert request.to_phone == "+15551234567"
    assert request.provider == "twilio"

def test_invalid_phone_number():
    """Test invalid phone number format."""
    with pytest.raises(ValidationError) as exc_info:
        ColdCallInitiateRequest(
            to_phone="555-123-4567",  # Invalid format
            provider="twilio"
        )
    assert "phone" in str(exc_info.value).lower()

def test_default_provider():
    """Test default provider is twilio."""
    request = ColdCallInitiateRequest(to_phone="+15551234567")
    assert request.provider == "twilio"

@pytest.mark.parametrize("phone,valid", [
    ("+15551234567", True),
    ("+442071234567", True),
    ("5551234567", False),
    ("+1-555-123-4567", False),
    ("", False),
])
def test_phone_number_validation(phone, valid):
    """Test various phone number formats."""
    if valid:
        request = ColdCallInitiateRequest(
            to_phone=phone,
            provider="twilio"
        )
        assert request.to_phone == phone
    else:
        with pytest.raises(ValidationError):
            ColdCallInitiateRequest(
                to_phone=phone,
                provider="twilio"
            )
```

#### Test: Handler Factory

**File**: `test_handler_factory.py`

```python
import pytest
from app.cold_call.handler_factory import get_cold_call_handler
from app.cold_call.twilio_handler import TwilioColdCallHandler
from app.cold_call.telnyx_handler import TelnyxColdCallHandler

def test_get_twilio_handler():
    """Test factory returns Twilio handler."""
    handler = get_cold_call_handler("twilio")
    assert isinstance(handler, TwilioColdCallHandler)

def test_get_telnyx_handler():
    """Test factory returns Telnyx handler."""
    handler = get_cold_call_handler("telnyx")
    assert isinstance(handler, TelnyxColdCallHandler)

def test_invalid_provider():
    """Test factory raises error for invalid provider."""
    with pytest.raises(ValueError) as exc_info:
        get_cold_call_handler("invalid_provider")
    assert "unsupported" in str(exc_info.value).lower()

def test_case_insensitive():
    """Test provider name is case insensitive."""
    handler1 = get_cold_call_handler("TWILIO")
    handler2 = get_cold_call_handler("twilio")
    assert type(handler1) == type(handler2)
```

#### Test: Twilio Handler (Mocked)

**File**: `test_twilio_handler.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.cold_call.twilio_handler import TwilioColdCallHandler
from app.telephony.twilio_provider import TwilioProvider

@pytest.fixture
def mock_twilio_provider():
    """Create mock Twilio provider."""
    provider = Mock(spec=TwilioProvider)
    provider.client = Mock()
    provider.account_sid = "AC123"
    provider.auth_token = "token123"
    return provider

@pytest.fixture
def handler(mock_twilio_provider):
    """Create handler with mocked provider."""
    return TwilioColdCallHandler(mock_twilio_provider)

@pytest.mark.asyncio
async def test_add_phone_participant(handler, mock_twilio_provider):
    """Test adding phone participant to conference."""
    # Mock Twilio client response
    mock_call = Mock()
    mock_call.sid = "CA123abc"
    mock_twilio_provider.client.calls.create.return_value = mock_call

    # Execute
    call_sid = await handler.add_phone_participant(
        conference_sid="CF123",
        to_phone="+15551234567",
        from_phone="+15559876543"
    )

    # Verify
    assert call_sid == "CA123abc"
    mock_twilio_provider.client.calls.create.assert_called_once()

@pytest.mark.asyncio
async def test_control_participant_mute(handler, mock_twilio_provider):
    """Test muting participant."""
    # Execute
    success = await handler.control_participant(
        conference_sid="CF123",
        participant_sid="PA123",
        action="mute",
        value=True
    )

    # Verify
    assert success is True
    mock_twilio_provider.client.conferences.assert_called_with("CF123")

@pytest.mark.asyncio
async def test_end_conference(handler, mock_twilio_provider):
    """Test ending conference."""
    # Execute
    success = await handler.end_conference("CF123")

    # Verify
    assert success is True
    mock_twilio_provider.client.conferences.assert_called_with("CF123")
```

### Admin-Board Unit Tests

**Location**: `services/admin-board/tests/unit/`

#### Test: CSV Parser

**File**: `test_csv_parser.py`

```python
import pytest
import pandas as pd
from io import StringIO
from components.cold_call.csv_parser import CSVParser

@pytest.fixture
def parser():
    return CSVParser()

def test_valid_csv(parser):
    """Test parsing valid CSV."""
    csv_data = """name,company,phone,title
John Doe,Acme Inc,+15551234567,CEO
Jane Smith,Tech Corp,+15559876543,CTO"""

    file = StringIO(csv_data)
    contacts = parser.parse_contacts(file)

    assert len(contacts) == 2
    assert contacts[0].name == "John Doe"
    assert contacts[0].phone == "+15551234567"
    assert contacts[1].title == "CTO"

def test_missing_required_column(parser):
    """Test CSV with missing required column."""
    csv_data = """name,company,title
John Doe,Acme Inc,CEO"""

    file = StringIO(csv_data)
    with pytest.raises(ValueError) as exc_info:
        parser.parse_contacts(file)
    assert "phone" in str(exc_info.value).lower()

def test_optional_title_column(parser):
    """Test CSV without optional title column."""
    csv_data = """name,company,phone
John Doe,Acme Inc,+15551234567"""

    file = StringIO(csv_data)
    contacts = parser.parse_contacts(file)

    assert len(contacts) == 1
    assert contacts[0].title is None

def test_invalid_phone_number(parser):
    """Test CSV with invalid phone numbers."""
    csv_data = """name,company,phone
John Doe,Acme Inc,555-1234"""

    file = StringIO(csv_data)
    # Should skip invalid rows or raise error
    # Behavior depends on implementation
    contacts = parser.parse_contacts(file)
    assert len(contacts) == 0  # or raise error
```

#### Test: Phone Validator

**File**: `test_phone_validator.py`

```python
import pytest
from components.cold_call.phone_validator import PhoneValidator

@pytest.fixture
def validator():
    return PhoneValidator()

@pytest.mark.parametrize("phone,expected", [
    ("+15551234567", True),
    ("+442071234567", True),
    ("+33123456789", True),
    ("5551234567", False),
    ("+1-555-123-4567", False),
    ("", False),
    (None, False),
])
def test_validate_e164(validator, phone, expected):
    """Test E.164 validation."""
    assert validator.validate_e164(phone) == expected

def test_format_e164_us(validator):
    """Test formatting US number to E.164."""
    result = validator.format_e164("5551234567", country_code="US")
    assert result == "+15551234567"

def test_format_e164_uk(validator):
    """Test formatting UK number to E.164."""
    result = validator.format_e164("2071234567", country_code="GB")
    assert result == "+442071234567"

def test_format_invalid_number(validator):
    """Test formatting invalid number."""
    with pytest.raises(ValueError):
        validator.format_e164("123", country_code="US")
```

#### Test: API Client

**File**: `test_api_client.py`

```python
import pytest
import responses
from components.cold_call.api_client import ColdCallAPIClient

@pytest.fixture
def client():
    return ColdCallAPIClient(
        base_url="http://outcall-agent:8000/aicallgo/api/v1/cold-call",
        api_key="test-key"
    )

@responses.activate
@pytest.mark.asyncio
async def test_initiate_call_success(client):
    """Test successful call initiation."""
    # Mock HTTP response
    responses.add(
        responses.POST,
        "http://outcall-agent:8000/aicallgo/api/v1/cold-call/initiate",
        json={
            "conference_sid": "CF123",
            "call_sid": "CA123",
            "status": "initiated"
        },
        status=201
    )

    # Execute
    result = await client.initiate_call(
        to_phone="+15551234567",
        from_phone="+15559876543"
    )

    # Verify
    assert result["conference_sid"] == "CF123"
    assert result["status"] == "initiated"
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["X-API-Key"] == "test-key"

@responses.activate
@pytest.mark.asyncio
async def test_initiate_call_error(client):
    """Test call initiation error handling."""
    # Mock HTTP error response
    responses.add(
        responses.POST,
        "http://outcall-agent:8000/aicallgo/api/v1/cold-call/initiate",
        json={"error": {"message": "Invalid phone number"}},
        status=400
    )

    # Execute and verify exception
    with pytest.raises(Exception) as exc_info:
        await client.initiate_call(to_phone="invalid")
    assert "400" in str(exc_info.value)
```

---

## Integration Testing

### API Endpoint Integration Tests

**Location**: `services/outcall-agent/tests/integration/`

#### Test: Full Call Flow (with Twilio Sandbox)

**File**: `test_call_flow_integration.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def api_key():
    return "test-internal-key"

@pytest.mark.integration
def test_initiate_call_endpoint(client, api_key):
    """Test /initiate endpoint integration."""
    response = client.post(
        "/aicallgo/api/v1/cold-call/initiate",
        json={
            "to_phone": "+15551234567",
            "from_phone": "+15559876543",
            "provider": "twilio"
        },
        headers={"X-API-Key": api_key}
    )

    assert response.status_code == 201
    data = response.json()
    assert "conference_sid" in data
    assert "call_sid" in data
    assert data["provider"] == "twilio"

@pytest.mark.integration
def test_status_endpoint(client, api_key):
    """Test /status endpoint integration."""
    # First create a conference
    init_response = client.post(
        "/aicallgo/api/v1/cold-call/initiate",
        json={"to_phone": "+15551234567", "provider": "twilio"},
        headers={"X-API-Key": api_key}
    )
    conference_sid = init_response.json()["conference_sid"]

    # Then get status
    status_response = client.get(
        f"/aicallgo/api/v1/cold-call/status/{conference_sid}",
        headers={"X-API-Key": api_key}
    )

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["conference_sid"] == conference_sid

@pytest.mark.integration
def test_unauthorized_request(client):
    """Test request without API key."""
    response = client.post(
        "/aicallgo/api/v1/cold-call/initiate",
        json={"to_phone": "+15551234567"}
    )
    assert response.status_code == 401
```

### Database Integration Tests

**File**: `test_database_integration.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, User

@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.mark.integration
def test_save_call_log(db_session):
    """Test saving call log to database."""
    # Implementation depends on if you're storing call logs
    # This is a placeholder example
    pass
```

---

## End-to-End Testing

### E2E Test Setup

**Location**: `services/admin-board/tests/e2e/`

**File**: `test_cold_call_e2e.py`

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session")
def browser():
    """Launch browser for testing."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    """Create new page for each test."""
    context = browser.new_context(
        permissions=["microphone"]  # Grant microphone permission
    )
    page = context.new_page()
    yield page
    context.close()

@pytest.mark.e2e
def test_login_and_navigate_to_dialer(page: Page):
    """Test user can login and navigate to dialer."""
    # Navigate to admin board
    page.goto("http://localhost:8501")

    # Login
    page.fill("input[name='username']", "admin")
    page.fill("input[name='password']", "password")
    page.click("button:has-text('Login')")

    # Navigate to dialer
    page.goto("http://localhost:8501/16_📞_Cold_Call_Dialer")

    # Verify page loaded
    expect(page.locator("h1")).to_contain_text("Cold Call Dialer")

@pytest.mark.e2e
def test_upload_csv(page: Page):
    """Test CSV upload functionality."""
    # Login and navigate (reuse from above)
    login_and_navigate(page)

    # Upload CSV
    page.set_input_files(
        "input[type='file']",
        "tests/fixtures/test_contacts.csv"
    )

    # Verify contacts displayed
    expect(page.locator("table")).to_be_visible()
    expect(page.locator("tbody tr")).to_have_count(5)

@pytest.mark.e2e
def test_initiate_call(page: Page):
    """Test initiating a call."""
    # Login, navigate, upload CSV
    setup_dialer_with_contacts(page)

    # Click first dial button
    page.click("button:has-text('Dial'):first")

    # Verify modal appeared
    expect(page.locator("[role='dialog']")).to_be_visible()
    expect(page.locator("text='Dialing...'")).to_be_visible()

    # Wait for connection (timeout after 10s)
    expect(page.locator("text='Connected'")).to_be_visible(timeout=10000)

@pytest.mark.e2e
def test_mute_unmute(page: Page):
    """Test mute/unmute controls."""
    # Setup call (reuse from above)
    setup_active_call(page)

    # Click mute button
    mute_button = page.locator("button:has-text('Mute')")
    mute_button.click()
    expect(mute_button).to_have_text("Unmute")

    # Click unmute
    mute_button.click()
    expect(mute_button).to_have_text("Mute")

@pytest.mark.e2e
def test_end_call_and_log(page: Page):
    """Test ending call and logging outcome."""
    # Setup active call
    setup_active_call(page)

    # End call
    page.click("button:has-text('End Call')")

    # Verify log form appeared
    expect(page.locator("select[name='outcome']")).to_be_visible()
    expect(page.locator("textarea[name='notes']")).to_be_visible()

    # Fill out log
    page.select_option("select[name='outcome']", "connected")
    page.fill("textarea[name='notes']", "Great conversation")

    # Save
    page.click("button:has-text('Save')")

    # Verify modal closed
    expect(page.locator("[role='dialog']")).not_to_be_visible()

    # Verify contact status updated
    expect(page.locator("tbody tr:first-child")).to_contain_text("Connected")
```

---

## Load Testing

### Locust Load Test

**File**: `tests/load/locustfile.py`

```python
from locust import HttpUser, task, between
import random

class ColdCallUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://outcall-agent:8000"

    def on_start(self):
        """Setup: Get API key."""
        self.api_key = "test-internal-key"
        self.headers = {"X-API-Key": self.api_key}

    @task(3)
    def initiate_call(self):
        """Simulate initiating a cold call."""
        phone = f"+1555{random.randint(1000000, 9999999)}"
        response = self.client.post(
            "/aicallgo/api/v1/cold-call/initiate",
            json={
                "to_phone": phone,
                "provider": "twilio"
            },
            headers=self.headers
        )
        if response.status_code == 201:
            data = response.json()
            self.conference_sid = data.get("conference_sid")

    @task(1)
    def get_status(self):
        """Simulate checking call status."""
        if hasattr(self, 'conference_sid'):
            self.client.get(
                f"/aicallgo/api/v1/cold-call/status/{self.conference_sid}",
                headers=self.headers
            )

    @task(1)
    def end_call(self):
        """Simulate ending a call."""
        if hasattr(self, 'conference_sid'):
            self.client.post(
                "/aicallgo/api/v1/cold-call/end",
                json={"conference_sid": self.conference_sid},
                headers=self.headers
            )

# Run with:
# locust -f tests/load/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089 to configure and start load test
```

### Load Test Scenarios

#### Scenario 1: Normal Load
- **Users**: 10 concurrent
- **Duration**: 5 minutes
- **Expected**: < 2s response time, 0% errors

#### Scenario 2: Peak Load
- **Users**: 50 concurrent
- **Duration**: 10 minutes
- **Expected**: < 5s response time, < 1% errors

#### Scenario 3: Stress Test
- **Users**: 100+ concurrent
- **Duration**: 15 minutes
- **Expected**: Identify breaking point

---

## Browser Compatibility Testing

### Target Browsers

| Browser | Versions | Priority |
|---------|----------|----------|
| Chrome | Latest 2 | High |
| Firefox | Latest 2 | High |
| Safari | Latest 2 | Medium |
| Edge | Latest 2 | Medium |

### WebRTC Compatibility

Test checklist per browser:
- [ ] Microphone permission prompt works
- [ ] Audio input detected
- [ ] WebRTC connection established
- [ ] Audio quality acceptable
- [ ] Mute/unmute works
- [ ] No console errors

### Testing Tools

```bash
# Install playwright browsers
playwright install

# Run cross-browser tests
pytest tests/e2e/ --browser=chromium
pytest tests/e2e/ --browser=firefox
pytest tests/e2e/ --browser=webkit
```

---

## Test Data & Fixtures

### Test Contacts CSV

**File**: `tests/fixtures/test_contacts.csv`

```csv
name,company,phone,title
John Doe,Acme Inc,+15551234567,CEO
Jane Smith,Tech Corp,+15559876543,CTO
Bob Johnson,StartupXYZ,+15555556789,Founder
Alice Williams,BigCo,+15551112222,VP Sales
Charlie Brown,MediumCo,+15553334444,Manager
```

### Mock Twilio Responses

**File**: `tests/fixtures/twilio_responses.json`

```json
{
  "conference_created": {
    "sid": "CF123abc456def",
    "friendly_name": "COLD_CALL_test_123",
    "status": "init"
  },
  "call_created": {
    "sid": "CA789ghi012jkl",
    "to": "+15551234567",
    "from": "+15559876543",
    "status": "queued"
  },
  "participant_added": {
    "call_sid": "CA789ghi012jkl",
    "conference_sid": "CF123abc456def",
    "muted": false,
    "hold": false
  }
}
```

---

## CI/CD Integration

### GitHub Actions Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Test Cold Call Dialer

on:
  push:
    branches: [main, staging, feature/cold-call-dialer]
  pull_request:
    branches: [main, staging]

jobs:
  unit-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd services/outcall-agent
          pip install poetry
          poetry install --with dev

      - name: Run unit tests
        run: |
          cd services/outcall-agent
          poetry run pytest tests/unit/ -v --cov=app/cold_call --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./services/outcall-agent/coverage.xml

  integration-tests:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd services/outcall-agent
          pip install poetry
          poetry install --with dev

      - name: Run integration tests
        run: |
          cd services/outcall-agent
          poetry run pytest tests/integration/ -v
        env:
          REDIS_URL: redis://localhost:6379/0
          TWILIO_ACCOUNT_SID: ${{ secrets.TWILIO_TEST_ACCOUNT_SID }}
          TWILIO_AUTH_TOKEN: ${{ secrets.TWILIO_TEST_AUTH_TOKEN }}

  e2e-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install Playwright
        run: |
          pip install playwright pytest-playwright
          playwright install

      - name: Start services
        run: |
          docker-compose up -d
          sleep 10  # Wait for services to start

      - name: Run E2E tests
        run: |
          cd services/admin-board
          pytest tests/e2e/ -v

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-screenshots
          path: services/admin-board/test-results/
```

### Pre-commit Hooks

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: bash -c 'cd services/outcall-agent && poetry run pytest tests/unit/ -x'
        language: system
        pass_filenames: false

      - id: coverage-check
        name: Check test coverage
        entry: bash -c 'cd services/outcall-agent && poetry run pytest tests/unit/ --cov=app/cold_call --cov-fail-under=80'
        language: system
        pass_filenames: false
```

---

## Test Execution

### Running All Tests

```bash
# Run all unit tests
cd services/outcall-agent
poetry run pytest tests/unit/ -v

# Run all integration tests
poetry run pytest tests/integration/ -v --integration

# Run all E2E tests
cd services/admin-board
pytest tests/e2e/ -v --headed  # Shows browser

# Run load tests
cd services/outcall-agent
locust -f tests/load/locustfile.py
```

### Running Specific Tests

```bash
# Run single test file
pytest tests/unit/cold_call/test_models.py -v

# Run single test function
pytest tests/unit/cold_call/test_models.py::test_valid_phone_number -v

# Run tests matching pattern
pytest -k "phone_number" -v

# Run with coverage
pytest tests/unit/ --cov=app/cold_call --cov-report=html
open htmlcov/index.html
```

### Test Markers

```python
# In pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
]

# Run only unit tests
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run integration and e2e
pytest -m "integration or e2e"
```

---

## Coverage Reports

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest tests/unit/ --cov=app/cold_call --cov-report=html

# Generate XML for CI
pytest tests/unit/ --cov=app/cold_call --cov-report=xml

# Show missing lines
pytest tests/unit/ --cov=app/cold_call --cov-report=term-missing
```

### Coverage Requirements

| Component | Minimum Coverage |
|-----------|-----------------|
| Models | 95% |
| Handlers | 90% |
| Endpoints | 95% |
| Utils | 85% |
| Overall | 90% |

---

## Appendix

### Useful Testing Commands

```bash
# Run tests with verbose output
pytest -vv

# Run tests in parallel
pytest -n auto

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run last failed tests
pytest --lf

# Run with pdb on failure
pytest --pdb
```

### Mock Data Generators

```python
# Factory Boy example
import factory
from app.cold_call.models import Contact

class ContactFactory(factory.Factory):
    class Meta:
        model = Contact

    name = factory.Faker('name')
    company = factory.Faker('company')
    phone = factory.LazyFunction(
        lambda: f"+1555{factory.Faker('random_int', min=1000000, max=9999999)}"
    )
    title = factory.Faker('job')

# Usage
contact = ContactFactory()
contacts = ContactFactory.create_batch(10)
```

---

## References

- [pytest Documentation](https://docs.pytest.org/)
- [Playwright Python](https://playwright.dev/python/)
- [Locust Documentation](https://docs.locust.io/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
