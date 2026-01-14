# Versioning Strategy

Batchivo follows [Semantic Versioning 2.0.0](https://semver.org/).

## Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE]
```

Examples:
- `0.2.0` - Development release
- `1.0.0` - First stable release
- `1.2.3` - Patch release
- `2.0.0-alpha.1` - Pre-release

## Version Semantics

### Pre-1.0 (Current Phase)

During development (0.x.x):
- **MINOR** version bumps may include breaking changes
- **PATCH** version bumps are for bug fixes and non-breaking changes
- API stability is not guaranteed

### Post-1.0 (Future)

After reaching 1.0:
- **MAJOR** - Breaking changes to public API or data models
- **MINOR** - New features, backward-compatible
- **PATCH** - Bug fixes, backward-compatible

## Pre-release Labels

| Label | Meaning |
|-------|---------|
| `alpha` | Feature incomplete, unstable |
| `beta` | Feature complete, testing phase |
| `rc` | Release candidate, final testing |

Example progression:
```
0.2.0-alpha.1 → 0.2.0-alpha.2 → 0.2.0-beta.1 → 0.2.0-rc.1 → 0.2.0
```

## Component Versioning

Both backend and frontend share the same version number to simplify deployment and compatibility tracking.

| Component | Location |
|-----------|----------|
| Backend | `backend/pyproject.toml` |
| Frontend | `frontend/package.json` |

## Release Process

1. **Version Bump**
   - Update version in `backend/pyproject.toml`
   - Update version in `frontend/package.json`
   - Update `CHANGELOG.md`

2. **Tag Release**
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

3. **Create GitHub Release**
   - Generate release notes from CHANGELOG
   - Attach any relevant assets

## Current Version

- **Version**: 0.2.0-alpha
- **Status**: In Development
- **Phase**: 4 of 10 (Production Run System)

## Roadmap to 1.0

Prerequisites for 1.0 stable release:
- [ ] Complete Phase 4 (Production Runs)
- [ ] Complete Phase 5 (Pricing Engine)
- [ ] Complete Phase 6 (Sales & Orders)
- [ ] API stability guarantee
- [ ] Comprehensive documentation
- [ ] Security audit

---

*Last Updated: January 2026*
