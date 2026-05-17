import pytest
from playwright.sync_api import Page, expect
import subprocess
import time
import os
import signal
import requests

@pytest.fixture(scope="module", autouse=True)
def start_server():
    # Ensure data directory exists for server
    os.makedirs("data", exist_ok=True)
    # Start the server in the background
    proc = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )

    # Wait for server to be responsive
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8000")
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        pytest.fail("Server failed to start in time")

    yield
    # Kill the server process group
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass

def test_dashboard_header(page: Page):
    page.goto("http://localhost:8000")
    expect(page.get_by_role("heading", name="Charger Tracker")).to_be_visible()

def test_home_automation_section(page: Page):
    page.goto("http://localhost:8000")
    expect(page.get_by_text("Home Automation Integration")).to_be_visible()
