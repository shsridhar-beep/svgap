# Troubleshooting `svgap doctor`

`svgap doctor` is the first thing to run when a checked-out environment
does not behave as expected. It prints the resolved path for each required
tool, the discovered backends, and — when something is missing — the exact
remediation for the detected platform. This page walks through the failures
it reports and the fix for each one.

```bash
svgap doctor
```

## `yosys MISSING`

The `reference-yosys` structural backend shells out to `yosys` on `PATH`.
Without it, `doctor` prints `yosys MISSING` and exits with status 1.

- **macOS**: `brew install yosys`
- **Ubuntu/Debian**: `sudo apt-get update && sudo apt-get install -y yosys`
- **Fedora**: `sudo dnf install -y yosys`
- **Arch**: `sudo pacman -S yosys`

Verify with `command -v yosys`, then re-run `svgap doctor`.

## `iverilog MISSING`

Icarus Verilog provides both the `iverilog` compiler and the `vvp` runtime
used for the functional checker.

- **macOS**: `brew install icarus-verilog`
- **Ubuntu/Debian**: `sudo apt-get update && sudo apt-get install -y iverilog`
- **Fedora**: `sudo dnf install -y iverilog`
- **Arch**: `sudo pacman -S iverilog`

Verify with `command -v iverilog`.

## `vvp MISSING`

`vvp` ships inside the Icarus Verilog package, so this almost always means
the `iverilog` install above did not complete, or a partial install left
`iverilog` on `PATH` without its runtime. Reinstall the `iverilog` package
for your platform (see above) and verify with `command -v vvp`.

## Old or unsupported tool versions

`doctor` only checks whether a tool resolves on `PATH`, not whether its
version is recent enough. An old `yosys` or `iverilog` build can pass
`doctor` and still fail during `svgap check` with a synthesis error, a
missing command, or a finding count that does not match a fresh checkout.

The reference container and CI action pin the
[OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) release
documented in [CI and container integration](ci-and-container.md), which is
the version combination this project actually tests against. If a native
install behaves differently:

1. Check the resolved version: `yosys -V` and `iverilog -V`.
2. Upgrade through your package manager (Homebrew formulae and most Linux
   package repositories track upstream releases within a few months) or
   install from [YosysHQ's releases](https://github.com/YosysHQ/yosys) directly.
3. If upgrading the host tool is not an option, use the pinned container
   instead of a native install:

   ```bash
   docker run --rm ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.9 doctor
   ```

## Still stuck?

Confirm the exact binaries `svgap` will actually invoke — a second Python
environment or an unactivated virtualenv is a common cause of "it works in
one shell but not another":

```bash
command -v svgap
command -v yosys
command -v iverilog
command -v vvp
```

If SV-Gap is installed inside a virtual environment, either activate it
first or call it by its full path (`.venv/bin/svgap doctor`). See
[Linux install and doctor checks](linux-install-and-doctor.md) for the full
installation walkthrough, including CI and the container fallback.
