# Contributing to ConversionBridge

Thank you for your interest in contributing to ConversionBridge! We welcome pull requests, bug reports, and suggestions.

---

## Development Workflow

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/hamid-digitalmarketer/conversionbridge.git
   cd conversionbridge
   ```

2. **Set up Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   pip install -r requirements-dev.txt
   ```

3. **Run Linting & Formatting**:
   ```bash
   ruff check .
   ruff format .
   ```

4. **Run Test Suite**:
   ```bash
   pytest -v
   ```

5. **Commit Conventions**:
   Follow conventional commits:
   - `feat: add new destination adapter`
   - `fix: correct phone hashing regex`
   - `docs: update setup guide`
   - `test: add edge cases for consent engine`

6. **Submit a Pull Request**:
   Ensure all tests pass and code style is clean before opening a PR against `main`.
