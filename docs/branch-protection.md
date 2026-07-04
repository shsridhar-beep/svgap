# Main-branch protection

The public repository should protect `main` after the v0.2 CI workflow has
completed once and its matrix check names are visible.

Required policy:

- pull requests required for external changes;
- at least one approving review when another maintainer is available;
- conversation resolution required;
- required CI checks for Python 3.11, 3.12, 3.13, package, and container jobs;
- branch must be current before merge;
- force pushes and branch deletion disabled; and
- administrator bypass retained only while the project has one maintainer.

The policy is repository state rather than source code. Confirm it through the
GitHub branch-protection API after every workflow-name change.
