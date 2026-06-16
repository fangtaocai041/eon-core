# Contributing

Thanks for your interest in improving eon-core!

## Development Setup

```bash
cd eon-core
pip install -e .
pip install pytest ruff
```

## Testing

```bash
# Run tests
python -m pytest tests/ -v

# Lint
ruff check src/
ruff format --check src/
```

## Pull Request Checklist

- [ ] Tests pass
- [ ] No ruff errors
- [ ] Runtime invariants (INV-001~008) verified
- [ ] New features have docstrings + type hints
- [ ] Changes to DAG topology update `config/taiji.yaml`

## License

MIT — by contributing, you agree to MIT licensing.
