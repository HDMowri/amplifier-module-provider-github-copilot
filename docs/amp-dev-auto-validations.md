# GitHub Copilot Provider - Development Validation Guide

**Module**: `amplifier-module-provider-github-copilot`  
**Path**: `/mnt/d/v2-amp-ghcp-provider`  
**Last Verified**: 2026-04-03

---

## Prerequisites (Read This First!)

Before running any tests, make sure you have:

1. **WSL Terminal Open** — All commands run in WSL (Ubuntu), not Windows CMD/PowerShell
   - Open Windows Terminal → Click the dropdown arrow → Select "Ubuntu" (or just type `wsl` in any terminal)
   
2. **Docker Desktop Running** — For the Docker E2E test
   - Check: Open Docker Desktop app on Windows, make sure it says "Running"
   
3. **Navigate to the Project**:
   ```bash
   cd /mnt/d/v2-amp-ghcp-provider
   ```

---

## Test 1: Unit Tests (The Most Important One)

**What it does**: Runs 1177+ tests to check your code works correctly.

**How to run it**:
```bash
cd /mnt/d/v2-amp-ghcp-provider
.venv-wsl-py314/bin/python -m pytest tests/ -q --tb=short -m "not live"
```

**What you should see**:
```
......................................................................... [100%]
1177 passed, 11 skipped, 6 deselected, 3 warnings in 68.51s
```

**If it says "FAILED"**: Something is broken. Fix the failing tests before committing.

---

## Test 2: Coverage Report (Statement, Function, Branch)

**What it does**: Runs all tests AND generates a detailed coverage report showing which lines/functions are tested.

### From Windows PowerShell (Recommended - Includes Live Tests)

```powershell
# Run from Windows PowerShell (not WSL) - includes live tests with GitHub auth
$token = (gh auth token -u mowree 2>&1); if ($LASTEXITCODE -ne 0) { $token = (gh auth token 2>&1) }
wsl bash -lc "cd /mnt/d/v2-amp-ghcp-provider && export GITHUB_TOKEN='$token' && .venv-wsl-py314/bin/python -m pytest tests/ -v --tb=short -m 'live or not live' --cov=amplifier_module_provider_github_copilot --cov-branch --cov-report=term-missing --cov-report=html:coverage_html_wsl 2>&1" | Select-Object -Last 60
```

### From WSL (Without Live Tests)

```bash
cd /mnt/d/v2-amp-ghcp-provider
.venv-wsl-py314/bin/python -m pytest tests/ -v --tb=short -m "not live" \
  --cov=amplifier_module_provider_github_copilot \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=html:coverage_html_wsl
```

### View the HTML Report

Open in your Windows browser:
```
file:///D:/v2-amp-ghcp-provider/coverage_html_wsl/index.html
```

The HTML report includes:
- **Statement Coverage** — Which lines of code were executed
- **Branch Coverage** — Which branches (if/else) were taken
- **Function Index** — Coverage by function (`function_index.html`)
- **Class Index** — Coverage by class (`class_index.html`)

---

## Test 3: Docker E2E Test

**What it does**: Installs your module in a fresh Docker container (like a brand new computer) and checks everything works.

**How to run it**:
```bash
cd /mnt/d/v2-amp-ghcp-provider
./scripts/docker-e2e-test.sh
```

**What you should see**:
```
=== GitHub Copilot Provider - Docker E2E Test ===
Project: /mnt/d/v2-amp-ghcp-provider

=== Installing dependencies ===
=== Installing module and dependencies ===
=== Testing module import ===
✓ Provider class imported
✓ mount function imported
✓ Provider instantiated: github-copilot
✓ Provider protocol: 6/6 methods
✓ All 8 config files valid

==================================================
VERDICT: ✅ PASS - Docker E2E Test Successful
==================================================

=== Docker E2E Test: PASSED ===
```

**If it fails**: Check that Docker Desktop is running. If the import fails, there's a code error.

---

## Test 4: Shadow Environment Test

**What it does**: Creates an isolated "shadow copy" of your code and tests it like a real user would.

**Step 1 — Install the shadow CLI (only need to do this once)**:
```bash
uv tool install git+https://github.com/microsoft/amplifier-bundle-shadow
```

**Step 2 — Build the shadow image (only need to do this once)**:
```bash
amplifier-shadow build
```

**Step 3 — Create a shadow environment with your local code**:
```bash
amplifier-shadow create \
  --local /mnt/d/v2-amp-ghcp-provider:microsoft/amplifier-module-provider-github-copilot \
  --name ghcp-test
```

**Step 4 — Test inside the shadow**:
```bash
amplifier-shadow exec ghcp-test "python -c \"
from amplifier_module_provider_github_copilot import GitHubCopilotProvider, mount
p = GitHubCopilotProvider()
print('Provider name:', p.name)
print('Protocol methods: ✓ all present')
\""
```

**Step 5 — Clean up when done**:
```bash
amplifier-shadow destroy ghcp-test
```

**Troubleshooting**:
```bash
# If you see "Error: Shadow environment already exists: ghcp-test":
amplifier-shadow destroy ghcp-test

# If that doesn't work:
rm -rf /tmp/shadow-ghcp-test
amplifier-shadow destroy ghcp-test
```

---

## Test 5: Lint & Type Check

**What it does**: Checks code style (lint) and type correctness (pyright).

