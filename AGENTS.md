# Ollama Code Assistant (OCA) - Agent Configuration

## Project Overview
Ollama Code Assistant (OCA) is a free and open-source command-line interface tool for AI-assisted coding using Ollama's open-weight language models. It provides a safe, isolated environment for AI-driven code modifications with comprehensive Git integration and strict sandboxing.

## Key Components

### Core Modules
- **oca/cli.py**: Main CLI entry point with command definitions (init, explain, fix, refactor, test, commit, search)
- **oca/core/ollama.py**: Ollama API client wrapper for AI interactions
- **oca/core/session.py**: Session management and Git worktree handling
- **oca/utils/git.py**: Git operations wrapper
- **oca/utils/files.py**: File system operations

### Commands
- `oca init`: Initialize OCA in a project
- `oca explain`: Get code explanations
- `oca fix`: Fix bugs and issues
- `oca refactor`: Refactor code
- `oca test`: Generate tests
- `oca commit`: Create descriptive commits
- `oca search`: Search codebase

## Coding Conventions
- **Language**: Python 3.8+
- **Style**: PEP 8 with Black formatting
- **Imports**: Group external libs, then internal modules; use absolute paths
- **Types**: TypeScript-style type hints required for public APIs
- **Error Handling**: Try/catch for async operations, descriptive Error objects
- **Comments**: JSDoc for public APIs only, avoid inline comments
- **Naming**: camelCase for variables/functions, PascalCase for classes

## Development Workflow
- **Build**: `pip install -e .`
- **Lint**: `ruff check .`
- **Test**: `pytest` (100% coverage required)
- **Format**: `black .`
- **Type Check**: `mypy .`

## Architecture Principles
1. **Isolation First**: Every session in isolated Git worktree
2. **Immutable History**: All changes tracked via Git commits
3. **No Side Effects**: Cannot modify files outside CWD
4. **Transparent Operations**: Every action logged and committed
5. **Fail-Safe Design**: Errors never corrupt original codebase

## Security & Safety
- Directory restriction (no access outside CWD)
- No network access except local Ollama API
- No system commands except Git operations
- File type validation
- Path traversal prevention
- Size limits and input validation

## Dependencies
- click>=8.0.0: CLI framework
- requests>=2.28.0: HTTP client for Ollama API
- pyyaml>=6.0: Configuration file parsing
- Git 2.20+: Worktree support required

## Configuration
- Project config: `.oca/config.yaml`
- User config: `~/.config/oca/config.yaml`
- System config: `/etc/oca/config.yaml`

Default model: codellama, API URL: http://localhost:11434

## Testing Strategy
- Unit tests: All Ollama interactions mocked
- Integration tests: Git operations with temp repos
- End-to-end tests: Full workflow with mocked Ollama
- 100% test coverage required

## Git Workflow
- Always creates new worktree/branch per session
- Auto-commits each AI change
- Branch naming: oca/feature-timestamp
- User reviews before merging to original branch