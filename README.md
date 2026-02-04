# Intermodal Yard Decision Support System (Prototype)

A Python-based decision-support prototype that simulates intermodal rail yard operations from container arrival to train departure. The system explicitly models human confirmation checkpoints, yard stacking constraints, rehandles, missed connections, and KPI-driven evaluation.

---

## Project Purpose

This project is designed to model real-world operational trade-offs in intermodal rail yards. It intentionally avoids unrealistic *“perfect optimization”* assumptions and instead focuses on decision-support logic under physical constraints, congestion, and uncertainty.

---

## What the System Models

The system models how an intermodal yard:

- Accepts arriving containers through a human-confirmed gate process  
- Decides where to stack containers in a constrained yard  
- Retrieves and stages containers ahead of fixed train departures  
- Handles rehandles caused by blocked containers  
- Manages missed connections and reassignment  
- Measures operational performance using KPIs  

---

## Core Concepts

### Container Lifecycle

Containers move through a finite state machine including:
- Arrival buffer  
- Yard placement  
- Urgency window  
- Retrieval  
- Staging  
- Departure  
- Missed connection reassignment  

### Human Checkpoints

Human confirmation points are explicitly modeled at:
- Arrival confirmation  
- Placement approval  
- Retrieval / staging approval  
- Final train loading  

---

## Key Performance Indicators (KPIs)

- Rehandles per container  
- Yard utilization  
- On-time train connection rate  
- Average container dwell time  
- Missed connections  
- Recovery time under disruption scenarios  

---

## User Interface

The user interface is implemented as a **Streamlit dashboard** to support:

- Scenario comparison  
- Yard visualization  
- Human checkpoint monitoring  
- KPI review  

Streamlit is used as a rapid decision-support prototype UI.

---

## Repository Structure (Planned)

app.py # Streamlit dashboard
docs/ # Specification documents
sim/ # Simulation engine (planned)
strategies/ # Decision strategies (planned)
reports/ # Generated outputs (planned)



---

## Specifications

System behavior is governed by formal specification documents stored in the `docs/` directory, including:

- Data assumptions  
- Operational rules  
- Event flow with human checkpoints  
- Container lifecycle states  
- State transition tables  

These documents serve as the source of truth for the simulation logic.

---

## Roadmap

- **Phase 1:** Streamlit UI shell  (in progress)
- **Phase 2:** Minimal simulation engine  
- **Phase 3:** Strategy comparison and reporting  

---

## Disclaimer

This project uses synthetic data and publicly defensible assumptions. It does not use proprietary railroad data and does not claim to replicate any specific terminal.


