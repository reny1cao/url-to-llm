# Contributing to URL → LLM Pipeline

Thank you for your interest in contributing to URL → LLM Pipeline! We welcome contributions from the community.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Issues

1. Check if the issue already exists in the [issue tracker](https://github.com/your-org/url-to-llm/issues)
2. If not, create a new issue using the appropriate template
3. Provide as much detail as possible, including:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment details

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following our coding standards
4. Write or update tests as needed
5. Ensure all tests pass:
   ```bash
   make test
   ```
6. Commit your changes using conventional commits:
   ```bash
   git commit -m "feat: add new feature"
   ```
7. Push to your fork and submit a pull request

### Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org/) for our commit messages:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks
- `perf:` Performance improvements

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- Poetry (for Python dependency management)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/url-to-llm.git
   cd url-to-llm
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Start the development environment:
   ```bash
   docker-compose up -d
   ```

4. Install dependencies for local development:
   ```bash
   # Backend
   cd backend
   poetry install
   
   # Frontend
   cd ../frontend
   npm install
   
   # Crawler
   cd ../crawler
   poetry install
   ```

## Coding Standards

### Python (Backend & Crawler)

- Follow PEP 8
- Use type hints
- Maximum line length: 88 characters (Black default)
- Run linters before committing:
  ```bash
  poetry run black .
  poetry run ruff check .
  poetry run mypy .
  ```

### TypeScript/JavaScript (Frontend)

- Use TypeScript for all new code
- Follow the ESLint configuration
- Use functional components with hooks for React
- Run linters before committing:
  ```bash
  npm run lint
  npm run type-check
  ```

### General Guidelines

- Write clear, self-documenting code
- Add comments for complex logic
- Keep functions small and focused
- Write tests for new functionality
- Update documentation as needed

## Testing

### Running Tests

```bash
# All tests
make test

# Backend tests
cd backend && poetry run pytest

# Frontend tests
cd frontend && npm test

# Crawler tests
cd crawler && poetry run pytest
```

### Writing Tests

- Aim for >80% code coverage
- Test edge cases and error conditions
- Use descriptive test names
- Mock external dependencies

## Documentation

- Update README files when adding new features
- Add docstrings to Python functions and classes
- Add JSDoc comments to TypeScript functions
- Update API documentation when changing endpoints

## Review Process

1. All pull requests require at least one review
2. CI checks must pass
3. No merge conflicts
4. Follow the pull request template

## Questions?

If you have questions, feel free to:
- Open a [discussion](https://github.com/your-org/url-to-llm/discussions)
- Ask in the issue tracker
- Contact the maintainers

Thank you for contributing! 🎉