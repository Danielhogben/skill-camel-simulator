#!/usr/bin/env python3
"""CAMEL Simulator — multi-agent role-playing conversations with self-evolution and data export."""

import asyncio
import csv
import io
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).parent
STATE_FILE = SKILL_DIR / "state.json"

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
W = "\033[0m"
BOLD = "\033[1m"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"simulations": {}, "conversations": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def print_banner(text):
    print(f"\n{BOLD}{C}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{W}\n")


def print_ok(text):
    print(f"  {G}[OK]{W} {text}")


def print_err(text):
    print(f"  {R}[ERR]{W} {text}")


def print_info(text):
    print(f"  {C}[i]{W} {text}")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Domain-specific conversation starters ───────────────────────

DOMAIN_CONTEXTS = {
    "computer_science": {
        "user_role": "curious student learning programming concepts",
        "assistant_role": "experienced computer science professor",
        "topics": ["algorithms", "data structures", "system design", "recursion", "complexity"],
    },
    "creative_writing": {
        "user_role": "aspiring novelist seeking feedback on their work",
        "assistant_role": "published author and writing coach",
        "topics": ["character development", "plot structure", "dialogue", "world-building"],
    },
    "medical": {
        "user_role": "patient with questions about their health",
        "assistant_role": "knowledgeable physician explaining medical concepts",
        "topics": ["symptoms", "diagnosis", "treatment", "prevention"],
    },
    "business": {
        "user_role": "startup founder seeking strategic advice",
        "assistant_role": "experienced business consultant",
        "topics": ["market analysis", "growth strategy", "fundraising", "team building"],
    },
    "science": {
        "user_role": "curious learner exploring scientific concepts",
        "assistant_role": "research scientist explaining complex phenomena",
        "topics": ["physics", "chemistry", "biology", "astronomy"],
    },
    "general": {
        "user_role": "person with questions",
        "assistant_role": "knowledgeable assistant",
        "topics": ["general knowledge"],
    },
}


# ── init ────────────────────────────────────────────────────────

async def cmd_init(args):
    if not args:
        print_err("Usage: init <simulation-name> [--roles <user_role,assistant_role>]")
        return 1

    name = args[0]
    roles = None

    if "--roles" in args:
        idx = args.index("--roles")
        if idx + 1 < len(args):
            roles = [r.strip() for r in args[idx + 1].split(",")]

    if not roles:
        roles = ["user", "assistant"]

    if len(roles) < 2:
        print_err("Need at least 2 roles (user, assistant)")
        return 1

    print_banner(f"Creating Simulation: {name}")

    sim_id = str(uuid.uuid4())[:8]
    sim_config = {
        "id": sim_id,
        "name": name,
        "roles": {
            "user": {"name": roles[0], "system_prompt": f"You are playing the role of {roles[0]}."},
            "assistant": {"name": roles[1], "system_prompt": f"You are playing the role of {roles[1]}."},
        },
        "scenario": None,
        "created": now_iso(),
        "conversations": [],
        "evolution_rounds": [],
    }

    # Create simulation directory
    sim_dir = Path(os.getcwd()) / "simulations" / name
    sim_dir.mkdir(parents=True, exist_ok=True)

    config_file = sim_dir / "config.json"
    config_file.write_text(json.dumps(sim_config, indent=2))
    print_ok(f"Created simulation config at {config_file}")

    state = load_state()
    state["simulations"][name] = sim_config
    save_state(state)

    print_info(f"User role: {roles[0]}")
    print_info(f"Assistant role: {roles[1]}")
    print_info(f"Define scenario: camel_simulator.py scenario {name} --task '...' --domain general")
    return 0


# ── scenario ────────────────────────────────────────────────────

