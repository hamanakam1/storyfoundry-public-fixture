# StoryFoundry public-safe fixture

This is a fictional, offline service company dataset for CRM workflow testing and
training. Mosaic Service Studio is an invented company. Its people, customers,
transactions, conversations, outcomes and projections are synthetic; none are
evidence of a real business or permission to contact, charge or import records.

The role and capability templates in `inputs/profile-shapes.json` were authored
for this edition. They were not derived from a private organization roster.
This repository has independent Git history and contains no private source
snapshot, transformation receipts or raw model run.

## Use

Python 3.10+ and the standard library are sufficient:

```bash
python3 -m unittest -v
python3 validate.py --data data --receipt /tmp/storyfoundry-validation.json
python3 generate.py --output /tmp/storyfoundry-replay
python3 import_preview.py --data data --output /tmp/storyfoundry-preview
```

`data/json/*.jsonl` is canonical; CSV mirrors it for inspection. The import
preview is a dry run with no target client. The generated data is deterministic
for the committed configuration and profile templates. All contact addresses
use `.example.invalid`, and phone values use the fictional 202-555-01xx range.

The synthetic scenario includes lost leads, repeat projects, credits, failed
payment attempts, support cases and future meetings. Its accounting identity is
issued invoices minus credits equals posted payments plus outstanding balances.
The numbers are training data, not revenue claims, accounting advice or a
forecast for any future venture.

## License

The code, authored inputs, documentation and generated synthetic fixture in
this repository are available under the [MIT License](LICENSE). The fictional
company name is a sample label, not a representation of a real business.
