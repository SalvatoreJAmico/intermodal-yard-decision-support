import streamlit as st
import pandas as pd
import random

# --------------------------------------------------
# App state initialization
# --------------------------------------------------

TIME_STEP_MINUTES = 5

def init_state():
    st.session_state.sim_minute = 0
    st.session_state.run_id = 1
    st.session_state.seed = 7  # controls reproducible mock behavior

if "sim_minute" not in st.session_state:
    init_state()


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
    st.metric("Simulation Time", f"Day 1 — {hours:02d}:{minutes:02d}")


with col4:
    st.write("Controls")

    if st.button("Reset"):
        init_state()
        st.rerun()

    if st.button("Step"):
        st.session_state.sim_minute += TIME_STEP_MINUTES
        st.rerun()

    if st.button("Run"):
        st.session_state.sim_minute += TIME_STEP_MINUTES
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
missed = random.randint(0, 45)
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

    random.seed(21 + st.session_state.sim_minute)


    # Mock queues: list of container IDs waiting at each checkpoint
    arrival_buffer = [f"A-{i:04d}" for i in range(random.randint(5, 25))]
    confirmed_waiting = [f"P-{i:04d}" for i in range(random.randint(3, 18))]
    staged = [f"S-{i:04d}" for i in range(random.randint(10, 40))]
    departed_count = random.randint(50, 250)

    c1, c2 = st.columns(2)
    c1.metric("Arrival Buffer (Unconfirmed)", len(arrival_buffer))
    c2.metric("Confirmed Waiting Placement", len(confirmed_waiting))

    c3, c4 = st.columns(2)
    c3.metric("Staged (Ready to Load)", len(staged))
    c4.metric("Loaded / Departed", departed_count)

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
    {"Time": current_time, "Type": "Arrival", "Detail": "12 containers arrived → arrival buffer"},
    {"Time": current_time, "Type": "Arrival Confirm", "Detail": "8 containers confirmed (gate)"},
    {"Time": current_time, "Type": "Placement", "Detail": "8 containers placed into yard stacks"},
    {"Time": current_time, "Type": "Urgency Update", "Detail": "3 containers became urgent (<= 2h to departure)"},
    {"Time": current_time, "Type": "Retrieval", "Detail": "2 containers retrieved → staging"},
    {"Time": current_time, "Type": "Rehandle", "Detail": "4 rehandles occurred while unblocking urgent containers"},
]

st.dataframe(events, use_container_width=True, hide_index=True)

st.caption("Mock event feed. This will later be generated directly from the simulation event log.")
