---
name: upgrading-python-packages
description: Safely upgrade Python packages one at a time by analyzing breaking changes, new features, and required code adjustments. Use when Dependabot suggests package updates or when the user asks to upgrade a specific package.
---

# Python Package Upgrade Assistant

## Overview

This skill helps safely upgrade Python packages by analyzing:
- Breaking changes requiring code modifications
- New features that could improve the application
- Compatibility issues with existing code
- Required configuration changes

**ALWAYS upgrade ONE package at a time** to isolate issues.

## Upgrade workflow

Copy this checklist and track progress:

```
Upgrade Progress:
- [ ] Step 1: Analyze current usage in codebase
- [ ] Step 2: Review release notes and breaking changes
- [ ] Step 3: Identify code adjustments needed
- [ ] Step 4: Check for beneficial new features
- [ ] Step 5: Create upgrade plan
- [ ] Step 6: Apply changes
- [ ] Step 7: Verify functionality
```

### Step 1: Analyze current usage

Search the codebase to understand how the package is currently used:

```bash
# Find all imports and usage
grep -r "import <package_name>" --include="*.py"
grep -r "from <package_name>" --include="*.py"
```

Document:
- Which files use this package
- What features/functions are imported
- How critical the package is to core functionality

### Step 2: Review release notes

**If user provides release notes**: Use them as primary source

**If release notes missing or incomplete**: Fetch documentation using Context7 MCP server:

1. Resolve the library ID:
   ```
   Use mcp_io_github_ups_resolve-library-id with libraryName="<package_name>"
   ```

2. Get relevant documentation:
   ```
   Use mcp_io_github_ups_get-library-docs with:
   - context7CompatibleLibraryID from step 1
   - topic="breaking changes migration guide"
   - mode="info" (for migration guides)
   ```

3. If needed, get API changes:
   ```
   Use mcp_io_github_ups_get-library-docs with:
   - Same library ID
   - topic="api changes new features"
   - mode="code" (for code examples)
   ```

Focus on:
- Breaking changes between current and target version
- Deprecated features in use
- Migration guides
- New recommended patterns

### Step 3: Identify required code adjustments

Cross-reference Step 1 usage with Step 2 breaking changes:

For each breaking change:
1. Check if it affects code found in Step 1
2. Identify specific files and line numbers needing updates
3. Determine the required modification

Create a structured list:
```
File: path/to/file.py
Line: 45
Current: old_function(param)
Required: new_function(param, new_required_arg)
Reason: Function signature changed in v2.0
```

### Step 4: Check for beneficial new features

Review new features from release notes and identify improvements:

**Consider new features that**:
- Improve performance for existing functionality
- Simplify current implementation patterns
- Add error handling or logging capabilities
- Provide better type hints or async support

**Context for this application**:
- **Database operations**: SQLite interactions (database/init_sqlite.py)
- **API integrations**: External crypto/financial APIs
- **Azure Functions**: Serverless deployment environment
- **Telegram bot**: Real-time notifications
- **AI/ML**: Gemini API for content generation
- **Data processing**: ETF data, news articles, technical analysis

Example analysis format:
```
New Feature: async/await support added in v3.0
Benefit: Could improve Azure Function cold start times
Location: shared_code/api_client.py (currently uses sync requests)
Effort: Medium - requires refactoring 3 functions
Priority: High - performance critical for serverless
```

### Step 5: Create upgrade plan

Synthesize findings into actionable plan:

```markdown
## Upgrade Plan: <package_name> from v<current> to v<target>

### Critical Changes (MUST DO)
1. [File path] - [Specific change needed]
2. [File path] - [Specific change needed]

### Configuration Updates
- Update requirements.txt: <package_name>==<new_version>
- [Any other config changes]

### Recommended Improvements (OPTIONAL)
1. [New feature] - [Where to apply] - [Expected benefit]

### Testing Strategy
- [ ] Run existing tests: pytest
- [ ] Test specific functionality: [describe what to test]
- [ ] Verify Azure Function deployment
- [ ] Check Telegram notifications work

### Rollback Plan
If issues occur:
1. Revert requirements.txt to <package_name>==<old_version>
2. Run: pip install -r requirements.txt
3. Revert code changes from this upgrade
```

