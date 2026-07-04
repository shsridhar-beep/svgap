from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable

from svgap.backends.base import CheckerBackend
from svgap.backends.reference_yosys import ReferenceYosysBackend


BackendFactory = Callable[[], CheckerBackend]


class BackendError(ValueError):
    pass


def discover_backends() -> tuple[dict[str, BackendFactory], dict[str, str]]:
    """Return built-in and installed checker backend factories.

    Third-party packages register factories in the ``svgap.backends`` entry
    point group. A plugin may not replace a built-in backend name.
    """

    factories: dict[str, BackendFactory] = {
        ReferenceYosysBackend.name: ReferenceYosysBackend,
    }
    errors: dict[str, str] = {}
    for entry_point in entry_points(group="svgap.backends"):
        if entry_point.name in factories:
            continue
        try:
            factories[entry_point.name] = entry_point.load()
        except Exception as exc:  # plugin import failures must not disable built-ins
            errors[entry_point.name] = f"{type(exc).__name__}: {exc}"
    return factories, errors


def available_backends() -> dict[str, BackendFactory]:
    return discover_backends()[0]


def load_backend(name: str) -> CheckerBackend:
    factories, errors = discover_backends()
    if name in errors:
        raise BackendError(f"cannot load structural backend {name!r}: {errors[name]}")
    try:
        factory = factories[name]
    except KeyError as exc:
        choices = ", ".join(sorted(factories)) or "none"
        raise BackendError(f"unsupported structural backend {name!r}; available: {choices}") from exc
    backend = factory()
    if getattr(backend, "name", None) != name or not callable(
        getattr(backend, "check", None)
    ):
        raise BackendError(f"backend entry point {name!r} does not implement the SV-Gap contract")
    return backend
