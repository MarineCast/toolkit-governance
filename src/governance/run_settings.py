"""Read-only path settings shared by CLI and flat-product Python APIs."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shlex

from ._config.paths import project_root
from .shared.config import DEFAULT_CONFIG_PATH

KEYS = {'GOVERNANCE_CONFIG', 'GOVERNANCE_OUTPUT_DIRECTORY',
        'GOVERNANCE_GRIDS', 'GOVERNANCE_ORIGINAL_DATA'}


@dataclass(frozen=True)
class RunSettings:
    workspace: Path
    config_path: Path
    output_directory: Path | None
    grid_paths: tuple[Path, ...]
    original_data: Path | None


def resolve_settings(*, workspace=None, env_file=None, config_path=None,
                     output_directory=None, grid_paths=None, original_data=None,
                     require_output=False, require_grids=False):
    """Resolve explicit arguments > environment > workspace .env > defaults.

    Workspace selection remains explicit > GOVERNANCE_WORKSPACE > cwd. It is
    never read from .env. File-relative settings resolve beside the selected file;
    explicit/environment paths resolve from cwd, except config uses workspace.
    Only known path keys are parsed. No interpolation, environment mutation,
    directories, acquisition, or implicit destructive flags are supported.
    """
    root = Path(workspace).expanduser().resolve() if workspace is not None else project_root()
    path = (root / Path(env_file).expanduser()).resolve() if env_file is not None else root / '.env'
    values, origins, errors = {}, {}, []
    try:
        if path.exists():
            if not path.is_file():
                raise ValueError('env_file must be a regular file.')
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                line = line.strip()
                if line.startswith('export '):
                    line = line[7:].lstrip()
                key, separator, raw = line.partition('=')
                key = key.strip()
                if key not in KEYS:
                    continue
                if key in values:
                    errors.append(f'{key} repeated on .env line {number}.')
                try:
                    tokens = shlex.split(raw, comments=True)
                    if not separator or len(tokens) != 1:
                        raise ValueError
                    values[key] = tokens[0]
                    origins[key] = path.parent
                except ValueError:
                    errors.append(f'{key} invalid syntax on .env line {number}.')
        elif env_file is not None:
            errors.append('Explicit env_file does not exist.')
    except (OSError, UnicodeError):
        errors.append('env_file cannot be read as UTF-8.')
    for key in KEYS:
        if key in os.environ:
            values[key], origins[key] = os.environ[key], root if key == 'GOVERNANCE_CONFIG' else Path.cwd()
    for key, value in [('GOVERNANCE_CONFIG', config_path), ('GOVERNANCE_OUTPUT_DIRECTORY', output_directory),
                       ('GOVERNANCE_GRIDS', grid_paths), ('GOVERNANCE_ORIGINAL_DATA', original_data)]:
        if value is not None:
            values[key], origins[key] = value, root if key == 'GOVERNANCE_CONFIG' else Path.cwd()
    values.setdefault('GOVERNANCE_CONFIG', DEFAULT_CONFIG_PATH)
    origins.setdefault('GOVERNANCE_CONFIG', root)

    def resolved(key, value):
        try:
            raw = os.fspath(value)
            if not isinstance(raw, str) or not raw.strip() or '\x00' in raw or '$' in raw:
                raise ValueError
            candidate = Path(raw).expanduser()
            return (origins[key] / candidate).resolve()
        except (TypeError, ValueError, OSError, RuntimeError):
            errors.append(f'{key} must be a nonempty path without variable interpolation.')
            return None

    config = resolved('GOVERNANCE_CONFIG', values['GOVERNANCE_CONFIG'])
    output = resolved('GOVERNANCE_OUTPUT_DIRECTORY', values['GOVERNANCE_OUTPUT_DIRECTORY']) if 'GOVERNANCE_OUTPUT_DIRECTORY' in values else None
    original = resolved('GOVERNANCE_ORIGINAL_DATA', values['GOVERNANCE_ORIGINAL_DATA']) if 'GOVERNANCE_ORIGINAL_DATA' in values else None
    grids = values.get('GOVERNANCE_GRIDS', [])
    if isinstance(grids, str):
        try:
            grids = json.loads(grids)
        except ValueError:
            grids = None
    if not isinstance(grids, (list, tuple)):
        errors.append('GOVERNANCE_GRIDS must be a JSON array of paths (or a Python sequence).')
        grids = []
    grids = tuple(resolved('GOVERNANCE_GRIDS', value) for value in grids)
    if require_output and output is None:
        errors.append('GOVERNANCE_OUTPUT_DIRECTORY or output_directory is required.')
    if require_grids and not grids:
        errors.append('GOVERNANCE_GRIDS or grid_paths must contain at least one path.')
    if errors:
        raise ValueError('Governance settings failed:\n- ' + '\n- '.join(errors))
    return RunSettings(root, config, output, grids, original)
