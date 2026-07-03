# Security

SV-Gap processes untrusted generated RTL by invoking external EDA tools. Treat
candidate files as untrusted input and run evaluations in an isolated container
or disposable worker. The v0.1 local runner does not provide a security sandbox.

Do not run contributed functional commands on a workstation containing secrets.
Public task packs must not contain credentials, proprietary RTL, or unreviewed
shell commands.

Do not publish exploit details for active vulnerabilities. Report them privately
to project maintainer Shraddha S at `shsridhar@nvidia.com`.