### Step 6: Apply changes

Implement changes in this order:

1. **Update requirements.txt** with new version
2. **Install the package**: `pip install -r requirements.txt`
3. **Apply required code changes** from Step 3
4. **Optionally implement new features** from Step 4

Use multi_replace_string_in_file for multiple changes across files.

### Step 7: Verify functionality

Run comprehensive verification:

```bash
# Run tests
pytest

# Check for import errors
python -m py_compile <affected_files>

# Run specific functionality tests
python <test_script>
```

**IMPORTANT**: If verification fails:
1. Review error messages carefully
2. Check if additional breaking changes were missed
3. Consult Context7 MCP server for additional documentation
4. Consider rolling back if issues cannot be resolved quickly

## Common package categories

### Azure SDK packages (azure-*)
- Check Azure Function runtime compatibility
- Verify authentication method changes
- Test connection strings and credentials
- Review async/await patterns

### API client libraries (requests, httpx, aiohttp)
- Check timeout and retry logic changes
- Verify SSL/TLS certificate handling
- Test error handling patterns
- Review connection pooling settings

### Data processing (pandas, numpy)
- Check for deprecated numpy types
- Verify dataframe operation changes
- Test serialization/deserialization
- Review memory usage patterns

### Database libraries (sqlite3, sqlalchemy)
- Check connection string format
- Verify transaction handling
- Test query syntax changes
- Review connection pooling

### Testing frameworks (pytest, unittest)
- Check fixture syntax changes
- Verify assertion methods
- Test async test support
- Review plugin compatibility

## Project-specific considerations

This application has these key characteristics:

**Deployment**: Azure Functions (Python 3.9+)
- Cold start performance matters
- Memory limits apply (1.5GB default)
- Execution timeout is 5 minutes for consumption plan

**Critical paths**:
1. News article processing (news/article_processor.py)
2. ETF data fetching (etf/etf_fetcher.py)
3. Telegram notifications (infra/telegram_logging_handler.py)
4. AI content generation (AI/current_situation_analysis.py)

**External dependencies**:
- Gemini AI API (must remain functional)
- Telegram Bot API (must remain functional)
- Various crypto APIs (binance, coingecko, etc.)

When upgrading packages used in these areas, prioritize stability over new features.

## Package-specific guidance

See [PACKAGE_NOTES.md](PACKAGE_NOTES.md) for version-specific upgrade notes.

## Troubleshooting

### Error: Import fails after upgrade
1. Check if package structure changed
2. Verify submodule imports
3. Check for renamed modules
4. Review deprecation warnings

### Error: Function signature mismatch
1. Compare old vs new API documentation
2. Check for new required parameters
3. Verify parameter name changes
4. Look for deprecated parameter removal

### Error: Tests fail after upgrade
1. Check if test framework API changed
2. Verify mock/patch patterns still work
3. Review fixture changes
4. Check assertion method changes

## Best practices

✓ **Always read the full changelog** between versions, not just latest
✓ **Test in local environment** before committing changes
✓ **Update one package at a time** to isolate issues
✓ **Check transitive dependencies** that might also upgrade
✓ **Review security advisories** for the package
✓ **Document why upgrade is needed** in commit message

✗ **Don't skip testing** even for "minor" version bumps
✗ **Don't upgrade multiple packages simultaneously**
✗ **Don't ignore deprecation warnings**
✗ **Don't assume semantic versioning** is strictly followed

## Output format

After completing the upgrade analysis, provide:

```markdown
# Package Upgrade Summary: <package_name>

## Current Status
- Current version: v<current>
- Target version: v<target>
- Risk level: [Low/Medium/High]

## Required Changes
[List all required code changes with file paths and line numbers]

## Optional Improvements
[List beneficial new features to consider]

## Files Affected
- path/to/file1.py (3 changes)
- path/to/file2.py (1 change)

## Next Steps
1. [Specific action]
2. [Specific action]

## Estimated Time
- Required changes: [X] minutes
- Optional improvements: [Y] minutes
- Testing: [Z] minutes
```
