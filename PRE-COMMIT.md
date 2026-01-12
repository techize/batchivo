# Pre-Commit Setup for Batchivo

This project uses pre-commit hooks to ensure code quality before commits.

## Installation

1. **Install pre-commit**:
   ```bash
   pip install pre-commit
   ```

2. **Install the git hooks**:
   ```bash
   pre-commit install
   ```

3. **Install frontend dependencies** (if not already done):
   ```bash
   cd frontend && npm install
   ```

## Usage

### Automatic (on git commit)
Pre-commit hooks will run automatically when you commit:
```bash
git add .
git commit -m "your message"
# Hooks run automatically
```

### Manual execution
Run hooks on all files:
```bash
pre-commit run --all-files
```

Run hooks on staged files only:
```bash
pre-commit run
```

Run a specific hook:
```bash
pre-commit run ruff --all-files
pre-commit run frontend-eslint --all-files
```

## Hooks Configured

### Backend (Python)
- **ruff**: Linting with auto-fix
- **ruff-format**: Code formatting

### Frontend (TypeScript/React)
- **frontend-eslint**: ESLint linting
- **frontend-typecheck**: TypeScript type checking

### General
- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with newline
- **check-yaml**: Validate YAML files
- **check-added-large-files**: Prevent large files (>1MB)
- **check-merge-conflict**: Detect merge conflict markers
- **detect-private-key**: Prevent committing private keys

## Skipping Hooks (Emergency Only)

If absolutely necessary, skip hooks with:
```bash
git commit --no-verify -m "message"
```

**Warning**: Only use this for emergencies. Skipping hooks defeats their purpose.

## Troubleshooting

### "Hook failed" errors
1. Fix the issues reported by the hook
2. Stage the fixes: `git add .`
3. Try committing again

### Frontend hooks fail
Ensure you're in the project root and frontend dependencies are installed:
```bash
cd frontend && npm install && cd ..
```

### Update hooks
Update to latest hook versions:
```bash
pre-commit autoupdate
```
