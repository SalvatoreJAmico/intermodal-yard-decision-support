"""
Intermodal Yard Decision Support System (Streamlit) — Prototype v1

Purpose (layman):
- This prototype simulates minute-to-minute intermodal yard flow and whether staged
  containers make scheduled train departures.

What is REAL in this prototype:
- Simulation clock (anchored to current date/time on reset)
- Deterministic flow model: arrivals → confirm → placement → staging → departure
- Real departure schedule: 06:00 / 12:00 / 18:00 / 23:00
- Capacity vs demand at each departure
- Missed connections tracking (real KPI)
- Train Cancelled scenario (real behavior at departure times)
- Urgency window (real): becomes “urgent” at T–120 minutes before next departure
- Strategy hook (real): “Urgency-Aware (Planned)” increases throughput during urgent windows
- Event feed driven by actual simulation step output
- Queue metrics (right panel) driven by real counters
- Example simulations (Ex 1–Ex 6): run preset scenarios and store a real summary + event sample

What is MOCK / UI scaffolding (clearly labeled):
- Yard View bar chart (random heights for visual scaffolding)
- Stack Inspector container list & attributes (mock IDs, mock urgency/train assignment)
- Several KPI row values (random for layout scaffolding)

How to use (demo controls):
- Reset: re-initialize model and anchor sim time to current clock
- Step (5 min): advance by one tick
- Run (1 hour): advance by 12 ticks (12 × 5 minutes)
- Ex 1–Ex 6: reset + run an 8-hour canned scenario and display a summary (great for demos)

Important note:
- This is a simulation / decision-support prototype. In production, state would be driven by
  real events (gates, cranes, hostlers, train ETAs) rather than demo buttons.
"""

# ==================================================
# Imports
# ==================================================
import streamlit as st
import pandas as pd
import random
from datetime import datetime


# ==================================================
# Configuration / Constants
# ==================================================
TIME_STEP_MINUTES = 5

# Departure schedule in minutes since midnight (time-of-day)
DEPARTURE_TOD_MINS = [360, 720, 1080, 1380]  # 06:00, 12:00, 18:00, 23:00

# Urgency definition: within T–120 minutes of next departure
URGENT_WINDOW_MINS = 120

# Run button advances by 1 hour per click (12 × 5 minutes)
RUN_STEPS_PER_CLICK = 12


# ==================================================
# Session State Initialization
# ==================================================
def init_state():
    """
    Initialize all app state variables in Streamlit session_state.

    Design choice:
    - v1 is counter-based (not per-container objects yet).
    - The right-side queue tables show mock IDs derived from these real counters.
    """
    # Anchor simulation clock to current real time (minute precision).
    # Store seconds separately so the UI feels like “now”.
    now = datetime.now()
    st.session_state.sim_minute = now.hour * 60 + now.minute
    st.session_state.sim_second_offset = now.second
    st.session_state.sim_start_date = now.date()

    # Deterministic seed controls reproducible MOCK UI elements
    # (yard chart + stack inspector only).
    st.session_state.run_id = 1
    st.session_state.seed = 7

    # ------------------------------
    # Real flow counters (v1 model)
    # ------------------------------
    st.session_state.arrival_buffer_count = 12
    st.session_state.confirmed_waiting_count = 8
    st.session_state.staged_count = 20
    st.session_state.departed_total = 0

    # Real KPI counters
    st.session_state.missed_total = 0
    st.session_state.cancelled_departures = 0

    # Simple train model (real for v1)
    st.session_state.train_capacity = 25
    st.session_state.train_demand_per_departure = 28

    # Urgency tracking (real)
    st.session_state.urgent_window = False
    st.session_state.prev_urgent_window = False
    st.session_state.mins_to_next_departure = None
    st.session_state.next_departure_label = None

    # Event feed output from the most recent step (real)
    st.session_state.last_events = []

    # Example-run output payload (set when Ex buttons are used)
    st.session_state.example_output = None


# Initialize state once per browser session
if "sim_minute" not in st.session_state:
    init_state()


