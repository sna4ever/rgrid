# Git Hooks

This directory contains sample Git hooks for the RGrid project.

## Pre-Commit Hook

The pre-commit hook automatically runs the test suite before allowing a commit. This ensures that:
- All tests pass before code is committed
- No broken code is added to the repository
- Test coverage is maintained

### Installation

```bash
# Copy the sample to .git/hooks/
cp hooks/pre-commit.sample .git/hooks/pre-commit

# Make it executable (should already be executable)
chmod +x .git/hooks/pre-commit
```

### Usage

Once installed, the hook runs automatically before every commit:

```bash
$ git commit -m "Add new feature"
🧪 Running test suite before commit...

✅ All tests passing - commit allowed
[main abc1234] Add new feature
```

### Bypassing the Hook

In rare cases where you need to commit without running tests (NOT recommended):

```bash
git commit --no-verify -m "Emergency fix"
```

**Warning**: Only use `--no-verify` in emergencies. Committing code without tests defeats the purpose of TDD and can introduce bugs.

### Hook Behavior

- Runs all tests in `tests/` directory
- Blocks commit if any test fails
- Shows minimal output for quick feedback
- Provides clear error messages on failure

### Troubleshooting

**Hook not running?**
- Check if `.git/hooks/pre-commit` exists and is executable
- Run `chmod +x .git/hooks/pre-commit`

**Tests failing incorrectly?**
- Run `venv/bin/pytest tests/ -v` manually to see detailed errors
- Fix the failing tests before committing

**Virtual environment not found?**
- Run `make setup` to create the virtual environment
- Ensure you're in the project root directory

## Future Hooks

Additional hooks that could be added:
- **pre-push**: Run full test suite + linting before pushing
- **commit-msg**: Enforce commit message format
- **post-commit**: Automatically run code formatting

## Notes

- Hooks in `.git/hooks/` are not tracked by Git (intentional design)
- This `hooks/` directory provides templates that can be copied
- All developers should install these hooks locally
- Consider adding hook installation to `make setup` target