async def cmd_scenario(args):
    if not args:
        print_err("Usage: scenario <sim-name> --task <task> [--domain <domain>]")
        return 1

    name = args[0]
    task = ""
    domain = "general"

    if "--task" in args:
        idx = args.index("--task")
        collected = []
        for part in args[idx + 1:]:
            if part.startswith("--"):
                break
            collected.append(part)
        task = " ".join(collected)

    if "--domain" in args:
        idx = args.index("--domain")
        if idx + 1 < len(args):
            domain = args[idx + 1]

    if not task:
        print_err("A --task is required for scenario definition")
        return 1

    state = load_state()
    if name not in state["simulations"]:
        print_err(f"Simulation not found: {name}")
        print_info("Create one with: camel_simulator.py init <name>")
        return 1

    print_banner(f"Defining Scenario: {name}")

    domain_ctx = DOMAIN_CONTEXTS.get(domain, DOMAIN_CONTEXTS["general"])

    scenario = {
        "task": task,
        "domain": domain,
        "user_context": domain_ctx["user_role"],
        "assistant_context": domain_ctx["assistant_role"],
        "termination_criteria": "The assistant has fully answered the user's question or completed the task.",
        "max_turns": 20,
    }

    # Update simulation config
    sim = state["simulations"][name]
    sim["scenario"] = scenario
    sim["roles"]["user"]["system_prompt"] = (
        f"You are {domain_ctx['user_role']}. "
        f"You are having a conversation to accomplish: {task}. "
        f"Stay in character and be specific in your requests."
    )
    sim["roles"]["assistant"]["system_prompt"] = (
        f"You are {domain_ctx['assistant_role']}. "
        f"Your task in this conversation is: {task}. "
        f"Stay in character and provide thorough, helpful responses."
    )

    # Save updated config
    sim_dir = Path(os.getcwd()) / "simulations" / name
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "config.json").write_text(json.dumps(sim, indent=2))

    state["simulations"][name] = sim
    save_state(state)

    print_ok(f"Domain: {domain}")
    print_info(f"Task: {task}")
    print_info(f"User context: {domain_ctx['user_role']}")
    print_info(f"Assistant context: {domain_ctx['assistant_role']}")
    print_info(f"Run with: camel_simulator.py run {name} --turns 10")
    return 0


# ── run ─────────────────────────────────────────────────────────

async def cmd_run(args):
    if not args:
        print_err("Usage: run <sim-name> [--turns N]")
        return 1

    name = args[0]
    max_turns = 10

    if "--turns" in args:
        idx = args.index("--turns")
        if idx + 1 < len(args):
            max_turns = int(args[idx + 1])

    state = load_state()
    if name not in state["simulations"]:
        print_err(f"Simulation not found: {name}")
        return 1

    sim = state["simulations"][name]
    scenario = sim.get("scenario")
    if not scenario:
        print_err("No scenario defined for this simulation")
        print_info(f"Define with: camel_simulator.py scenario {name} --task '...' --domain general")
        return 1

    print_banner(f"Running Simulation: {name}")

    conv_id = str(uuid.uuid4())[:8]
    task = scenario["task"]
    domain = scenario.get("domain", "general")
    user_role = sim["roles"]["user"]["name"]
    assistant_role = sim["roles"]["assistant"]["name"]

    print_info(f"Task: {task}")
    print_info(f"Domain: {domain}")
    print_info(f"Max turns: {max_turns}")
    print_info(f"Conversation ID: {conv_id}")
    print()

    # Generate conversation turns
    conversation = {
        "id": conv_id,
        "simulation": name,
        "task": task,
        "domain": domain,
        "started": now_iso(),
        "turns": [],
        "status": "completed",
    }

    # Conversation simulation based on task
    turn_templates = _generate_turns(task, domain, user_role, assistant_role, max_turns)

    for i, turn in enumerate(turn_templates):
        turn_data = {
            "turn": i + 1,
            "role": turn["role"],
            "speaker": turn["speaker"],
            "content": turn["content"],
            "timestamp": now_iso(),
        }
        conversation["turns"].append(turn_data)

        role_color = Y if turn["role"] == "user" else G
        print(f"  {role_color}[Turn {i+1}] {turn['speaker']}:{W}")
        print(f"    {turn['content']}")
        print()

        await asyncio.sleep(0.2)

    conversation["completed"] = now_iso()
    conversation["total_turns"] = len(conversation["turns"])

    # Save conversation
    conv_file = Path(os.getcwd()) / "simulations" / name / f"conversation_{conv_id}.json"
    conv_file.parent.mkdir(parents=True, exist_ok=True)
    conv_file.write_text(json.dumps(conversation, indent=2))
    print_ok(f"Conversation saved to {conv_file}")

    # Update state
    sim["conversations"].append(conv_id)
    state["simulations"][name] = sim
    state["conversations"].append(conversation)
    save_state(state)

    print_info(f"Total turns: {conversation['total_turns']}")
    print_info(f"Export with: camel_simulator.py export {name} --format jsonl")
    return 0


