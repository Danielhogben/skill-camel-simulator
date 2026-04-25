# Camel Simulator

Simulate multi-agent role-playing scenarios. Define roles, run conversations, evolve scenarios, and export results.

**Category:** AI Agents

**Language:** Python

## Quick Start

```bash
python3 camel_simulator.py help
```

## Commands

| Command | Description |
|---------|-------------|
| `---------` | ------------- |
| `init <simulation> --roles <user,assistant>` | Create a simulation with two agent roles |
| `scenario <sim> --task <t> --domain <d>` | Define a conversation scenario with task specification |
| `run <sim> [--turns N]` | Execute role-playing conversation with turn limits |
| `evolve <sim> --rounds <N>` | Self-evolving conversation where agents refine their approach |
| `export <sim> --format <jsonl\` | json\ |

## Files

- `SKILL.md` (1KB)
- `camel_simulator.py` (21KB)

---

*Part of [Hermes Skills](https://github.com/Danielhogben/hermes-skills) — the world's largest open-source AI agent skill collection.*
