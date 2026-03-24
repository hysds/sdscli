# HySDS SDSCli Packaging Migration Summary

## Migration Completed: March 24, 2026

This document summarizes the migration of the `sdscli` repository from legacy `setup.py` to modern `pyproject.toml` packaging.

---

## Changes Made

### ✅ Files Created

1. **`pyproject.toml`** - Modern packaging configuration
   - Package name: `hysds-sdscli` (PyPI) / `sdscli` (import)
   - Version: Dynamic from git tags via `hatch-vcs`
   - Dependencies: 14 third-party packages
   - Console script: `sds` command preserved

2. **`.github/workflows/publish.yml`** - PyPI publishing automation
   - Triggered on git tags (`v*`)
   - Uses PyPI Trusted Publishers (OIDC)

### ✅ Files Modified

1. **`sdscli/__init__.py`**
   - Changed from hardcoded version to `version("hysds-sdscli")`

2. **`setup.py`**
   - Replaced with minimal shim for backward compatibility
   - Delegates all configuration to `pyproject.toml`
   - Will be removed in v7.1.0+

---

## Key Dependency Changes

### Fixed Issues

| Issue | Before | After |
|-------|--------|-------|
| prompt-toolkit outdated | `>=1.0,<2.0` | `>=3.0,<4.0` |

### Dependencies Preserved Exactly

All 14 core dependencies maintained with exact pins from original `setup.py`:
- `PyYAML>=5.1`
- `Pygments>=2.4.0`
- `tqdm>=4.32.1`
- `backoff>=1.8.0`
- `requests>=2.22.0`
- `kombu>=4.5.0`
- `redis>=3.2.1`
- `elasticsearch>=7.0.0,<7.14.0`
- `elasticsearch-dsl>=7.0.0,<=7.4.0`
- `awscli>=1.17.1`
- `boto3>=1.11.1`
- `fab-classic>=1.19.2`
- `Jinja2>=3.0.0,<4.0.0`

---

## Build Verification

```bash
$ python -m build
Successfully built hysds_sdscli-2.1.0.post1.dev0+g65c5cb1f9.d20260324.tar.gz
Successfully built hysds_sdscli-2.1.0.post1.dev0+g65c5cb1f9.d20260324-py3-none-any.whl
```

---

## Next Steps

### Before Publishing to PyPI

1. **Tag version 7.0.0**
   ```bash
   git tag -a v7.0.0 -m "Release 7.0.0 - Modern packaging migration"
   git push origin v7.0.0
   ```

2. **Configure PyPI Trusted Publisher**
   - Go to https://pypi.org/manage/account/publishing/
   - Add GitHub Actions publisher for `hysds/sdscli` repo
   - Workflow: `publish.yml`
   - Environment: `pypi`

### Installation Methods

#### Development (Local)
```bash
pip install -e .
```

#### Development (From Git Branch)
```bash
pip install "git+https://github.com/hysds/sdscli.git@feature-branch"
```

#### Production (After PyPI Publishing)
```bash
pip install hysds-sdscli

# Console script still works
sds --help
```

---

## Backward Compatibility

### Import Names (Unchanged)
```python
# All existing imports continue to work
import sdscli
from sdscli.command_line import main
```

### Console Script (Unchanged)
```bash
sds --help  # Still works
```

### Package Name Change
- **PyPI package**: `sdscli` → `hysds-sdscli`
- **Import name**: `sdscli` (unchanged)

---

## Migration Checklist

- [x] Create `pyproject.toml` with all dependencies
- [x] Upgrade prompt-toolkit to 3.x
- [x] Preserve all other dependency pins exactly
- [x] Update `sdscli/__init__.py` for dynamic versioning
- [x] Add GitHub Actions workflow for PyPI publishing
- [x] Preserve console script entry point
- [x] Keep minimal `setup.py` shim for backward compatibility
- [x] Verify `python -m build` succeeds
- [ ] Tag v7.0.0 release
- [ ] Configure PyPI Trusted Publisher
- [ ] Publish to PyPI

---

## Contact

For questions about this migration, contact the HySDS team at hysds-help@jpl.nasa.gov
