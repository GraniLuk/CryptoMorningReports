# Package-Specific Upgrade Notes

This file contains version-specific guidance for commonly upgraded packages in this project.

## Table of Contents
- [azure-functions](#azure-functions)
- [google-generativeai](#google-generativeai)
- [pandas](#pandas)
- [pytest](#pytest)
- [requests](#requests)
- [Adding new package notes](#adding-new-package-notes)

## azure-functions

### Common breaking changes
- v1.x → v2.x: WSGI replaced with ASGI
- Authentication model changes between major versions
- Binding syntax updates

### Key considerations
- Test with local Functions runtime before deploying
- Check host.json compatibility
- Verify trigger binding formats

## google-generativeai

### Common breaking changes
- Model naming conventions change between versions
- Authentication flow modifications
- Response format changes (especially for streaming)

### Key considerations
- Always test with actual API calls (quota permitting)
- Check temperature/parameter names
- Verify safety settings format
- Review token counting changes

## pandas

### Common breaking changes
- Deprecation of append() → use concat()
- Changes in NA/NaN handling
- DataFrame.applymap() → DataFrame.map()
- Integer NA behavior changes

### Key considerations
- Test data serialization/deserialization
- Check for deprecation warnings in tests
- Verify datetime handling
- Review inplace parameter usage

## pytest

### Common breaking changes
- Fixture scope behavior changes
- Assertion rewriting updates
- Plugin API modifications

### Key considerations
- Run full test suite after upgrade
- Check custom fixtures
- Verify pytest.ini configuration
- Test async test support

## requests

### Common breaking changes
- SSL/TLS default behavior
- Timeout parameter handling
- Session management changes

### Key considerations
- Test all API integrations
- Verify certificate validation
- Check timeout configurations
- Review retry logic

---

## Adding new package notes

When upgrading a package for the first time, add notes here:

```markdown
## package-name

### Common breaking changes
- [Document observed breaking changes]

### Key considerations
- [Document testing considerations]
- [Document configuration changes]
- [Document gotchas for this project]

### Last upgraded
- Date: YYYY-MM-DD
- From version: vX.Y.Z
- To version: vX.Y.Z
- Issues encountered: [Brief description]
```
