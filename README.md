# NexForge v6.0 — Proof of Concept (Repository omnia)

**A robust architecture to constrain artificial intelligence in Cyber-Physical Systems (CPS)**

> We don't ask AI to "write safe code".
> We place it inside a **fixed, rigid architecture** that forces it to produce deterministic, safe systems.

---

## 🎯 What is this project?

NexForge is a **compiler + hard kernel** that transforms a simple domain description (YAML) into a CPS simulation system:
- ✅ Reads YAML and translates it into a fixed Intermediate Representation (IR).
- ✅ Checks 12 strict architectural rules (no duplicates, no invalid references).
- ✅ Performs dimensional analysis (SI units) and prevents mixing (no Volts + Celsius).
- ✅ Solves real ordinary differential equations (ODE).
- ✅ Runs a Safety Guardian that monitors contracts every 10 ms.
- ✅ If a safety contract is breached, it issues a **VETO** immediately and shuts down the system.
- ✅ Records the entire session, and you can replay it with exactly the same result.
- ✅ 17 unit tests (Pytest) passing.

**All of this from a single YAML file – without writing any runtime code.**

---

## ✅ What was actually achieved (Proof of Concept)

We successfully ran the project on **three different real-world domains**, proving the architecture is **Domain‑Agnostic** (independent of the field):

| Domain | YAML file | Contracts | Faults tested | VETO result |
|--------|-----------|:--------:|----------------------|:--------:|
| Water Pump | `domains/pump.yaml` | 3 | Motor failure, Overheating | ✅ VETO + SHUTDOWN |
| EV Charger | `domains/ev_charger.yaml` | 4 | Plug disconnect, Ground fault | ✅ Multiple VETOs |
| Data Center Fan | `domains/datacenter_fan.yaml` | 6 | Vibration, Stall, Overheating | ✅ 3 different contracts triggered |

**All of this was done without modifying the core Runtime Kernel. The only change was a small fix in the simulator (`physics.py`) to inject faults directly into the physical state.**

---

## 🧠 Why developers will be interested

| What they'll find | Why it matters |
|-------------------|----------------|
| **Novel idea** | "Constrained Architecture" – limiting AI within a rigid architecture, instead of dangerous free code. |
| **Ready foundation** | Safety Engine + Compiler + Validator ready to use and modify. |
| **Easy to extend** | Add any new domain (elevator, fridge, drone) just with a YAML file – no core changes. |
| **Safe test environment** | Test safety ideas in simulation before touching a real machine. |
| **Educational tool** | Suitable for universities teaching safety-critical systems engineering. |
| **Open future** | Clear roadmap towards Multi‑Agent, ESP32, Dashboard, and LLM Integration. |
| **Open source** | Apache License – use it, modify it, contribute freely. |

---

## 🧩 Extensibility (Plugin Domains)

Any domain can be added **without modifying the core** as long as it respects this YAML structure:

```yaml
metadata:
  name: domain_name
  description: "description"
sensors: [ { name: x, unit: U, min: a, max: b, default: c }, ... ]
actuators: [ { name: y, unit: U, min: a, max: b, default: c, fail_safe_value: f }, ... ]
contracts:
  - name: contract_name
    assume: "expression"
    guarantee: "expression"
    reason: "reason for tripping"
    safety_class: CRITICAL
physics:
  states: [ { name: var, unit: U, initial: val }, ... ]
  equations:
    var: "dx/dt = ..."
control:
  strategy: PID
  target_sensor: sensor_name
  output_actuator: actuator_name
  setpoint: target_value
timing: { safety_loop_hz: 100, control_loop_hz: 50, telemetry_hz: 10 }
deployment: { target: mock }
```

Examples that can be added right now: elevator, cold_storage, drone, nuclear_reactor.

---

## ⚠️ Important Warning

**This project is a Proof of Concept only.**

- ❌ Not suitable for direct use on real hardware (ESP32, STM32…)
- ❌ Currently uses MockHAL (fake hardware) for simulation
- ❌ Has not undergone independent safety audits or certifications

**Any use on real hardware is at the user's own risk.**

---

## 🚀 Quick Start

```bash
git clone https://github.com/Mouafek91/omnia-.git
cd omnia-/nexforge-v6          # or cd nexforge-v6 if you cloned directly
pip install -e .[dev]
nexforge list-domains
nexforge compile domains/pump.yaml
nexforge simulate domains/pump.yaml -d 10 --scenario motor_failure --record sessions/run.json
nexforge replay sessions/run.json --domain domains/pump.yaml
pytest
```

You can also run custom scenarios using the provided scripts:

```powershell
python run_sim_overheating.py          # to see overheating VETO
python "run_sim motor failure - Copy.py"   # for motor failure
python run_sim_ev_charger.py           # for the EV charger
python run_sim_datacenter_fan.py       # for the data center fan
```

---

## 👥 For Contributors

All contributions are welcome! The project is still in the Early Prototype stage, and your contribution will shape its future.

### ✅ What you can contribute (recommended and safe)

| Area | What to do |
|------|------------|
| Adding YAML domains | Put your file in `domains/` (elevator, fridge, fan, robot…) |
| Fault scenarios | Add a new scenario in `nexforge/scenarios/` |
| New tests | Add tests in `tests/` to cover new domains |
| Documentation | Translate docs, write examples, add diagrams |
| Plugin SDK | Add a Validator or Domain Plugin via `nexforge/plugins/` |

### ⚠️ Areas requiring caution (do not modify without deep understanding)

| Area | Why caution |
|------|-------------|
| Hard core (`nexforge/compiler/`, `nexforge/runtime/safety.py`) | Any error here affects determinism and safety. |
| IR Schema (`nexforge/compiler/ir.py`) | Changing it will impact all domains. |
| Safe Evaluator (`nexforge/compiler/expr.py`) | Any vulnerability here is a security risk. |

**Golden rule:** If your change would alter the core behavior for all domains, open an Issue first for discussion.

---

## 🛣️ Roadmap

### v6.0 (current) — Completed ✅

- Compiler + Validator + Safety Engine + Simulator + Replay
- Proof of concept demonstrated across 3 different physical domains

### v7.0 (planned)

- **Multi‑Agent layer for YAML generation** (Orchestrator + DomainAgent + Reviewer…)
  - Their only role is to collaborate on writing the best YAML.
  - They are not allowed to touch the hard core.
- **LLM assistant for YAML writing** (Grok / Ollama / OpenAI)
  - Infers YAML from a description.
- **ESP32 code generator via fixed templates** (not via AI)
  - Ensures Dual‑Core and Safety Path.
- **Web dashboard** (FastAPI + WebSocket + Chart.js)

### Long‑term goal

Make NexForge a general framework for **"Constrained Agentic Architectures"**, where AI is **constrained to the role of spec writer** and the rigid architecture is the **executor and judge**.
This principle will apply to: CPS, finance, cybersecurity, robotics…

---

## 📜 Philosophy

> "Architecture Engineering > Prompt Engineering"

We don't want an unconstrained LLM that hallucinates.
We want an LLM bound within a rigid architecture that guarantees:
- Safety‑First
- Determinism
- Verifiability

---

## 📄 License

Apache License — use it, modify it, contribute freely.

---

**Lead Developer:** [Mouafek91](https://github.com/Mouafek91) (Tunisia)
**Project Status:** Early Prototype — Successful Proof of Concept
