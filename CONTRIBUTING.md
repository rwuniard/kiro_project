# Contributing to RAG File Processor

Welcome to the RAG File Processor project! This guide outlines our trunk-based development workflow and contribution standards.

## 🌳 Trunk-Based Development Workflow

We use trunk-based development to ensure fast integration, high quality, and continuous delivery.

### Core Principles

- **Main branch is always deployable**
- **Short-lived feature branches** (1-3 days max)
- **Small, frequent commits** with clear messages
- **Comprehensive automated testing** before merge
- **85% code coverage minimum** per file
- **Automated security scanning** and code review

## 🚀 Quick Start

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/kiro_project.git
   cd kiro_project
   ```

2. **Set up development environment**
   ```bash
   # Install uv for dependency management
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install dependencies
   uv sync --all-extras
   
   # Verify setup
   uv run pytest --version
   ```

3. **Run tests to ensure everything works**
   ```bash
   uv run pytest -v
   ```

## 🔄 Development Workflow

### 1. Create Feature Branch

```bash
# Sync with main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

**Branch Naming Conventions:**
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test improvements

### 2. Develop Your Changes

- **Write tests first** (TDD approach recommended)
- **Make small, focused commits**
- **Follow existing code patterns** and conventions
- **Add documentation** for new features

```bash
# Run tests frequently during development
uv run pytest tests/

# Run specific test files
uv run pytest tests/test_your_module.py -v

# Check coverage
uv run pytest --cov=src --cov-report=html
```

### 3. Ensure Quality Gates Pass

Before pushing, verify your changes meet all requirements:

```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=xml --cov-fail-under=90 -v

# Security scan (optional but recommended)
uv add --dev bandit[toml]
uv run bandit -r src/

# Check dependency security
uv add --dev safety  
uv run safety scan
```

### 4. Push and Create Pull Request

```bash
# Push feature branch
git push origin feature/your-feature-name

# Create PR via GitHub CLI (optional)
gh pr create --title "Your PR Title" --body "Description of changes"
```

## 🎯 Pull Request Requirements

### Automated Quality Gates (All Must Pass)

- ✅ **All unit tests pass** (450+ tests)
- ✅ **85% code coverage per file** (enforced)
- ✅ **90% total project coverage**
- ✅ **Security vulnerability scan** passes
- ✅ **Docker image builds** successfully
- ✅ **Integration tests** pass

### Manual Review Requirements

- [ ] **Code review** by team member
- [ ] **Business logic** validation
- [ ] **Requirements** compliance
- [ ] **Documentation** updated

### PR Title Format

```
type(scope): description

Examples:
feat(rag): add support for DOCX file processing
fix(monitor): resolve file watching issue on macOS
docs(readme): update installation instructions
refactor(core): simplify file processor logic
test(integration): add comprehensive RAG workflow tests
```

### PR Description Template

```markdown
## 📋 Summary
Brief description of changes and motivation

## 🔄 Changes Made
- Change 1
- Change 2
- Change 3

## 🧪 Testing
- [ ] Unit tests added/updated
- [ ] Integration tests verified
- [ ] Manual testing completed

## 📊 Coverage
- File coverage: XX%
- Total coverage: XX%

## 🔒 Security
- [ ] No sensitive data exposed
- [ ] Input validation added where needed
- [ ] Security patterns followed
```

## 🔍 Code Standards

### Testing Requirements

**Coverage Standards:**
- **85% minimum per file** (strictly enforced)
- **90% total project coverage**
- **100% coverage** for critical paths (authentication, file processing)

**Test Types:**
```bash
# Unit tests
uv run pytest tests/test_*.py

# Integration tests  
uv run pytest tests/test_*_integration.py

# RAG system tests
uv run pytest tests/test_rag_integration_comprehensive/

# Performance tests
uv run pytest tests/test_performance_stress.py
```

### Code Quality

**Security Patterns:**
- Use environment variables for secrets (`OPENAI_API_KEY`, `GOOGLE_API_KEY`)
- Validate all input data
- Use parameterized queries for database operations
- Implement proper error handling
- Log security events appropriately

**Performance Patterns:**
- Avoid N+1 query problems
- Use async/await for I/O operations
- Implement proper caching strategies
- Monitor memory usage for large files
- Use generators for large datasets

**Maintainability:**
- Functions should be < 50 lines
- Maximum nesting depth of 4 levels
- Clear, descriptive variable names
- Comprehensive docstrings for public APIs
- Type hints for function parameters and returns

### Docker Development

**Local Development:**
```bash
# Build and run locally
./docker_deployment/deploy-local.sh [openai|google]

# Monitor logs
docker-compose logs -f

# Test different model vendors
./docker_deployment/deploy-local.sh google
```

## 🛠️ Development Environment

### Required System Dependencies

**Document Processing:**
```bash
# macOS
brew install tesseract libreoffice

# Ubuntu/Debian
sudo apt-get install tesseract-ocr libreoffice pandoc

# Windows
choco install tesseract libreoffice
```

### Environment Variables

Create `.env.local` file:
```env
# Required
SOURCE_FOLDER=./test_data/source
SAVED_FOLDER=./test_data/saved
ERROR_FOLDER=./test_data/error

# Optional - RAG functionality
ENABLE_DOCUMENT_PROCESSING=true
MODEL_VENDOR=openai
CHROMA_DB_PATH=./test_data/chroma_db
OPENAI_API_KEY=your_test_key_here
GOOGLE_API_KEY=your_test_key_here
```

### IDE Configuration

**VS Code Settings** (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "python.linting.enabled": true,
    "python.linting.banditEnabled": true
}
```

## 🚨 Troubleshooting

### Common Issues

**Test Failures:**
```bash
# Clear test cache
uv run pytest --cache-clear

# Run with maximum verbosity
uv run pytest -vvv --tb=long

# Run specific failing test
uv run pytest tests/test_file.py::TestClass::test_method -vvs
```

**Coverage Issues:**
```bash
# Generate detailed HTML coverage report
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html

# Check per-file coverage
uv run pytest --cov=src --cov-report=term-missing
```

**Docker Issues:**
```bash
# Rebuild containers
docker-compose down
docker-compose up --build

# Check container logs
docker-compose logs rag-file-processor

# Debug inside container
docker-compose exec rag-file-processor bash
```

### Getting Help

1. **Check existing issues** on GitHub
2. **Run the test suite** to ensure reproducibility
3. **Include error logs** and environment details
4. **Provide minimal reproduction** steps

## 📚 Additional Resources

- **Project Architecture**: See `CLAUDE.md` for detailed technical architecture
- **Docker Deployment**: See `docker_deployment/README.md` for deployment guide
- **API Documentation**: Generated automatically from docstrings
- **Test Coverage Reports**: Available in CI/CD artifacts

## 🤝 Community Guidelines

- **Be respectful** and inclusive
- **Ask questions** when unsure
- **Share knowledge** and help others
- **Focus on code quality** over speed
- **Embrace feedback** as learning opportunities

---

**Happy coding! 🎉**

*This project follows trunk-based development principles for fast, high-quality software delivery.*