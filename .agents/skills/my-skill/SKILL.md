---
description: Develop software projects in a practical, modular,
  maintainable style with deliberate design and minimal overengineering.
  Use when planning, architecting, implementing, refactoring, or
  reviewing software.
name: project-development
---

# Sridhar's Project Development Skill

## Purpose

Build software that solves the actual problem cleanly and can grow when
real requirements appear. Favor thoughtful engineering over either
quick-and-dirty code or architecture for architecture's sake.

The guiding principle is:

> Keep the design as simple as possible, but make the important
> boundaries, responsibilities, and extension points clear.

Do not assume every project needs the same architecture. Adapt the
design to the project's size, domain, constraints, and likely evolution.

## Core principles

1.  **Solve the real problem first.** Understand the user workflow and
    the pain point before proposing components or abstractions.
2.  **Avoid overengineering.** Do not add layers, services,
    configuration systems, dependencies, or abstractions without a
    concrete reason.
3.  **Use modular architecture.** Separate responsibilities where doing
    so improves comprehension, testing, replacement, or independent
    change.
4.  **Keep APIs simple.** Prefer a small, understandable public API.
    Hide implementation details that callers should not need to know.
5.  **Design for reasonable change.** Make likely extension points
    replaceable without building speculative plugin systems for
    hypothetical futures.
6.  **Use design patterns intentionally.** Apply a known pattern when it
    clearly addresses a recurring design problem. Never use a pattern
    merely to make the architecture look sophisticated.
7.  **Prefer practical working software.** Implement in small,
    verifiable increments rather than designing a large system in
    advance.
8.  **Verify behavior.** Do not assume an API, library feature,
    configuration option, or layout behavior works as expected; inspect
    documentation or test it.

## Workflow

### 1. Understand the project

Before coding:

-   Identify the problem, intended users, inputs, outputs, and main
    workflows.
-   Read the existing repository structure, conventions, documentation,
    and tests.
-   Identify language, framework, runtime, platform, and dependency
    constraints.
-   Determine what already exists and what should be preserved.
-   Separate confirmed requirements from assumptions.
-   Ask a concise question only when a missing decision blocks a sound
    implementation. Otherwise, state a reasonable assumption and
    proceed.

Do not replace or reorganize working code just because another structure
is fashionable.

### 2. Propose the smallest sound design

Describe the proposed structure briefly before making broad changes:

-   Main modules and each module's responsibility.
-   Important data/control flow.
-   Public API and internal implementation boundaries.
-   Dependencies and why each is needed.
-   Any design pattern being used and the specific problem it solves.

Keep the design proportional to the project. A small CLI may need only a
few modules. A reusable library or runtime may justify stronger
boundaries and abstractions.

### 3. Implement incrementally

-   Build one coherent feature or vertical slice at a time.
-   Keep functions, classes, and modules focused.
-   Prefer clear names and straightforward control flow.
-   Avoid duplicated logic when a small shared function or module
    genuinely improves consistency.
-   Keep example programs, demos, and test entry points separate from
    framework/library logic.
-   Do not put application-specific policy into a reusable core unless
    it truly belongs there.
-   Preserve existing public behavior unless a change is required and
    explained.
-   Avoid unrelated refactors.

After each meaningful change, run the narrowest relevant test or
verification, then broader checks when appropriate.

### 4. Review and finish

Before declaring work complete:

-   Check that the implementation meets the stated requirements.
-   Run relevant tests, builds, linters, or type checks available in the
    project.
-   Inspect error paths and edge cases.
-   Check for unnecessary dependencies, abstractions, configuration, and
    duplicated code.
-   Confirm that examples demonstrate usage without becoming framework
    internals.
-   Update documentation where behavior or public APIs changed.
-   Report what changed, what was verified, and any known limitations
    honestly.

Never claim tests passed if they were not run.

## Architecture guidance

### Modules and responsibilities

Use modules to create meaningful boundaries, not simply to maximize the
number of files.

Good reasons to separate a module include:

-   It has a distinct responsibility.
-   It changes for different reasons from neighboring code.
-   It can be tested independently.
-   It represents a replaceable implementation behind a stable
    interface.
-   It is reused by multiple parts of the project.

Avoid both extremes: one giant file containing unrelated
responsibilities, and dozens of tiny files that make navigation harder.

### Public API and internal implementation

-   Keep the public surface small and consistent.
-   Expose concepts users of the library actually need.
-   Keep provider-, platform-, or implementation-specific details behind
    suitable interfaces.
-   Prefer dependency injection or explicit configuration when it makes
    implementations replaceable and tests easier.
-   Do not create an abstraction for a single implementation unless
    there is a real boundary or credible need for another
    implementation.

