# Devotional Agent Blueprint

## Main agent

- [devotional-orchestrator.toml](../../../agents/devotional-orchestrator.toml)

## Skills

- [devotional-exegesis](../../../skills/devotional-exegesis/SKILL.md)
- [biblical-theology-bridge](../../../skills/biblical-theology-bridge/SKILL.md)
- [spiritual-formation-guide](../../../skills/spiritual-formation-guide/SKILL.md)
- [devotional-question-architect](../../../skills/devotional-question-architect/SKILL.md)
- [spiritual-slide-composer](../../../skills/spiritual-slide-composer/SKILL.md)

## Role contract and intended flow

The orchestrator owns the complete study and final response. It first identifies whether the user needs a direct answer, passage study, evaluation of an interpretation, discussion highlights, a study plan, or a prepared artifact. The skills below are conditional methods; they are not a mandatory pipeline and their internal handoffs should not appear as separate voices.

When the request calls for passage study, use the relevant stages in this order:

1. **Exegesis:** establish the passage boundaries, context, structure, literary movement, key terms, and authorial point from the local Bible corpus.
2. **Biblical theology:** where relevant, map a claim to its canonical connection and identify whether it is quotation, thematic continuity, pattern/typology, or analogy.
3. **Spiritual formation:** where requested or useful, move from the established meaning to concrete, gospel-shaped formation and pastoral application.
4. **Discussion and synthesis:** answer the user’s actual question, test interpretations with textual support and limits, and state the passage’s main thread.
5. **Optional outputs:** use question design, slides, maps, or NotebookLM handoff only when requested.

For a narrow follow-up, the orchestrator may answer directly from the relevant local passage without displaying every stage. Completeness means a well-supported answer at the requested depth, not the longest answer or the use of every skill.

## Design choice

Your original idea described three expert agents plus an optional Agent 0 question architect. I translated that into:

- one orchestrator agent
- five focused skills

This keeps the theological process staged, but avoids over-fragmenting runtime control. The orchestrator remains accountable for selecting only the needed skills, resolving differences among local resources, and presenting one coherent answer.

## Agent 0 mapping

`Agent 0 / Question Architect` is represented by:

- [devotional-question-architect](../../../skills/devotional-question-architect/SKILL.md)

Its job is now split into two explicit modes:

- `Front-end architect mode`
  - define the controlling question and study spine before exegesis starts
- `Back-end discussion mode`
  - produce discussion questions, reflection prompts, and a golden sentence after the study is complete

## Bible map capability

Instead of creating a separate sixth skill, the existing slide-composer skill now also covers the Bible-map handoff workflow:

- FHL-locked viewport
- FHL-locked contour
- contour validation with a 95% gate
- NotebookLM package preparation
- NotebookLM MCP upload
- stop at upload