# ==================================================
# Time / Departure Helpers
# ==================================================
def minutes_to_next_departure(sim_minute: int) -> int:
    """
    Returns minutes until the next scheduled departure, based on time-of-day.
    """
    tod = sim_minute % 1440  # minutes since midnight
    for d in DEPARTURE_TOD_MINS:
        if d > tod:
            return d - tod
    # none remaining today → next day at 06:00
    return (1440 - tod) + DEPARTURE_TOD_MINS[0]


def next_departure_label(sim_minute: int) -> str:
    """
    Returns HH:MM label for the next scheduled departure, based on time-of-day.
    """
    tod = sim_minute % 1440
    for d in DEPARTURE_TOD_MINS:
        if d > tod:
            hh = d // 60
            mm = d % 60
            return f"{hh:02d}:{mm:02d}"
    return "06:00"


# ==================================================
# Example Simulation Runner (Demo Utility)
# ==================================================
def run_sim_example(example_name: str, scenario_value: str, strategy_value: str, hours: int = 8):
    """
    Runs a canned simulation example.

    Behavior:
    - Resets the model (anchors time to current clock)
    - Advances the simulation forward in 5-minute ticks for N hours
    - Captures a summary + a small sample of “notable” events
    - Stores results in st.session_state.example_output for display
    """
    init_state()

    steps = (hours * 60) // TIME_STEP_MINUTES
    event_log = []

    for _ in range(steps):
        st.session_state.sim_minute += TIME_STEP_MINUTES
        step_flow(scenario_value, strategy_value)
        event_log.extend(st.session_state.last_events)

    # Summarize ending state (real counters)
    summary = {
        "Example": example_name,
        "Scenario": scenario_value,
        "Strategy": strategy_value,
        "Sim Hours": hours,
        "Departed Total": st.session_state.departed_total,
        "Missed Total": st.session_state.missed_total,
        "Cancelled Departures": st.session_state.cancelled_departures,
        "Arrival Buffer End": st.session_state.arrival_buffer_count,
        "Confirmed Waiting End": st.session_state.confirmed_waiting_count,
        "Staged End": st.session_state.staged_count,
        "End Time": f"{st.session_state.sim_start_date} — "
                    f"{(st.session_state.sim_minute // 60) % 24:02d}:{st.session_state.sim_minute % 60:02d}"
    }

    # Keep just a small set of “storytelling” events for readability
    notable = []
    for t, d in event_log:
        if t in ("Urgency", "Departure", "Missed Connection", "Train Cancelled", "Strategy"):
            notable.append((t, d))
    notable = notable[:20]  # cap

    st.session_state.example_output = {
        "summary": summary,
        "notable_events": notable,
    }