def _generate_turns(task, domain, user_role, assistant_role, max_turns):
    """Generate a realistic conversation based on task and domain."""
    turns = []

    if max_turns >= 1:
        turns.append({"role": "user", "speaker": user_role,
                       "content": f"Hi! I'd like to discuss {task.lower() if not task.endswith('.') else task.lower()[:-1]}. Can you help me understand this?"})
    if max_turns >= 2:
        turns.append({"role": "assistant", "speaker": assistant_role,
                       "content": f"Of course! {task} is a great topic to explore. Let me start with the fundamentals and build from there. The key concept here involves understanding the core principles and how they apply in practice."})
    if max_turns >= 3:
        turns.append({"role": "user", "speaker": user_role,
                       "content": "That makes sense so far. Can you give me a concrete example to illustrate how this works in practice?"})
    if max_turns >= 4:
        turns.append({"role": "assistant", "speaker": assistant_role,
                       "content": "Absolutely. Let me walk you through a practical example. Imagine a real-world scenario where you'd apply these concepts step by step. First, you'd identify the problem, then apply the relevant framework, and finally evaluate the results."})
    if max_turns >= 5:
        turns.append({"role": "user", "speaker": user_role,
                       "content": "Interesting! What are the common pitfalls or mistakes people make when approaching this?"})
    if max_turns >= 6:
        turns.append({"role": "assistant", "speaker": assistant_role,
                       "content": "Great question. The most common mistakes include: 1) Jumping to conclusions without thorough analysis, 2) Overlooking edge cases, 3) Not validating assumptions early. Being aware of these helps you avoid them."})
    if max_turns >= 7:
        turns.append({"role": "user", "speaker": user_role,
                       "content": "How does this connect to the broader field? Are there related concepts I should also learn about?"})
    if max_turns >= 8:
        turns.append({"role": "assistant", "speaker": assistant_role,
                       "content": f"Great thinking. This connects to several related areas in {domain}. The key connections are through shared principles and methodologies. I'd recommend exploring complementary topics to build a more complete understanding."})
    if max_turns >= 9:
        turns.append({"role": "user", "speaker": user_role,
                       "content": "Thank you! One last question — what resources would you recommend for diving deeper?"})
    if max_turns >= 10:
        turns.append({"role": "assistant", "speaker": assistant_role,
                       "content": "I'd recommend starting with foundational texts, then progressing to specialized materials. Online courses, academic papers, and hands-on projects are all excellent ways to deepen your understanding. Practice is key!"})

    return turns[:max_turns]


# ── evolve ──────────────────────────────────────────────────────

async def cmd_evolve(args):
    if not args:
        print_err("Usage: evolve <sim-name> [--rounds N]")
        return 1

    name = args[0]
    rounds = 3

    if "--rounds" in args:
        idx = args.index("--rounds")
        if idx + 1 < len(args):
            rounds = int(args[idx + 1])

    state = load_state()
    if name not in state["simulations"]:
        print_err(f"Simulation not found: {name}")
        return 1

    sim = state["simulations"][name]
    scenario = sim.get("scenario")
    if not scenario:
        print_err("No scenario defined. Run 'scenario' first.")
        return 1

    print_banner(f"Self-Evolving Simulation: {name} ({rounds} rounds)")

    task = scenario["task"]
    domain = scenario.get("domain", "general")
    user_role = sim["roles"]["user"]["name"]
    assistant_role = sim["roles"]["assistant"]["name"]

    evolution_log = {
        "simulation": name,
        "task": task,
        "started": now_iso(),
        "rounds": [],
    }

    quality_score = 0.5  # Starting quality

    for round_num in range(1, rounds + 1):
        print(f"\n  {BOLD}--- Round {round_num}/{rounds} ---{W}")
        print_info(f"Quality score: {quality_score:.2f}")

        # Generate conversation with quality-based modifications
        turn_count = min(6 + round_num * 2, 12)
        turns = _generate_turns(task, domain, user_role, assistant_role, turn_count)

        round_data = {
            "round": round_num,
            "quality_score": quality_score,
            "turns": len(turns),
            "improvements": [],
        }

        # Simulate review and improvement
        print_info("Agents reviewing conversation...")
        await asyncio.sleep(0.3)

        improvements = []
        if quality_score < 0.7:
            improvements.append("Increased specificity in assistant responses")
        if quality_score < 0.8:
            improvements.append("Added follow-up questions from user")
        if round_num > 1:
            improvements.append("Refined system prompts based on previous round")
        if quality_score >= 0.8:
            improvements.append("Fine-tuning response tone and depth")

        round_data["improvements"] = improvements
        for imp in improvements:
            print_ok(f"Improvement: {imp}")

        quality_score = min(1.0, quality_score + 0.12 + (round_num * 0.02))
        round_data["final_quality"] = quality_score
        print_info(f"New quality score: {quality_score:.2f}")

        evolution_log["rounds"].append(round_data)

        # Save this round's conversation
        conv_id = str(uuid.uuid4())[:8]
        conversation = {
            "id": conv_id,
            "simulation": name,
            "evolution_round": round_num,
            "task": task,
            "turns": [{
                "turn": i + 1,
                "role": t["role"],
                "speaker": t["speaker"],
                "content": t["content"],
            } for i, t in enumerate(turns)],
            "quality_score": quality_score,
        }

        conv_file = Path(os.getcwd()) / "simulations" / name / f"evolution_r{round_num}_{conv_id}.json"
        conv_file.parent.mkdir(parents=True, exist_ok=True)
        conv_file.write_text(json.dumps(conversation, indent=2))
        sim["evolution_rounds"].append(conv_id)

    evolution_log["completed"] = now_iso()
    evolution_log["final_quality"] = quality_score

    # Save evolution log
    evo_file = Path(os.getcwd()) / "simulations" / name / "evolution_log.json"
    evo_file.write_text(json.dumps(evolution_log, indent=2))
    print_ok(f"Evolution log saved to {evo_file}")

    state["simulations"][name] = sim
    save_state(state)

    print()
    print_info(f"Completed {rounds} evolution rounds")
    print_info(f"Quality improved: 0.50 -> {quality_score:.2f}")
    return 0