For reusable libraries, keep usage examples in a separate `examples/`
directory where appropriate. Example code is a demonstration or test
entry point, not framework logic.

### Dependencies

-   Prefer the standard library when it is sufficient.
-   Add a dependency when it materially reduces complexity, improves
    reliability, or provides necessary functionality.
-   Avoid adding packages for trivial helpers.
-   Consider platform support, maintenance, licensing, footprint, and
    installation cost.
-   Do not build a custom replacement for a mature dependency without a
    clear reason.

### Configuration

-   Keep defaults sensible.
-   Make configuration explicit and discoverable.
-   Avoid scattering constants and environment reads throughout the
    code.
-   Do not create a large configuration framework for a handful of
    settings.
-   Validate configuration at an appropriate boundary and produce
    actionable errors.

### Errors and logging

-   Handle errors at the layer that has enough context to respond
    meaningfully.
-   Preserve useful error details; do not silently swallow failures.
-   Avoid excessive catch-all exception handling.
-   Use consistent error types or result conventions when they improve
    the public API.
-   Keep logs useful and appropriately scoped; do not log secrets or
    flood normal operation.

### Testing

-   Test observable behavior and important contracts.
-   Cover normal paths, meaningful edge cases, and failure paths.
-   Keep tests understandable and deterministic where practical.
-   Use unit tests for isolated logic and integration tests for
    important module boundaries.
-   Do not introduce elaborate test infrastructure without a project
    need.
-   Treat a small reproducible example as useful evidence, but do not
    confuse it with a complete test suite.

## Design-pattern policy

Choose patterns based on the problem, not by quota.

Potentially useful patterns include:

-   **Strategy** when multiple interchangeable algorithms or providers
    are needed.
-   **Adapter** when integrating an external API or making incompatible
    interfaces work together.
-   **Factory** when object creation has meaningful selection or setup
    logic.
-   **Registry** when components or tools need explicit registration and
    lookup.
-   **Observer / event-driven design** when multiple consumers genuinely
    need to react to changes without tight coupling.
-   **Facade** when a complicated subsystem needs a simpler public entry
    point.
-   **Repository** when persistence access needs a meaningful boundary.
-   **Command** when operations need to be represented, queued, logged,
    or executed uniformly.

These are examples, not defaults. Prefer a direct function or simple
class when it solves the problem more clearly.

When introducing a pattern, explain: 1. The concrete problem. 2. Why the
pattern fits. 3. The complexity it adds. 4. Why a simpler alternative is
insufficient.

Do not stack patterns unnecessarily or create interfaces with only
ceremonial value.

## Agent and tool-based projects

For projects involving LLMs, agents, or tools:

-   Keep model/provider integration separate from agent behavior where
    that boundary is useful.
-   Keep tools as independently understandable units with explicit
    inputs and outputs.
-   Use a registry or selector only when dynamic selection or discovery
    is actually required.
-   Keep conversation history separate from temporary
    execution/workspace state when their lifecycles differ.
-   Prefer one capable agent with multiple independent tools over a
    manager-and-specialist-agent hierarchy when that simpler design
    meets the requirements.
-   Add multiple agents only when distinct roles, independent context,
    parallelism, or measurable quality improvements justify the
    coordination cost.
-   Keep example usage separate from runtime/framework implementation.

A modular arrangement such as configuration, provider/model selection,
agent logic, tool registry, individual tools, and examples can be
appropriate for a reusable agent library. Treat it as a project-specific
option, not a mandatory template.

## Communication style while developing

-   Explain decisions in plain, direct language.
-   Show the relevant folder structure when architecture is being
    discussed.
-   Explain what each important module owns.
-   When suggesting a pattern or abstraction, state the problem it
    solves.
-   Do not dump large amounts of code without explaining where it
    belongs and how the pieces connect.
-   Be honest about trade-offs and uncertainty.
-   Avoid repeating generic best practices that do not affect the
    current decision.

## Decision checklist

Before adding a component, abstraction, dependency, or pattern, ask:

1.  What concrete problem does this solve?
2.  Is the problem present now, or am I speculating about a future
    requirement?
3.  Would a simpler function, module, or direct implementation work?
4.  Does this create a useful boundary or just another layer?
5.  Does it make the public API or day-to-day development easier?
6.  Can it be tested and understood without excessive setup?

If the benefit is unclear, do not add it yet.

## Important distinction

The user's preferences are not a rigid architecture template. The goal
is not to force every project into the same folder structure or design.
Preserve the principles---simplicity, modularity, clear APIs, deliberate
patterns, incremental implementation, and verification---while adapting
the implementation to the actual project.
