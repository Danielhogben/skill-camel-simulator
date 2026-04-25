# CAMEL Simulator

Multi-agent role-playing conversation simulator with scenario definition, turn-limited execution, self-evolving conversations, and training data export.

## What it does

Creates two-agent role-playing sessions (user + assistant roles), defines conversation scenarios with task specifications, runs turn-limited conversations, supports self-evolving refinement, and exports conversation traces as training data.

## Commands

| Command | Description |
|---------|-------------|
| `init <simulation> --roles <user,assistant>` | Create a simulation with two agent roles |
| `scenario <sim> --task <t> --domain <d>` | Define a conversation scenario with task specification |
| `run <sim> [--turns N]` | Execute role-playing conversation with turn limits |
| `evolve <sim> --rounds <N>` | Self-evolving conversation where agents refine their approach |
| `export <sim> --format <jsonl\|json\|csv>` | Export conversation traces as training data |

## Examples

```bash
python3 camel_simulator.py init tutoring --roles student,tutor
python3 camel_simulator.py scenario tutoring --task "Explain recursion" --domain computer_science
python3 camel_simulator.py run tutoring --turns 10
python3 camel_simulator.py evolve tutoring --rounds 3
python3 camel_simulator.py export tutoring --format jsonl
```

## Role-playing format

Each simulation has:
- **User agent** — plays the role of the requester/questioner
- **Assistant agent** — plays the role of the expert/provider
- **Task specification** — what the conversation should accomplish
- **Termination criteria** — when the conversation ends

## Self-evolving mode

In evolve mode, agents iteratively:
1. Have a conversation
2. Review the conversation quality
3. Adjust their prompts and behavior
4. Have an improved conversation
5. Repeat for N rounds

## Export formats

- **jsonl** — one JSON object per line (for fine-tuning)
- **json** — full conversation structure with metadata
- **csv** — flattened turn-by-turn data
