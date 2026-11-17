# Contributing

The list is rebuilt every day by [`scripts/update.py`](scripts/update.py), so edits to `README.md` or `data/` are overwritten at the next run.

- **A role is wrong or closed:** open a [report](../../issues/new?template=closed-role.yml).
- **A role is missing:** [suggest it](../../issues/new?template=add-role.yml) with a link to the company's careers page.
- **Code:** changes to `scripts/`, `templates/` or `tests/` are welcome as pull requests. Run the tests first:

```sh
python3 -m unittest discover -s tests
python3 scripts/update.py
```

The scripts use the Python standard library only.
