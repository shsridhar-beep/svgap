# Disputed-finding regression fixtures

SV-Gap is backend- and evidence-neutral: a contribution may challenge the
reference oracle (see
[CONTRIBUTING.md](https://github.com/shsridhar-beep/svgap/blob/main/CONTRIBUTING.md)).
A disputed-finding fixture makes that kind of disagreement reviewable instead
of a comment on an issue that nobody can rerun.

[`examples/disputed_finding_template`](https://github.com/shsridhar-beep/svgap/tree/main/examples/disputed_finding_template)
is a template for this. It contains:

- `design.sv` / `tb.sv` — a synthetic RTL fixture and its functional
  testbench;
- `manifest.toml` — the intent declaration the reference checker runs
  against; and
- `expected-finding.json` — the disagreement itself, recorded as data
  rather than prose.

`expected-finding.json` has four required fields:

- `rule_id` — the finding you are disputing (must match a rule ID the
  reference checker actually emits);
- `checker_status` — the status you expect the checker to keep reporting
  (`fail` or `unknown`);
- `claim` — your specific reasoning: which structural evidence or
  functional trace you believe the checker is missing or misreading, not a
  general objection; and
- `disposition` — `"disputed"` until a maintainer or backend change
  resolves it. Nothing in this repository is allowed to flip a checker
  result to `pass` because a dispute file exists next to it;
  `tests/test_disputed_finding.py` asserts the finding still fires.

The checked-in template is a placeholder, not a real dispute: it reuses the
binary-bus-crossing pattern from
[`examples/gray_counter`](https://github.com/shsridhar-beep/svgap/tree/main/examples/gray_counter)
so the regression test has something concrete to run.

## Filing a real dispute

1. Copy `examples/disputed_finding_template` to a new directory named for
   your case.
2. Replace `design.sv`, `tb.sv`, and `manifest.toml` with a minimized,
   non-confidential reproducer distilled from the design you are disputing.
   It must stay within the project's
   [digital RTL scope boundary](scope-boundary.md) and use an existing rule
   category; contain no proprietary RTL or commercial-tool output.
3. Update `expected-finding.json`: point `rule_id` at the finding you
   disagree with and write your `claim`.
4. Run the fixture locally (`svgap check <manifest>` plus the functional
   commands in `manifest.toml`) and confirm the checker still reports
   `checker_status` on your reproducer.
5. Open a pull request. Leave `disposition` as `"disputed"` — a maintainer
   updates it once the disagreement is reviewed and resolved, in either
   direction.
