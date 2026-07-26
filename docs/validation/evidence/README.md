# Validation evidence

This directory stores non-text evidence referenced by durable validation reports.
Files remain descriptive artifacts; their presence does not authorize implementation
or establish a product gate beyond the report that cites them.

## Studio 009 addendum reproducer

`docs/validation/reproducers/verify_studio009_addendum.py` is portable, but its
three frozen inputs are not committed because they include a Studio fixture from a
separate repository and gitignored league-runtime artifacts. Supply exact copies
with `--studio-board`, `--matrix`, and `--snapshot`. The script refuses missing or
hash-mismatched inputs.

- Studio `board-data.js`: `ce81294d0795676b846caeae57ec7584327135a4032d2217a110111199a36392`
- `team_value_matrix.json`: `76e79f875848c223b103cba4990bc1637f603b9670ce10b7e35225bd77bd5986`
- `snapshot.json`: `41dc8d50d2539ebd342605739ba7aebc9eb8d11961b8f820c08fc45edac7119b`
