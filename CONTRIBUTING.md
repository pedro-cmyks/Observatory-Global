# Contributing to Atlas

Thanks for your interest. Here's how to get started.

## Running locally

See the [README](README.md#running-locally) for setup instructions.

## Code style

**Backend (Python)**
- Python 3.11+, async patterns with FastAPI
- Format with `black` (line length 100), lint with `ruff`
- Type hints encouraged but not enforced everywhere

**Frontend (TypeScript)**
- React 19 + Vite, strict TypeScript
- Functional components with hooks
- MapLibre GL + Deck.gl for map layers

## Making changes

1. Fork the repo and create a branch from `v3-intel-layer`
2. Make your changes — keep diffs small and focused
3. Test locally (backend: `pytest`, frontend: `npm run build`)
4. Open a PR with a clear description of what and why

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add country detail sidebar
fix: resolve sentiment color scale
docs: update setup instructions
```

## Questions?

Open an issue. We're happy to help.
