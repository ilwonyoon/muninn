# Publishing to PyPI

## Prerequisites

1. PyPI account: https://pypi.org/account/register/
2. API token: https://pypi.org/manage/account/token/ (scope: entire account or project `muninn-mcp`)

## Setup Credentials

```bash
# Option 1: Environment variables
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR-TOKEN-HERE

# Option 2: ~/.pypirc file
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TESTPYPI-TOKEN-HERE
EOF
chmod 600 ~/.pypirc
```

## Build

```bash
cd /path/to/muninn
uv build
```

This creates:
- `dist/muninn_mcp-0.1.0.tar.gz` (source distribution)
- `dist/muninn_mcp-0.1.0-py3-none-any.whl` (wheel)

## Verify

```bash
uv run twine check dist/*
# Should show: PASSED for both files
```

## Publish to TestPyPI (Recommended First)

```bash
uv run twine upload --repository testpypi dist/*
```

Test installation:
```bash
pip install -i https://test.pypi.org/simple/ muninn-mcp
```

## Publish to PyPI

```bash
uv run twine upload dist/*
```

After publishing:
```bash
pip install muninn-mcp          # basic (stdio only)
pip install muninn-mcp[http]    # with HTTP transport
pip install muninn-mcp[all]     # everything
```

## Version Bump

1. Update version in `pyproject.toml` and `src/muninn/__init__.py`
2. Commit and tag: `git tag v0.1.1`
3. Rebuild and upload

## Current Version: 0.1.0
