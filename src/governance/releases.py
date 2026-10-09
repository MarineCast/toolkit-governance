"""Immutable local generations with a verified, atomically switched current pointer.

This is a toolkit-local publication envelope, not a change to manifest contract 0.1.
Readers resolve current once and retain that generation path for their whole operation.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .shared.artifacts import sha256_file


def _id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError("Release identity must be a safe single path component")
    return value


def _json(path: Path, value: dict) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _lock(root: Path):
    lock = root / '.publish.lock'
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, str(os.getpid()).encode())
        yield
    finally:
        os.close(descriptor)
        lock.unlink()


def verify_generation(path: str | Path) -> dict:
    """Verify every member, exact membership and containment before a reader uses it."""
    if Path(path).is_symlink():
        raise ValueError('Generation directory symlinks are forbidden')
    root = Path(path).resolve()
    manifest = json.loads((root / 'generation.json').read_text())
    if manifest.get('schema_version') != 1 or manifest.get('release_id') != root.name:
        raise ValueError('Invalid generation identity/schema')
    files = manifest.get('files', {})
    if not files:
        raise ValueError('Empty release')
    actual = set()
    for member in root.rglob('*'):
        if member.is_symlink():
            raise ValueError('Release symlinks are forbidden')
        if member.is_file() and member != root / 'generation.json':
            actual.add(member.relative_to(root).as_posix())
    if actual != set(files):
        raise ValueError('Generation membership mismatch')
    for name, record in files.items():
        member = root / name
        if member.resolve().parent != root and root not in member.resolve().parents:
            raise ValueError('Member escapes generation')
        if member.stat().st_size != record['bytes'] or sha256_file(member) != record['sha256']:
            raise ValueError(f'Generation checksum mismatch: {name}')
    return manifest


def _activate(root: Path, generation: Path) -> None:
    verify_generation(generation)
    if (generation / 'study-contract.json').exists():
        from .study import validate_study_release
        validate_study_release(generation)
    pointer = {'schema_version': 1, 'release_id': generation.name,
               'generation_sha256': sha256_file(generation / 'generation.json')}
    temporary = root / f'.current-{os.getpid()}.json'
    try:
        _json(temporary, pointer)
        os.replace(temporary, root / 'current.json')
        _sync_directory(root)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_current(root: str | Path) -> Path:
    root = Path(root).resolve()
    pointer = json.loads((root / 'current.json').read_text())
    generation = root / _id(pointer['release_id'])
    if sha256_file(generation / 'generation.json') != pointer['generation_sha256']:
        raise ValueError('Current generation manifest checksum mismatch')
    verify_generation(generation)
    return generation


def activate_generation(root: str | Path, release_id: str) -> Path:
    """Explicit rollback/activation, without modifying any immutable generation."""
    root = Path(root).resolve()
    with _lock(root):
        generation = root / _id(release_id)
        _activate(root, generation)
    return generation


def publish_generation(source: str | Path, root: str | Path, release_id: str, *,
                       scientific_method_version: str, software_revision: str,
                       activate: bool = True) -> Path:
    """Copy, hash, verify and atomically expose a prepared local release.

    A failed pointer switch can leave a verified unreferenced generation; the previous
    pointer stays intact. Never remove or overwrite existing generations automatically.
    Source files must be quiescent during publication. No remote upload occurs.
    """
    source, root = Path(source).resolve(), Path(root).resolve()
    _id(release_id)
    if not source.is_dir() or source == root or source in root.parents or root in source.parents:
        raise ValueError('Source and release root must be separate directories')
    if not scientific_method_version.strip() or not re.fullmatch(r'[0-9a-f]{40}', software_revision):
        raise ValueError('Explicit method version and full software Git SHA required')
    root.mkdir(parents=True, exist_ok=True)
    with _lock(root):
        destination = root / release_id
        if destination.exists():
            raise FileExistsError(destination)
        members = sorted(source.rglob('*'))
        if any(p.is_symlink() for p in members):
            raise ValueError('Source symlinks are forbidden')
        if any(p.name == 'generation.json' for p in members):
            raise ValueError('generation.json is reserved')
        temporary = Path(tempfile.mkdtemp(prefix='.staging-', dir=root))
        try:
            files = {}
            for path in members:
                if not path.is_file():
                    continue
                relative = path.relative_to(source)
                target = temporary / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                before = sha256_file(path)
                shutil.copyfile(path, target)
                if sha256_file(target) != before or sha256_file(path) != before:
                    raise ValueError(f'Source changed during publication: {relative}')
                with target.open('rb') as stream:
                    os.fsync(stream.fileno())
                files[relative.as_posix()] = {'sha256': before, 'bytes': target.stat().st_size}
            if not files:
                raise ValueError('Empty release')
            _json(temporary / 'generation.json', {
                'schema_version': 1, 'release_id': release_id,
                'scientific_method_version': scientific_method_version,
                'software_revision': software_revision,
                'created_at_utc': datetime.now(UTC).isoformat(), 'files': files,
            })
            for directory in sorted((p for p in temporary.rglob('*') if p.is_dir()), reverse=True):
                _sync_directory(directory)
            _sync_directory(temporary)
            os.rename(temporary, destination)
            _sync_directory(root)
            verify_generation(destination)
            if activate:
                _activate(root, destination)
            return destination
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
