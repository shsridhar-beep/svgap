# Linux install and doctor checks

SV-Gap's built-in backend needs Python, Yosys, and Icarus Verilog on `PATH`.
On Ubuntu or Debian, install the open tools before installing SV-Gap:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip yosys iverilog
python3 -m venv .venv
. .venv/bin/activate
python -m pip install svgap==0.3.0a2
svgap doctor
```

For a GitHub Actions Ubuntu runner, use the maintained runner Python plus the
same open RTL packages:

```yaml
- uses: actions/setup-python@v6
  with:
    python-version: "3.12"
- run: sudo apt-get update && sudo apt-get install -y iverilog yosys
- run: python -m pip install svgap==0.3.0a2
- run: svgap doctor
```

## Understanding `svgap doctor`

`svgap doctor` checks whether `yosys`, `iverilog`, and `vvp` are discoverable on
`PATH`. It exits with status 1 when any required tool is missing.

- `yosys MISSING`: install the `yosys` package and verify it with
  `command -v yosys`.
- `iverilog MISSING`: install the `iverilog` package and verify it with
  `command -v iverilog`.
- `vvp MISSING`: install the `iverilog` package; the simulator runtime is
  packaged with Icarus Verilog on Ubuntu and Debian. Verify it with
  `command -v vvp`.

To inspect the exact paths that will be used:

```bash
command -v svgap
command -v yosys
command -v iverilog
command -v vvp
printf '%s\n' "$PATH" | tr ':' '\n'
```

If SV-Gap was installed in a virtual environment, activate it first or call the
script directly:

```bash
. .venv/bin/activate
svgap doctor

# or
.venv/bin/svgap doctor
```

When all required tools are present, `doctor` also prints the configured
`reference-yosys` backend with the detected Yosys version.

## Container fallback

If the host is not Ubuntu/Debian, the system package names differ, or the local
EDA packages are too old for a reproducible run, use the open-tool container:

```bash
docker run --rm ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.2 doctor
```

The container bundles SV-Gap with the pinned open-source toolchain used by the
project image.
