# Package Upgrade Skill

This skill helps AI agents safely upgrade Python packages in the CryptoMorningReports project.

## Purpose

When Dependabot or security advisories suggest package updates, this skill guides the AI agent to:
1. Analyze breaking changes
2. Identify required code modifications
3. Suggest beneficial new features
4. Create a comprehensive upgrade plan
5. Apply changes safely

## Usage

### With Claude Desktop or API

1. Load this skill
2. Provide the package name and version information from Dependabot
3. Optionally attach release notes or changelog
4. The agent will analyze and create an upgrade plan

Example prompt:
```
Dependabot suggests upgrading pandas from 1.5.3 to 2.1.0.
Please analyze the upgrade and create a plan.
```

### With release notes

If you have release notes, attach them:
```
I need to upgrade google-generativeai from 0.3.0 to 0.4.0.
[Attach release notes]
Please analyze what changes we need in our codebase.
```

### Without release notes

The agent will fetch documentation automatically:
```
Need to upgrade pytest from 7.4.0 to 8.0.0.
Please fetch the migration guide and analyze our code.
```

## Files

- **SKILL.md**: Main skill instructions with step-by-step workflow
- **PACKAGE_NOTES.md**: Historical notes on package-specific issues
- **README.md**: This file

## Workflow

The agent follows this 7-step process:

1. **Analyze current usage** - Find how the package is used in the codebase
2. **Review release notes** - Read provided notes or fetch from Context7 MCP
3. **Identify adjustments** - Map breaking changes to code that needs updates
4. **Check new features** - Find improvements that could benefit the application
5. **Create upgrade plan** - Synthesize findings into actionable steps
6. **Apply changes** - Update requirements.txt and modify code
7. **Verify functionality** - Run tests and validate the upgrade

## Integration with tools

This skill uses:
- **Context7 MCP server** (mcp_io_github_ups_*) - Fetches up-to-date documentation
- **grep_search** - Finds package usage in codebase
- **read_file** - Examines specific files
- **multi_replace_string_in_file** - Applies multiple code changes efficiently
- **run_in_terminal** - Installs packages and runs tests

## Best practices

✓ Upgrade one package at a time
✓ Always run tests after upgrading
✓ Check transitive dependencies
✓ Document changes in commit messages
✓ Review security advisories

✗ Don't skip the analysis phase
✗ Don't upgrade multiple packages together
✗ Don't ignore deprecation warnings

## Maintenance

After each upgrade, consider updating PACKAGE_NOTES.md with lessons learned.
