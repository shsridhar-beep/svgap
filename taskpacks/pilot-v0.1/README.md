# Pilot v0.1 generation tasks

Six small SystemVerilog generation tasks exercise single-bit CDC, logic-before-CDC,
multi-bit coherence, and reset release. Prompts state production requirements but
do not name SV-Gap rules or prescribe internal signal names.

Each raw response can be evaluated with:

```sh
svgap pilot taskpacks/pilot-v0.1/tasks/level_crossing response.txt --model MODEL_ID
```

The command extracts the named module, records hashes and provenance, runs the
functional test, and applies the reference structural oracle. Generated outputs
remain ignored by Git by default.
