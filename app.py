import streamlit as st
import pandas as pd
import random
from datetime import datetime

# --------------------------------------------------
# App state initialization
# --------------------------------------------------

TIME_STEP_MINUTES = 5
DEPARTURE_TOD_MINS = [360, 720, 1080, 1380]  # 06:00, 12:00, 18:00, 23:00
URGENT_WINDOW_MINS = 120
RUN_STEPS_PER_CLICK = 12  # 12 * 5min = 60 minutes


def init_state():

    now = datetime.now()
    st.session_state.sim_minute = now.hour * 60 + now.minute
    st.session_state.sim_second_offset = now.second
    st.session_state.sim_start_date = now.date()

    st.session_state.run_id = 1
    st.session_state.seed = 7  # controls reproducible mock behavior

    # Deterministic flow counters (v2)
    st.session_state.arrival_buffer_count = 12
    st.session_state.confirmed_waiting_count = 8
    st.session_state.staged_count = 20
    st.session_state.departed_total = 0
    st.session_state.last_events = []

    # NEW: missed connection tracking
    st.session_state.missed_total = 0

    # NEW: simple train model (edit later)
    st.session_state.train_capacity = 25          # max that can load per departure
    st.session_state.train_demand_per_departure = 28  # demand requested per departure

    # NEW: urgency tracking
    st.session_state.urgent_window = False
    st.session_state.prev_urgent_window = False
    st.session_state.mins_to_next_departure = None
    st.session_state.next_departure_label = None

    st.session_state.cancelled_departures = 0


if "sim_minute" not in st.session_state:
    init_state()


def minutes_to_next_departure(sim_minute: int) -> int:
    tod = sim_minute % 1440  # minutes since midnight
    for d in DEPARTURE_TOD_MINS:
        if d > tod:
            return d - tod
    # next day 06:00
    return (1440 - tod) + DEPARTURE_TOD_MINS[0]

def next_departure_label(sim_minute: int) -> str:
    tod = sim_minute % 1440
    for d in DEPARTURE_TOD_MINS:
        if d > tod:
            hh = d // 60
            mm = d % 60
            return f"{hh:02d}:{mm:02d}"
    return "06:00"



# --------------------------------------------------
# Deterministic flow model (v2)
# --------------------------------------------------
def step_flow(scenario_value: str, strategy_value: str):
    """
    Deterministic flow model (v2):
    arrivals -> confirm -> placement -> staging -> departure/missed at scheduled times
    """
    events = []

    # ----- Urgency computation -----
    sim_minute = st.session_state.sim_minute
    mins_to_dep = minutes_to_next_departure(sim_minute)
    dep_label = next_departure_label(sim_minute)
    urgent_window = mins_to_dep <= URGENT_WINDOW_MINS

    st.session_state.mins_to_next_departure = mins_to_dep
    st.session_state.next_departure_label = dep_label
    st.session_state.urgent_window = urgent_window

    # Log urgency window transitions (once on entry)
    if urgent_window and not st.session_state.prev_urgent_window:
        events.append(("Urgency", f"Urgency window OPEN: T–{mins_to_dep} min to {dep_label} departure"))
    st.session_state.prev_urgent_window = urgent_window


    # Scenario tuning (simple)
    if scenario_value == "Port Surge":
        arrivals_per_step = 5
    else:
        arrivals_per_step = 3

    if scenario_value == "Crane Down":
        # fewer placements/staging during crane outage scenario
        confirms_per_step = 2
        placements_per_step = 1
        stage_per_step = 1
    else:
        confirms_per_step = 2
        placements_per_step = 2
        stage_per_step = 2


    # ----- Strategy: urgency-aware throughput boost -----
    if strategy_value == "Urgency-Aware (Planned)" and urgent_window:
        placements_per_step += 1
        stage_per_step += 1
        events.append(("Strategy", "Urgency-Aware boost applied (+1 placement, +1 staging)"))


    # Arrivals
    st.session_state.arrival_buffer_count += arrivals_per_step
    events.append(("Arrival", f"+{arrivals_per_step} arrived → arrival buffer"))

    # Confirm (gate)
    confirmed = min(confirms_per_step, st.session_state.arrival_buffer_count)
    st.session_state.arrival_buffer_count -= confirmed
    st.session_state.confirmed_waiting_count += confirmed
    events.append(("Arrival Confirm", f"{confirmed} confirmed (gate)"))

    # Placement
    placed = min(placements_per_step, st.session_state.confirmed_waiting_count)
    st.session_state.confirmed_waiting_count -= placed
    events.append(("Placement", f"{placed} approved/placed into yard stacks"))

    # Staging (retrieval)
    staged_now = min(stage_per_step, placed)
    st.session_state.staged_count += staged_now
    events.append(("Retrieval", f"{staged_now} retrieved → staging"))

    # ----- Departure logic -----
    total_minutes = st.session_state.sim_minute
    hh = (total_minutes // 60) % 24
    mm = total_minutes % 60

    departure_hours = [6, 12, 18, 23]
    is_departure_time = (mm == 0) and (hh in departure_hours)

    if is_departure_time:
        if scenario_value == "Train Cancelled":
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

# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Intermodal Yard Decision Support",
    layout="wide"
)

# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("Intermodal Yard Decision Support System")
st.caption("Decision-support prototype for intermodal rail yard operations")

# --------------------------------------------------
# Top control bar
# --------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    scenario = st.selectbox(
        "Scenario",
        ["Baseline Day", "Port Surge", "Crane Down", "Train Cancelled"]
    )

with col2:
    strategy = st.selectbox(
        "Strategy",
        ["Baseline (Shortest Stack)", "Urgency-Aware (Planned)", "Lookahead (Planned)"]
    )

with col3:
    total_minutes = st.session_state.sim_minute
    hours = (total_minutes // 60) % 24
    minutes = total_minutes % 60
    seconds = st.session_state.sim_second_offset
    sim_date = st.session_state.sim_start_date

    st.metric(
        "Simulation Time",
        f"{sim_date} — {hours:02d}:{minutes:02d}:{seconds:02d}"
    )



with col4:
    st.markdown("### 🧪 Simulation Controls")
    st.caption("For testing and demonstration only. In production, the system runs continuously.")

    if st.button("Reset Simulation"):
        init_state()
        st.rerun()

    if st.button("Step (5 min)"):
        st.session_state.sim_minute += TIME_STEP_MINUTES
        step_flow(scenario, strategy)
        st.rerun()

    if st.button("Run (1 hour)"):
        for _ in range(RUN_STEPS_PER_CLICK):
            st.session_state.sim_minute += TIME_STEP_MINUTES
            step_flow(scenario, strategy)
        st.rerun()



st.divider()

# --------------------------------------------------
# KPI Row (placeholders)
# --------------------------------------------------
# Mock KPIs that evolve with time (will become real later)
random.seed(st.session_state.seed + st.session_state.sim_minute)

rehandles_per = round(0.8 + random.random() * 2.2, 2)
util = f"{random.randint(35, 95)}%"
ontime = f"{random.randint(70, 99)}%"
dwell = round(0.5 + random.random() * 10, 1)
missed = st.session_state.missed_total
recovery = "—" if scenario == "Baseline Day" else f"{random.randint(30, 240)} min"

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Rehandles / Container", rehandles_per)
k2.metric("Yard Utilization", util)
k3.metric("On-Time %", ontime)
k4.metric("Avg Dwell (hrs)", dwell)
k5.metric("Missed Connections", missed)
k6.metric("Recovery Time", recovery)

st.divider()


# --------------------------------------------------
# Main panels
# --------------------------------------------------
left, right = st.columns([3, 2])

with left:
    st.subheader("Yard View (v1)")

    # --- mock yard data (temporary) ---
    random.seed(st.session_state.seed + st.session_state.sim_minute)
    stack_heights = [random.randint(0, 5) for _ in range(120)]

    yard_df = pd.DataFrame({
        "Stack": list(range(1, 121)),
        "Height": stack_heights
    })

    st.bar_chart(yard_df.set_index("Stack")["Height"])
    st.caption("Each bar = one stack. Height = containers in stack (0–5). Mock data for UI scaffolding.")

    st.divider()
    st.subheader("Stack Inspector (mock)")

    selected_stack = st.selectbox("Select stack", options=list(range(1, 121)), index=0)
    height = stack_heights[selected_stack - 1]

    # Create a mock container list (top -> bottom)
    # Example: C000123 format
    containers = [f"C{selected_stack:03d}-{i:02d}" for i in range(height, 0, -1)]  # top to bottom

    # Show details
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
    st.subheader("Human Checkpoints (v1 – Queues)")

    

    # real flow model.
    arrival_buffer = [f"A-{i:04d}" for i in range(st.session_state.arrival_buffer_count)]
    confirmed_waiting = [f"P-{i:04d}" for i in range(st.session_state.confirmed_waiting_count)]
    staged = [f"S-{i:04d}" for i in range(st.session_state.staged_count)]
    departed_count = st.session_state.departed_total
    
    urgent_backlog = (
    len(staged)
    if st.session_state.urgent_window
    else 0
)





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
        help="Staged containers at risk for the next scheduled departure"
    )

    c6.metric(
        "Cancelled Departures",
        st.session_state.cancelled_departures,
        help="Scheduled trains that did not run"
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

    st.caption("Mock queue lists. These will be driven by container lifecycle states later.")

# --------------------------------------------------
# Timeline / Events
# --------------------------------------------------
st.subheader("Operations Timeline (v1 – Event Feed)")

random.seed(99 + st.session_state.sim_minute)
total_minutes = st.session_state.sim_minute
hours = (total_minutes // 60) % 24
minutes = total_minutes % 60
current_time = f"Day 1 — {hours:02d}:{minutes:02d}"

events = [
    {"Time": current_time, "Type": t, "Detail": d}
    for (t, d) in st.session_state.last_events
]

st.dataframe(events, use_container_width=True, hide_index=True)

st.caption(
    "Event feed shows the operations generated during the most recent simulation step."
)