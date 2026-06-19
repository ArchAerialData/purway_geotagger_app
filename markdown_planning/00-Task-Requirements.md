# Task Planning Requirements

This file governs feature and edit planning files in `markdown_planning/`. It supplements the repository root `AGENTS.md`; the root instructions and any more specific future instructions remain binding.

## Planning File Rules

- Reserve this file as `00-Task-Requirements.md`.
- Give each requested feature, edit, or meaningful workstream its own markdown planning file.
- Name planning files with a two-digit sequence number followed by a short kebab-case description:
  - `01-feature-description.md`
  - `02-next-feature-description.md`
  - `03-another-edit.md`
- Assign numbers sequentially in the order tasks are accepted for planning.
- Do not reuse or renumber existing planning files. If a feature is abandoned, superseded, or merged into another task, record that status inside its existing file.
- Keep each feature plan focused on one feature or edit unless the user explicitly requests a combined plan.

## Compatibility Requirements

- Every planned feature or edit must be compatible with both macOS and Windows.
- Plans must call out any platform-specific behavior, filesystem assumptions, subprocess usage, packaging concern, or path handling concern.
- Implementation choices must preserve macOS pilot compatibility, including packaged `.app` launches where PATH may not include Homebrew locations.
- Implementation choices must also remain buildable and testable on Windows.
- Any feature plan that affects packaging, scripts, dependencies, subprocesses, file paths, Qt behavior, or CI must include explicit macOS and Windows verification steps.
- GitHub Actions compatibility is required. Plans must avoid changes that only work locally unless the plan also defines the CI updates needed to build and verify them.

## Required Structure For Each Feature Plan

Each numbered feature plan should include these sections unless the user explicitly asks for a different structure:

1. `Goal`
2. `Scope`
3. `Non-Goals`
4. `Current Behavior / Evidence`
5. `Design`
6. `Compatibility Notes`
7. `Implementation Phases`
8. `Verification Plan`
9. `Risks / Open Questions`
10. `Phase Notes`

## Phase Discipline

- Break implementation work into clear phases with checkboxes.
- Each phase must have a Gate that defines what must be true before the next phase starts.
- Agents must not begin the next phase until all checkboxes and the Gate for the current phase are complete.
- At the end of each completed phase, agents must update that feature's markdown file before moving on.

## Required Phase Updates

When a phase is completed, update the feature markdown file with:

- Completed checkboxes for the phase.
- A dated `Phase Notes` entry.
- A concise summary of what changed.
- Files or modules touched, when applicable.
- Verification commands, tests, manual checks, or reason verification was not run.
- Any deviations from the original plan.
- Any remaining risks, follow-up work, or debugging context discovered during implementation.

These updates are required so future agents can understand what was done, why it was done, and what evidence supports the current state.

## Source Of Authority

- User task request dated 2026-06-19.
- Repository root `AGENTS.md`.
- Existing project phase documents remain authoritative for implementation sequencing where applicable, including `PILOT_RAW_DATA_CONTEXT_AND_PLAN.md` and `IMPLEMENTATION_PHASES.md`.
