# Contributing to Verto AI

Thank you for your interest in contributing! Here's how to get started.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/verto-ai.git`
3. **Set up** your environment:
   ```bash
   cp .env.example .env
   # Fill in your API keys in .env
   pip install -r requirements.txt
   ```

## Development Workflow

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Make your changes
3. Test locally (see README Testing Checklist)
4. Commit with a clear message:
   ```bash
   git commit -m "feat: add support for audio messages"
   ```
5. Push and open a Pull Request

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use For |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code restructuring |
| `test:` | Adding/updating tests |
| `chore:` | Maintenance tasks |

## Code Style

- Python: Follow [PEP 8](https://pep8.org/)
- Use descriptive variable names
- Add docstrings to new functions
- Keep functions focused and small

## Reporting Bugs

Open a [GitHub Issue](https://github.com/Aaditya-jn/verto-ai/issues) with:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS)

## Feature Requests

Open a GitHub Issue with the `enhancement` label and describe:
- The problem you're solving
- Your proposed solution
- Any alternatives considered

## Security Issues

**Do not** open a public issue for security vulnerabilities.
Instead, contact the maintainer directly.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.