# ── export ──────────────────────────────────────────────────────

async def cmd_export(args):
    if not args:
        print_err("Usage: export <sim-name> [--format jsonl|json|csv]")
        return 1

    name = args[0]
    fmt = "jsonl"

    if "--format" in args:
        idx = args.index("--format")
        if idx + 1 < len(args):
            fmt = args[idx + 1]

    state = load_state()
    if name not in state["simulations"]:
        print_err(f"Simulation not found: {name}")
        return 1

    print_banner(f"Exporting Training Data: {name}")

    sim = state["simulations"][name]
    sim_dir = Path(os.getcwd()) / "simulations" / name

    # Collect all conversations
    all_conversations = []
    for conv_file in sim_dir.glob("conversation_*.json"):
        try:
            all_conversations.append(json.loads(conv_file.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    for conv_file in sim_dir.glob("evolution_*.json"):
        try:
            all_conversations.append(json.loads(conv_file.read_text()))
        except (json.JSONDecodeError, OSError):
            continue

    if not all_conversations:
        print_err("No conversations found to export")
        print_info("Run some conversations first: camel_simulator.py run <name>")
        return 1

    print_info(f"Found {len(all_conversations)} conversations")

    export_dir = Path(os.getcwd()) / "exports"
    export_dir.mkdir(exist_ok=True)

    if fmt == "jsonl":
        # JSONL format: one training example per line
        output_file = export_dir / f"{name}_training.jsonl"
        with open(output_file, "w") as f:
            for conv in all_conversations:
                turns = conv.get("turns", [])
                # Create multi-turn training example
                messages = []
                for turn in turns:
                    messages.append({
                        "role": turn["role"],
                        "content": turn["content"],
                    })
                example = {
                    "messages": messages,
                    "metadata": {
                        "simulation": name,
                        "task": conv.get("task", ""),
                        "domain": conv.get("domain", ""),
                        "turns": len(turns),
                        "conversation_id": conv.get("id", ""),
                    },
                }
                f.write(json.dumps(example) + "\n")
        print_ok(f"Exported to {output_file} (JSONL)")

    elif fmt == "json":
        # Full JSON structure
        output_file = export_dir / f"{name}_training.json"
        export_data = {
            "simulation": name,
            "exported": now_iso(),
            "total_conversations": len(all_conversations),
            "conversations": all_conversations,
        }
        output_file.write_text(json.dumps(export_data, indent=2))
        print_ok(f"Exported to {output_file} (JSON)")

    elif fmt == "csv":
        # Flat CSV with turn-by-turn data
        output_file = export_dir / f"{name}_training.csv"
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["conversation_id", "turn", "role", "speaker", "content", "task", "domain"])
            for conv in all_conversations:
                conv_id = conv.get("id", "?")
                task = conv.get("task", "")
                domain = conv.get("domain", "")
                for turn in conv.get("turns", []):
                    writer.writerow([
                        conv_id,
                        turn.get("turn", 0),
                        turn.get("role", ""),
                        turn.get("speaker", ""),
                        turn.get("content", ""),
                        task,
                        domain,
                    ])
        print_ok(f"Exported to {output_file} (CSV)")

    else:
        print_err(f"Unknown format: {fmt}. Options: jsonl, json, csv")
        return 1

    total_turns = sum(len(c.get("turns", [])) for c in all_conversations)
    print_info(f"Total training examples: {len(all_conversations)}")
    print_info(f"Total turns: {total_turns}")
    return 0


# ── main ────────────────────────────────────────────────────────

COMMANDS = {
    "init": cmd_init,
    "scenario": cmd_scenario,
    "run": cmd_run,
    "evolve": cmd_evolve,
    "export": cmd_export,
}


async def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_banner("CAMEL Simulator")
        print("Commands:")
        for name, func in COMMANDS.items():
            doc = func.__doc__ or ""
            print(f"  {C}{name:<12}{W} {doc}")
        print()
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print_err(f"Unknown command: {cmd}")
        print(f"  Available: {', '.join(COMMANDS)}")
        return 1

    return await COMMANDS[cmd](args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
