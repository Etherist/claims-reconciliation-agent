# Contributing to Claims Reconciliation Agent

Thank you for your interest in contributing! This project welcomes contributions from the community.

## How to Contribute

### 1. Found a Bug?
- Check existing [Issues](https://github.com/your-username/claims-reconciliation-agent/issues) to see if it's already reported
- If not, create a new issue with:
  - Clear title (e.g., "Fuzzy matching fails for names with hyphens")
  - Steps to reproduce
  - Expected vs actual behavior
  - Screenshots if applicable
  - Environment details (OS, Python version)

### 2. Want to Add a Feature?
- Open an issue first to discuss the feature proposal
- Explain the use case and value
- Get feedback before starting implementation

### 3. Ready to Code?

**Development workflow:**

```bash
# Fork the repo → Clone your fork
git clone https://github.com/YOUR-USERNAME/claims-reconciliation-agent.git
cd claims-reconciliation-agent

# Create a feature branch
git checkout -b feature/your-awesome-feature

# Make changes, commit with clear message
git add .
git commit -m "Add fuzzy name weighting for exact provider matches"

# Push to your fork
git push origin feature/your-awesome-feature
```

**Pull Request Guidelines:**

- Title: concise and descriptive (will become commit message)
- Description: explain *what* and *why* (not just *how*)
- Link to related issues (`Closes #123`)
- Include tests for new functionality
- Ensure CI passes (all tests, lint, type-check)
- Keep PR scope focused – avoid unrelated changes

### 4. Code Style

We follow PEP 8 with some adaptations:

- **Line length:** 88 characters (Black default)
- **Type hints:** Required for all function signatures
- **Docstrings:** Google style for public functions
- **Imports:** Sort with `isort` (3rd-party, then stdlib, then local)

```python
def clean_name(name: str) -> str:
    """Standardize patient name.

    Args:
        name: Raw patient name

    Returns:
        Cleaned name (e.g., "J. Smith" → "J Smith")
    """
    return " ".join(name.split()).title().replace(".", "")
```

**Before submitting:**

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/

# Test
pytest
```

---

## Project Structure

```
claims-reconciliation-agent/
├── src/
│   ├── agents/       # Core agents (file_ingestor, data_cleaner, ...)
│   ├── app/          # UI (streamlit_app, cli)
│   └── utils/        # Shared utilities
├── tests/            # Unit + integration tests
├── docs/             # Documentation
├── scripts/          # Helper scripts
├── notebooks/        # Jupyter demos
└── reports/          # Generated output (gitignored)
```

---

## Adding a New Agent

1. Create `src/agents/your_agent.py`
2. Add to `src/agents/__init__.py` (export)
3. Write unit tests in `tests/test_agents.py`
4. Update `docs/agent_workflow.md` if it changes the pipeline
5. Integrate into `src/app/cli.py` and/or `src/app/streamlit_app.py`

Pattern:

```python
class YourAgent:
    def __init__(self, config_param: int = 42):
        self.config = config_param

    def process(self, input_data: pd.DataFrame) -> pd.DataFrame:
        # Do work
        return output

def your_agent_function(input_data) -> output:
    agent = YourAgent()
    return agent.process(input_data)
```

---

## Adding a New Data Format

1. Update `FileIngestor.ingest_*()` method
2. Add extension to `ALLOWED_EXTENSIONS` in config
3. Add parser function in `file_ingestor.py`
4. Write tests for the new format
5. Update docs (`data_format.md`)

---

## Testing

We aim for ≥80% coverage.

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=html
# View: htmlcov/index.html

# Run specific test
pytest tests/test_agents.py::TestFuzzyMatcher::test_exact_match -v
```

**Write tests for:**
- All public functions (input → output)
- Edge cases (empty DataFrames, None values)
- Error conditions (invalid files, missing columns)
- Integration: full pipeline from ingest → report

---

## CI/CD

GitHub Actions automatically runs on every push:

1. **test.yml** – Lint (`flake8`), type-check (`mypy`), test (`pytest`), security scan (`safety`)
2. **docs.yml** – Deploy docs to GitHub Pages on main branch push

Your PR must pass all checks before merging.

---

## Documentation

Update docs as you code:

- Code changes → update `docs/architecture.md` or add inline docstrings
- New features → update `README.md` (Features, Usage sections)
- Bug fixes → add "Fixed in vX.X" note if applicable

Docs use Markdown with Mermaid diagrams for architecture.

---

## Performance Profiling

If your changes affect performance:

```bash
# Time the pipeline
python -m timeit -s "from src.pipeline import reconcile" \
  "reconcile('src/data/sample_claims.csv', 'src/data/sample_payments.csv')"

# Profile memory
pip install memray
memray run src/app/cli.py --claims ... --payments ...
memray flamegraph results.bin
```

Keep pipeline <5 seconds for 100 records.

---

## Questions?

- Open an issue for general questions
- Check `docs/` for architecture details
- Review agent source code (`src/agents/`) for implementation patterns
- See `demo.ipynb` for full pipeline example

---

## License

By contributing, you agree your work will be licensed under the MIT License (see `LICENSE`).

---

**Happy coding! 🏥💻**  
*Let's build better healthcare finance tools together.*
