# Harbor adapter maintainer guide

The public Harbor page is written for researchers who may be new to hardware
evaluation. This guide keeps rebuild and publication operations in the source
repository.

## Rebuild the adapters

The adapters are generated from the frozen taskpack:

```bash
python3 integrations/harbor/build_reset_release.py
harbor sync integrations/harbor/svgap-reset-release
```

Review generated changes before publishing. A documentation-only Hub revision
must not alter task digests.

## Validate witness calibration

The calibration gate requires every known-good witness to pass both checks.
Every intentionally flawed witness must pass simulation and fail the reset
wiring rule:

```bash
integrations/harbor/validate_reset_release_witnesses.sh
```

## Validate all Oracle solutions

From the repository root:

```bash
harbor run \
  -p integrations/harbor/svgap-reset-release \
  -a oracle \
  -o .harbor-jobs/oracle-reset-release \
  --n-concurrent 1
```

All eight tasks must receive `reward = 1`, `functional_accept = 1`, and
`structural_accept = 1`.

## Local development environment

If the Docker socket is not at its default location, export `DOCKER_HOST` for
the selected runtime. If the Compose plugin is outside Docker's default
configuration, use a `DOCKER_CONFIG` that declares the plugin directory. Keep
job output under the ignored `.harbor-jobs/` directory so the daemon can mount
verifier logs back to Harbor. The `harbor view` process must inherit the same
Docker environment and agent credential selectors as the jobs it analyzes.

## Publication gate

Do not publish a dataset version until:

1. All known-good and intentionally flawed witness pairs pass calibration.
2. All eight Oracle solutions receive full reward.
3. At least one non-Oracle Harbor agent completes all eight tasks.
4. The collected SV-Gap reports and Harbor metrics agree.
5. `unknown` and `tool_error` remain non-passing outcomes.
6. Task descriptions, image digest, and package version match the cited
   SV-Gap release.
7. The public page contains no workstation paths, credentials, or claims that
   extend beyond the retained evidence.

The Harbor Hub package is an execution and discovery surface. Reviewed result
contributions remain in the SV-Gap repository, and Harbor Hub uploads remain
optional.
