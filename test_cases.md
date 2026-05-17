# Test Cases for Charger Tracker

This document outlines the test suite designed to ensure the reliability and deployability of the Charger Tracker application.

## 1. Build & Deployment Safety (Structural Tests)
**File:** `tests/test_build_context.py`
**Purpose:** Prevents regressions in the Docker build process.

| ID | Name | Description | Verification |
|---|---|---|---|
| TC-BS-01 | Essential Files | Checks for presence of `Dockerfile`, `requirements.txt`, `main.py`, `scraper.py`, `.dockerignore`, and `templates/`. | `os.path.exists()` |
| TC-BS-02 | Dockerignore Sanity | Ensures `requirements.txt` is NOT ignored by `.dockerignore` patterns (e.g., `*.txt`). | Regex match against `.dockerignore` content. |
| TC-BS-03 | Dependency Check | Verifies all imports in the Python source code are listed in `requirements.txt`. | Manual or automated script analysis. |

## 2. Scraper Functional Tests
**File:** `tests/test_scraper_functional.py`
**Purpose:** Validates the scraper's ability to navigate the Shadow DOM and extract status.

| ID | Name | Description | Expected Result |
|---|---|---|---|
| TC-SC-01 | Navigation | Verifies scraper can reach the station details page via the provider selection flow. | Page URL contains station ID. |
| TC-SC-02 | Shadow DOM Extraction | Verifies `TreeWalker` can find connector IDs and availability markers. | Result contains `DE*LVP*` strings. |
| TC-SC-03 | Availability Mapping | Checks if markers (1/1, 0/1) are correctly mapped to "Available" or "Occupied". | Status is not "Unknown". |

## 3. Frontend Dashboard Verification (UI)
**File:** `tests/test_frontend.py` (Integrated in Pipeline)
**Purpose:** Ensures the user interface renders correctly.

| ID | Name | Description | Verification |
|---|---|---|---|
| TC-UI-01 | Dashboard Render | Verifies the main heading "Charger Tracker" and the station grid are visible. | Playwright `expect(locator).to_be_visible()` |
| TC-UI-02 | Station Cards | Ensures at least one station card is rendered if data is present. | Locator count > 0 |
| TC-UI-03 | Status Badges | Checks if status badges (Success/Danger) have the correct Bootstrap classes. | CSS class presence. |

## 4. CI/CD Integration
These tests are executed automatically on every push to the implementation branch and must pass before the Docker image is built or pushed.

## Versioning & Branch Protection

### How to release Version 1.3
To tag the current state as version 1.3 and trigger the release pipeline, use the standard git tag command.
Example: `git tag v1.3.0` and then push the tag.

### Branch Protection Rules
**Note:** These must be configured manually in the GitHub Web UI.

1. Go to **Settings** > **Branches** in your GitHub repository.
2. Click **Add rule** for the default branch.
3. Enable the following options:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging** (Select the 'test' job)
   - **Include administrators**

## Manual Pipeline Triggers

The CI/CD pipeline supports manual execution via the **Actions** tab in GitHub.

### Parameters
1. **Skip testing phase**: If checked, the pipeline will bypass the `test` job and proceed directly to building and pushing the Docker image.
2. **Manual release version**: If provided (e.g., `1.3.1`), the pipeline will:
   - Tag the Docker image with this version.
   - Create a corresponding GitHub Release and Git Tag automatically.

### Docker Registry URL
Once pushed, the Docker images are available at:
`ghcr.io/OWNER/REPOSITORY:latest`
(Replace OWNER/REPOSITORY with your actual GitHub path, e.g., `ghcr.io/your-user/your-repo:latest`)

## Test Reporting
After each test execution, HTML reports are uploaded as artifacts.
1. Go to the specific **Workflow Run**.
2. Scroll down to the **Artifacts** section.
3. Download `test-reports` to view detailed `pytest` results for the scraper and UI.
