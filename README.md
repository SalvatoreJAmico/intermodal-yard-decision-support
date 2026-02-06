# Intermodal Yard Decision Support System (Prototype v1)

A **Python / Streamlit–based decision-support prototype** that simulates intermodal rail yard operations from container arrival through train departure. The system is intentionally designed to be **transparent, deterministic, and explainable**, rather than an unrealistically optimized scheduler.

---

## Project Purpose

This project demonstrates how operational decisions in an intermodal yard affect outcomes such as **missed connections, urgency before departures, and recovery under disruption**.

The prototype explicitly avoids “perfect optimization” assumptions. Instead, it models **human checkpoints, throughput limits, fixed departure schedules, and time pressure**, making it suitable for walkthroughs, analysis, and future system design discussions.

---

## What the Prototype Models (As Built)

The current prototype models how an intermodal yard:

- Accepts arriving containers into an **arrival buffer**
- Processes containers through **human confirmation checkpoints**
- Places containers into the yard and retrieves them to staging
- Loads containers onto trains at **fixed scheduled departures**
- Enforces **capacity vs demand** at each departure
- Records **missed connections** when demand exceeds staged supply
- Handles **operational disruptions** (e.g., crane outage, train cancellation)
- Detects **urgency windows** prior to departures and applies urgency-aware strategies

All core flow logic is deterministic and inspectable.

---

## Core Concepts

### Container Lifecycle (v1 Abstraction)

In Prototype v1, container behavior is modeled using **aggregated counters** rather than per-container objects. This preserves correctness while keeping behavior explainable.

Lifecycle states represented:

- Arrival Buffer (unconfirmed)
- Confirmed Waiting Placement
- Staged (ready to load)
- Loaded / Departed
- Missed Connection

---

### Human Checkpoints

Human decision points are **explicitly modeled** as queues rather than automated decisions:

- Arrival / gate confirmation
- Yard placement approval
- Retrieval and staging approval
- Final train loading

This reflects real-world operational control points.

---

## Urgency & Time-Critical Behavior

- The system computes a **real urgency window** at **T–120 minutes** before the next scheduled departure
- Urgency entry is logged in the event feed
- An **Urgency-Aware strategy** increases placement and staging throughput during this window

This makes time pressure visible before missed connections occur.

---

## Scenarios & Strategies

### Implemented Scenarios

- **Baseline Day**
- **Port Surge** (increased arrivals)
- **Crane Down** (reduced throughput)
- **Train Cancelled** (scheduled departure does not run)

### Implemented Strategies

- **Baseline (Shortest Stack)** — normal throughput
- **Urgency-Aware (Planned)** — throughput boost during urgency windows
- **Lookahead (Planned)** — placeholder only

Strategies affect **throughput only**, not container routing.

---

## Key Performance Indicators (KPIs)

### Real KPIs

- Missed Connections
- Cancelled Departures

### Placeholder / UI Scaffolding KPIs

- Rehandles per container
- Yard utilization
- On-time percentage
- Average container dwell time

Placeholder KPIs are clearly labeled and exist to reserve UI space for future implementation.

---

## User Interface

The prototype is delivered as a **Streamlit dashboard** supporting:

- Scenario and strategy selection
- Real-time simulation clock (anchored to current date/time on reset)
- Yard flow visualization (mock)
- Human checkpoint queue monitoring
- KPI review
- Event timeline / operations feed
- Predefined example simulations for fast demonstrations

Simulation controls (Reset / Step / Run / Example buttons) are **demo-only** and would be replaced by real event ingestion in production.

---

## Example Simulations

The dashboard includes predefined example runs that:

- Reset the simulation
- Run forward for a fixed number of hours
- Produce a summary table
- Display a sample of notable operational events

These are intended for **walkthroughs and review**, not continuous operation.

---

## Repository Structure

```text
app.py          # Streamlit application (prototype v1)
docs/           # Consolidated specification (as-built)
```

(Additional folders such as simulation engines, strategies, and reporting are intentionally deferred.)

---

## Specifications

A **single consolidated specification document** is stored in the `docs/` directory and serves as the **authoritative source of truth** for this prototype.

Earlier draft documents (lifecycle tables, operational rules, assumptions) have been superseded and are retained only for historical reference if present.

---

## Roadmap (High-Level)

- **Prototype v1 (Complete):** Yard-level decision-support simulation
- **Future Phases (Not Implemented):**
  - Per-container object modeling
  - Stack legality and rehandle mechanics
  - Network-level empty container repositioning
  - Optimization and automated recommendations

---

## Disclaimer

This project uses **synthetic data and publicly defensible assumptions**. It does not use proprietary railroad data and does not claim to replicate any specific terminal.

It is a **decision-support prototype**, not a production scheduling system.