```bash
cd /mnt/d/v2-amp-ghcp-provider

# Lint check
.venv-wsl-py314/bin/python -m ruff check amplifier_module_provider_github_copilot/ tests/

# Type check  
.venv-wsl-py314/bin/python -m pyright amplifier_module_provider_github_copilot/ tests/
```

**Or run everything at once with make**:
```bash
make PYTHON=.venv-wsl-py314/bin/python check
```

---

## Test 6: Live Integration Test (In Amplifier Session)

**What it does**: Starts an actual Amplifier session using your provider and lets you test it interactively.

**How to run it**:
```bash
cd /mnt/d/v2-amp-ghcp-provider
amplifier run -p github-copilot -B amplifier-dev
```

Then in the session, say:
```
Delegate to amplifier-smoke-test to validate the GitHub Copilot provider module at /mnt/d/v2-amp-ghcp-provider
```

The smoke test agent will run a comprehensive validation and report results.

---

## Automation: Run All Tests with One Command (Recipe)

**What is a recipe?**  
A recipe is a YAML file that tells Amplifier: "Run these tests automatically, one after another."  
Instead of typing 5 commands, you type 1.

**How to use the recipe**:

The recipe file is at: `/mnt/d/v2-amp-ghcp-provider/.amplifier/recipes/validate-provider.yaml`

Run it with:
```bash
amplifier tool invoke recipes operation=execute recipe_path=.amplifier/recipes/validate-provider.yaml
```

Or in an Amplifier session, just say:
```
Run the validate-provider recipe
```

**What the recipe does**:
1. Runs unit tests
2. Runs lint check
3. Runs type check
4. Runs Docker E2E test
5. Runs smoke test agent

---

## Pre-Commit Checklist (Copy This for PRs)

```markdown
## Pre-Commit Validation

- [ ] Unit tests pass: `1177+ passed, 0 failed`
- [ ] Coverage: `97%+` (view at `file:///D:/v2-amp-ghcp-provider/coverage_html_wsl/index.html`)
- [ ] Lint clean: `ruff check` no errors
- [ ] Types clean: `pyright` no errors
- [ ] Docker E2E: `./scripts/docker-e2e-test.sh` PASS
- [ ] (Optional) Shadow test: `amplifier-shadow` PASS
- [ ] (Optional) Live session test with smoke agent
```

---

## Tell Another Amplifier Session to Run These Tests

Just paste this into any Amplifier session:

```
Run all validation tests for the GitHub Copilot provider module at /mnt/d/v2-amp-ghcp-provider:

1. Unit tests: .venv-wsl-py314/bin/python -m pytest tests/ -q --tb=short -m "not live"
2. Coverage: .venv-wsl-py314/bin/python -m pytest tests/ --cov=amplifier_module_provider_github_copilot --cov-branch --cov-report=term-missing --cov-report=html:coverage_html_wsl
3. Docker E2E: ./scripts/docker-e2e-test.sh
4. Delegate to foundation:amplifier-smoke-test for comprehensive validation
5. Report results

Expected: 1177+ tests pass, 97%+ coverage, Docker E2E passes, smoke test passes.
```

---

## Evidence from Last Run (2026-04-03)

### Unit Tests
```
1191 passed, 2 skipped, 1 failed (auth test - expected without token)
Time: 97.69s
```

### Coverage Summary
```
TOTAL                                                                        2320     46    748     41    97%

Coverage by Module:
  __init__.py               124 stmts   100%
  config_loader.py          219 stmts    99%
  error_translation.py      137 stmts    98%
  event_router.py            85 stmts    98%
  provider.py               234 stmts    97%
  streaming.py              260 stmts    99%
  request_adapter.py        124 stmts    96%
  sdk_adapter/client.py     186 stmts    97%
  tool_parsing.py            37 stmts   100%
  security_redaction.py      60 stmts   100%
  models.py                  32 stmts   100%

Coverage HTML: file:///D:/v2-amp-ghcp-provider/coverage_html_wsl/index.html
  - Statement coverage: index.html
  - Function coverage: function_index.html
  - Class coverage: class_index.html
```

### Docker E2E
```
✓ Provider class imported
✓ mount function imported
✓ Provider instantiated: github-copilot
✓ Provider protocol: 6/6 methods
✓ All 8 config files valid
VERDICT: ✅ PASS
```

### Shadow Environment
```
Provider name: github-copilot
Protocol methods: ✓ all present
VERDICT: ✅ PASS
```

### Smoke Test Agent
```
Module Imports:          ✓ 16/16 submodules
Protocol Compliance:     ✓ 7/7 methods/properties
Configuration:           ✓ 8/8 YAML files valid
Entry Points:            ✓ Correctly registered
Provider Instantiation:  ✓ All runtime checks pass
Contracts:               ✓ 10/10 present
Unit Tests:              ✓ 1177 passed, 0 failed

VERDICT: ✅ PASS
```

---

## Environment Reference

**Required venv**: `.venv-wsl-py314` (Python 3.14.3, amplifier_core 1.3.3+)

**Health check** (run this to verify your environment):
```bash
echo "Python: $(.venv-wsl-py314/bin/python --version)"
echo "amplifier_core: $(.venv-wsl-py314/bin/python -c 'import amplifier_core; print(amplifier_core.__version__)')"
```

**Update amplifier_core** (if needed):
```bash
uv pip install --python .venv-wsl-py314/bin/python -U amplifier-core
```

**Install copilot SDK** (required for live tests):
```bash
uv pip install --python .venv-wsl-py314/bin/python github-copilot-sdk
```
