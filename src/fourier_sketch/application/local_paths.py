"""Lexical local-filesystem path policy for user-selected desktop operations."""

from pathlib import Path, PureWindowsPath

from fourier_sketch.domain import DomainValidationError

_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CONIN$",
        "CONOUT$",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)


class LocalPathError(DomainValidationError):
    """A path is not inside the accepted local filesystem namespace."""


def validate_local_path(path: Path, *, field_name: str) -> Path:
    """Reject UNC, device, ADS and ambiguous drive-relative Windows paths before I/O."""
    if not isinstance(path, Path):
        raise LocalPathError(f"{field_name} must be a pathlib.Path")
    if not isinstance(field_name, str) or not field_name:
        raise DomainValidationError("local path validation requires a field name")
    raw = str(path)
    if not raw:
        raise LocalPathError(f"{field_name} path must not be empty")

    windows_path = PureWindowsPath(raw)
    normalized = raw.replace("/", "\\")
    if normalized.startswith("\\\\") or windows_path.drive.startswith("\\\\"):
        raise LocalPathError(f"{field_name} path must not use a UNC or device namespace")
    if windows_path.drive and not windows_path.root:
        raise LocalPathError(f"{field_name} path must not be drive-relative")

    tail = raw[len(windows_path.drive) :]
    if ":" in tail:
        raise LocalPathError(f"{field_name} path must not use an alternate data stream")
    for component in windows_path.parts:
        if component in (windows_path.drive, windows_path.root, "\\", "/"):
            continue
        normalized_component = component.rstrip(" .").partition(".")[0].upper()
        if normalized_component in _WINDOWS_RESERVED_NAMES:
            raise LocalPathError(f"{field_name} path must not use a device name")
    return path
