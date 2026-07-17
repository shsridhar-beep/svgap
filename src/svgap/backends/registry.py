from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable

from svgap.backends.base import BackendUnavailable, CheckerBackend
from svgap.backends.reference_yosys import ReferenceYosysBackend


BackendFactory = Callable[[], CheckerBackend]


class BackendError(ValueError):
    pass


def _discover() -> tuple[dict[str, BackendFactory], dict[str, str], dict[str, str]]:
    factories: dict[str, BackendFactory] = {
        ReferenceYosysBackend.name: ReferenceYosysBackend,
    }
    errors: dict[str, str] = {}
    unavailable: dict[str, str] = {}
    for entry_point in entry_points(group="svgap.backends"):
        if entry_point.name in factories:
            continue
        try:
            factories[entry_point.name] = entry_point.load()
        except BackendUnavailable as exc:
            # An optional extra that is not installed: neither a working
            # factory nor a broken plugin. The message carries the install hint.
            unavailable[entry_point.name] = str(exc)
        except Exception as exc:  # plugin import failures must not disable built-ins
            errors[entry_point.name] = f"{type(exc).__name__}: {exc}"
    return factories, errors, unavailable


def discover_backends() -> tuple[dict[str, BackendFactory], dict[str, str]]:
    """Return built-in and installed checker backend factories.

    Third-party packages register factories in the ``svgap.backends`` entry
    point group. A plugin may not replace a built-in backend name. A backend
    whose optional dependencies are not installed appears in neither dict;
    see :func:`unavailable_backends`.
    """

    factories, errors, _unavailable = _discover()
    return factories, errors


def unavailable_backends() -> dict[str, str]:
    """Registered backends whose optional dependencies are not installed.

    Maps the backend name to an actionable install hint. These are not
    errors: the backend is one ``pip install`` away, and ``svgap doctor``
    reports them without failing.
    """

    return _discover()[2]


def available_backends() -> dict[str, BackendFactory]:
    return discover_backends()[0]


def load_backend(name: str) -> CheckerBackend:
    factories, errors, unavailable = _discover()
    if name in unavailable:
        raise BackendError(f"cannot load structural backend {name!r}: {unavailable[name]}")
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