# ==================================================
# Simulation Core (Deterministic Flow Model)
# ==================================================
def step_flow(scenario_value: str, strategy_value: str):
    """
    Deterministic flow model (v2):
    arrivals → confirm → placement → staging → departure/missed at scheduled times

    Notes:
    - This is counter-based (not per-container yet).
    - Strategy hooks exist (urgency-aware boosts throughput during urgent windows).
    """
    events = []

    # ------------------------------
    # Urgency computation (real)
    # ------------------------------
    sim_minute = st.session_state.sim_minute
    mins_to_dep = minutes_to_next_departure(sim_minute)
    dep_label = next_departure_label(sim_minute)
    urgent_window = mins_to_dep <= URGENT_WINDOW_MINS

    st.session_state.mins_to_next_departure = mins_to_dep
    st.session_state.next_departure_label = dep_label
    st.session_state.urgent_window = urgent_window

    # Log urgency window transition once (on entry)
    if urgent_window and not st.session_state.prev_urgent_window:
        events.append(("Urgency", f"Urgency window OPEN: T–{mins_to_dep} min to {dep_label} departure"))
    st.session_state.prev_urgent_window = urgent_window

    # ------------------------------
    # Scenario tuning (simple)
    # ------------------------------
    if scenario_value == "Port Surge":
        arrivals_per_step = 5
    else:
        arrivals_per_step = 3

    if scenario_value == "Crane Down":
        # Reduced placement/staging throughput due to crane outage
        confirms_per_step = 2
        placements_per_step = 1
        stage_per_step = 1
    else:
        confirms_per_step = 2
        placements_per_step = 2
        stage_per_step = 2

    # ------------------------------
    # Strategy hook (real effect)
    # ------------------------------
    if strategy_value == "Urgency-Aware (Planned)" and urgent_window:
        placements_per_step += 1
        stage_per_step += 1
        events.append(("Strategy", "Urgency-Aware boost applied (+1 placement, +1 staging)"))

    # ------------------------------
    # Flow steps (real)
    # ------------------------------
    st.session_state.arrival_buffer_count += arrivals_per_step
    events.append(("Arrival", f"+{arrivals_per_step} arrived → arrival buffer"))

    confirmed = min(confirms_per_step, st.session_state.arrival_buffer_count)
    st.session_state.arrival_buffer_count -= confirmed
    st.session_state.confirmed_waiting_count += confirmed
    events.append(("Arrival Confirm", f"{confirmed} confirmed (gate)"))

    placed = min(placements_per_step, st.session_state.confirmed_waiting_count)
    st.session_state.confirmed_waiting_count -= placed
    events.append(("Placement", f"{placed} approved/placed into yard stacks"))

    staged_now = min(stage_per_step, placed)
    st.session_state.staged_count += staged_now
    events.append(("Retrieval", f"{staged_now} retrieved → staging"))

    # ------------------------------
    # Departure logic (real)
    # ------------------------------
    total_minutes = st.session_state.sim_minute
    hh = (total_minutes // 60) % 24
    mm = total_minutes % 60

    departure_hours = [6, 12, 18, 23]
    is_departure_time = (mm == 0) and (hh in departure_hours)

    if is_departure_time:
        if scenario_value == "Train Cancelled":
            # Scenario behavior: train does not run; no loading occurs
            st.session_state.cancelled_departures += 1
            events.append(("Train Cancelled", f"Departure at {hh:02d}:00 cancelled — no loading"))
        else:
            demand = st.session_state.train_demand_per_departure
            capacity = st.session_state.train_capacity

            loadable = min(st.session_state.staged_count, capacity)
            st.session_state.staged_count -= loadable
            st.session_state.departed_total += loadable
            events.append(("Departure", f"{loadable} loaded/departed at {hh:02d}:00 (cap {capacity})"))

            missed = max(0, demand - loadable)
            if missed > 0:
                st.session_state.missed_total += missed
                events.append(("Missed Connection", f"{missed} missed at {hh:02d}:00 (demand {demand}, staged shortage)"))

    st.session_state.last_events = events


# ==================================================
# Page Configuration
# ==================================================
st.set_page_config(page_title="Intermodal Yard Decision Support", layout="wide")


# ==================================================
# Header
# ==================================================
st.title("Intermodal Yard Decision Support System")
st.caption("Decision-support prototype for intermodal rail yard operations")


# ==================================================
# Top Control Bar
# ==================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    scenario = st.selectbox("Scenario", ["Baseline Day", "Port Surge", "Crane Down", "Train Cancelled"])

with col2:
    strategy = st.selectbox("Strategy", ["Baseline (Shortest Stack)", "Urgency-Aware (Planned)", "Lookahead (Planned)"])

with col3:
    # Display simulation clock anchored to real date/time at reset
    total_minutes = st.session_state.sim_minute
    hours = (total_minutes // 60) % 24
    minutes = total_minutes % 60
    seconds = st.session_state.sim_second_offset
    sim_date = st.session_state.sim_start_date

    st.metric("Simulation Time", f"{sim_date} — {hours:02d}:{minutes:02d}:{seconds:02d}")

with col4:
    st.markdown("### 🧪 Simulation Controls")
    st.caption("Simulation & demo controls (not part of production UI).")

    # -------- Row 1: Core controls --------
    r1c1, r1c2, r1c3 = st.columns(3)

    with r1c1:
        if st.button("Reset"):
            init_state()
            st.rerun()

    with r1c2:
        if st.button("Step (5 min)"):
            st.session_state.sim_minute += TIME_STEP_MINUTES
            step_flow(scenario, strategy)
            st.rerun()

    with r1c3:
        if st.button("Run (1 hour)"):
            for _ in range(RUN_STEPS_PER_CLICK):
                st.session_state.sim_minute += TIME_STEP_MINUTES
                step_flow(scenario, strategy)
            st.rerun()

    st.divider()

    # -------- Row 2: Example simulations (baseline / surge) --------
    r2c1, r2c2, r2c3 = st.columns(3)

    with r2c1:
        if st.button("Ex 1: Baseline → Baseline"):
            run_sim_example("Baseline → Baseline", "Baseline Day", "Baseline (Shortest Stack)", hours=8)
            st.rerun()

    with r2c2:
        if st.button("Ex 2: Baseline → Urgency"):
            run_sim_example("Baseline → Urgency-Aware", "Baseline Day", "Urgency-Aware (Planned)", hours=8)
            st.rerun()

    with r2c3:
        if st.button("Ex 3: Port Surge → Baseline"):
            run_sim_example("Port Surge → Baseline", "Port Surge", "Baseline (Shortest Stack)", hours=8)
            st.rerun()

    # -------- Row 3: Example simulations (surge / disruptions) --------
    r3c1, r3c2, r3c3 = st.columns(3)

    with r3c1:
        if st.button("Ex 4: Port Surge → Urgency"):
            run_sim_example("Port Surge → Urgency-Aware", "Port Surge", "Urgency-Aware (Planned)", hours=8)
            st.rerun()

    with r3c2:
        if st.button("Ex 5: Crane Down"):
            run_sim_example("Crane Down → Baseline", "Crane Down", "Baseline (Shortest Stack)", hours=8)
            st.rerun()

    with r3c3:
        if st.button("Ex 6: Train Cancelled"):
            run_sim_example("Train Cancelled → Baseline", "Train Cancelled", "Baseline (Shortest Stack)", hours=8)
            st.rerun()


# ==================================================
# Example Output Display (appears after you click Ex 1–Ex 6)
# ==================================================
if st.session_state.get("example_output"):
    out = st.session_state.example_output
    st.subheader("📊 Example Output Summary")
    st.dataframe(pd.DataFrame([out["summary"]]), use_container_width=True, hide_index=True)

    with st.expander("Show notable events (sample)"):
        if out["notable_events"]:
            st.dataframe(
                pd.DataFrame(out["notable_events"], columns=["Type", "Detail"]),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No notable events captured in this window.")


st.divider()


# ==================================================
# KPI Row (Mostly Mock, except Missed Connections)
# ==================================================
# These KPIs are UI scaffolding right now (except Missed Connections).
random.seed(st.session_state.seed + st.session_state.sim_minute)

rehandles_per = round(0.8 + random.random() * 2.2, 2)  # MOCK
util = f"{random.randint(35, 95)}%"                     # MOCK
ontime = f"{random.randint(70, 99)}%"                   # MOCK
dwell = round(0.5 + random.random() * 10, 1)            # MOCK
missed = st.session_state.missed_total                  # REAL
recovery = "—" if scenario == "Baseline Day" else f"{random.randint(30, 240)} min"  # MOCK

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Rehandles / Container (mock)", rehandles_per)
k2.metric("Yard Utilization (mock)", util)
k3.metric("On-Time % (mock)", ontime)
k4.metric("Avg Dwell (hrs) (mock)", dwell)
k5.metric("Missed Connections (real)", missed)
k6.metric("Recovery Time (mock)", recovery)

st.divider()


# ==================================================
# Main Panels (Left: Yard View, Right: Queues)
# ==================================================
left, right = st.columns([3, 2])

with left:
    st.subheader("Yard View (v1 — Mock Visualization)")

    # Mock yard data for UI scaffolding (not connected to flow counters yet)
    random.seed(st.session_state.seed + st.session_state.sim_minute)
    stack_heights = [random.randint(0, 5) for _ in range(120)]

    yard_df = pd.DataFrame({"Stack": list(range(1, 121)), "Height": stack_heights})
    st.bar_chart(yard_df.set_index("Stack")["Height"])
    st.caption("Mock yard stacks. Later versions will reflect real placement & stack heights.")

    st.divider()
    st.subheader("Stack Inspector (mock)")

    selected_stack = st.selectbox("Select stack", options=list(range(1, 121)), index=0)
    height = stack_heights[selected_stack - 1]

    containers = [f"C{selected_stack:03d}-{i:02d}" for i in range(height, 0, -1)]  # top→bottom
    st.write(f"**Stack {selected_stack:03d}**  |  **Height:** {height} / 5")

    if height == 0:
        st.info("This stack is empty.")
    else:
        inspector_df = pd.DataFrame({
            "Position (Top→Bottom)": list(range(1, height + 1)),
            "Container ID (mock)": containers,
            "Assigned Train (mock)": [random.choice(["06:00", "12:00", "18:00", "23:00"]) for _ in range(height)],
            "Urgent? (mock)": [random.choice(["No", "No", "Yes"]) for _ in range(height)]
        })
        st.dataframe(inspector_df, use_container_width=True, hide_index=True)

with right:
    st.subheader("Human Checkpoints (v1 — Real Counters + Mock IDs)")

    # Real counters → Mock IDs (for display only)
    arrival_buffer = [f"A-{i:04d}" for i in range(st.session_state.arrival_buffer_count)]
    confirmed_waiting = [f"P-{i:04d}" for i in range(st.session_state.confirmed_waiting_count)]
    staged = [f"S-{i:04d}" for i in range(st.session_state.staged_count)]
    departed_count = st.session_state.departed_total

    # v1 proxy: treat all staged inventory as "at risk" during the urgency window
    urgent_backlog = len(staged) if st.session_state.urgent_window else 0

    c1, c2 = st.columns(2)
    c1.metric("Arrival Buffer (Unconfirmed)", len(arrival_buffer))
    c2.metric("Confirmed Waiting Placement", len(confirmed_waiting))

    c3, c4 = st.columns(2)
    c3.metric("Staged (Ready to Load)", len(staged))
    c4.metric("Loaded / Departed", departed_count)

    c5, c6 = st.columns(2)
    c5.metric(
        "Urgent Backlog",
        urgent_backlog,
        help="Staged containers at risk for the next scheduled departure (proxy for v1)."
    )
    c6.metric(
        "Cancelled Departures",
        st.session_state.cancelled_departures,
        help="Scheduled trains that did not run (Train Cancelled scenario)."
    )

    st.caption(
        f"Next departure: {st.session_state.next_departure_label} "
        f"(T–{st.session_state.mins_to_next_departure} min)"
    )

    st.divider()

    tabs = st.tabs(["Arrival Buffer", "Waiting Placement", "Staged"])
    with tabs[0]:
        st.dataframe({"Container (mock)": arrival_buffer}, use_container_width=True, hide_index=True)
    with tabs[1]:
        st.dataframe({"Container (mock)": confirmed_waiting}, use_container_width=True, hide_index=True)
    with tabs[2]:
        st.dataframe({"Container (mock)": staged}, use_container_width=True, hide_index=True)

    st.caption("Queue lists use mock IDs; counts are real. Later versions will use real container lifecycle objects.")


# ==================================================
# Operations Timeline / Event Feed (Real)
# ==================================================
st.subheader("Operations Timeline (v1 — Event Feed)")

total_minutes = st.session_state.sim_minute
hours = (total_minutes // 60) % 24
minutes = total_minutes % 60
current_time = (
    f"{st.session_state.sim_start_date} — "
    f"{hours:02d}:{minutes:02d}:{st.session_state.sim_second_offset:02d}"
)

events = [{"Time": current_time, "Type": t, "Detail": d} for (t, d) in st.session_state.last_events]
st.dataframe(events, use_container_width=True, hide_index=True)

st.caption("Event feed shows the operations generated during the most recent simulation step.")

