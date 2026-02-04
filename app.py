import streamlit as st
import pandas as pd
import random
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
    st.metric("Simulation Time", "Day 1 — 00:00")

with col4:
    st.write("Controls")
    st.button("Run")
    st.button("Step")
    st.button("Reset")

st.divider()

# --------------------------------------------------
# KPI Row (placeholders)
# --------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Rehandles / Container", "—")
k2.metric("Yard Utilization", "—")
k3.metric("On-Time %", "—")
k4.metric("Avg Dwell (hrs)", "—")
k5.metric("Missed Connections", "—")
k6.metric("Recovery Time", "—")

st.divider()

# --------------------------------------------------
# Main panels
# --------------------------------------------------
left, right = st.columns([3, 2])

with left:
    st.subheader("Yard View (v1)")

    # --- mock yard data (temporary) ---
    random.seed(7)
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
    st.subheader("Human Checkpoints (v1)")

    # --- mock checkpoint data (temporary) ---
    arrival_buffer = random.randint(0, 50)
    confirmed_waiting = random.randint(0, 30)
    staged = random.randint(0, 80)
    departed = random.randint(0, 200)

    c1, c2 = st.columns(2)
    c1.metric("Arrival Buffer (Unconfirmed)", arrival_buffer)
    c2.metric("Confirmed Waiting Placement", confirmed_waiting)

    c3, c4 = st.columns(2)
    c3.metric("Staged (Ready to Load)", staged)
    c4.metric("Loaded / Departed", departed)

    st.caption("Mock checkpoint counts. These will be wired to container states later.")


st.divider()

# --------------------------------------------------
# Timeline / Events
# --------------------------------------------------
st.subheader("Operations Timeline")
st.info("Arrival, retrieval, staging, and departure events will appear here.")
