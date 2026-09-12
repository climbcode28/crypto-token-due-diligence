# EVM finding markers

User request: display ✅ Good, 🟡 Potential Risk and 🔴 Bad for each finding.

Implemented explicit chat/report guidance and changed the renderer’s Good marker from
🟢 to ✅. Yellow/red markers remain in place; the rendered legend now uses all three.
Machine summary.signal values, evidence gates, schemas and backend behavior are unchanged.
Versioned workflow 1.4.3 and reporting 1.1.2; mirrored the Claude Code copy while retaining
its tool conventions and adjusted paths. Existing research reports and evidence stay frozen.

Review: checked marker mapping, unknown qualifiers, unchanged label validation, and mirror
parity. Reconciled a concurrent matching Claude marker update and its documentation. Strengthened existing positive, unknown and adverse rendering regression assertions.
Canonical and mirrored EVM standard-library suites each pass 172 tests.

The optional skill-creator frontmatter checker could not run because PyYAML is absent;
frontmatter was not changed. Both standard-library EVM suites passed.
