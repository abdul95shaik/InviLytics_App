# app.py
import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
from scipy.stats import norm

from components.graph7 import render_graph7_sidebar, render_graph7_chart

st.set_page_config(page_title="InviLytics — Pro UI (Q, r)", layout="wide")

# --- Brand header ---
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
        <div style="width:10px;height:10px;border-radius:50%;background:#8AB4F8;"></div>
        <div style="font-size:28px;font-weight:700;">InviLytics</div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Inputs")
    D = st.number_input("Annual demand D (units/yr)", value=2000.0, min_value=0.0, step=10.0, format="%.2f")
    K = st.number_input("Order cost K ($/order)", value=100.0, min_value=0.0, step=5.0, format="%.2f")
    h = st.number_input("Holding cost h ($/unit/yr)", value=2.0, min_value=0.0, step=0.1, format="%.2f")
    days_per_year = st.number_input("Days per year", value=365, min_value=1, max_value=400, step=1)
    L = st.slider("Lead time (days)", min_value=1, max_value=90, value=5)
    dbar = st.number_input("Avg daily demand (units)", value=26.50, min_value=0.0, step=0.1, format="%.2f")
    sigma_d = st.number_input("Std dev daily demand (units)", value=5.50, min_value=0.0, step=0.1, format="%.2f")
    # Service level in percent → internally converted to z
    z_pct = st.slider("Service level (%)", min_value=50.0, max_value=99.9, value=95.0, step=0.1)
    z = float(norm.ppf(z_pct / 100.0))  # convert % → z-score

    st.markdown("---")
    override = st.checkbox("Override EOQ with manual Q", value=False)
    Q_manual = st.number_input("Manual Q (if override)", value=500.0, min_value=1.0, step=1.0, format="%.0f")
    st.markdown("---")
    budget = st.number_input("Annual inventory budget ($)", value=20000.0, min_value=0.0, step=100.0, format="%.2f")

# Default variation in session (for KPI math) — slider is shown later above Q curve
if "variation" not in st.session_state:
    st.session_state["variation"] = 35

# --- Core calculations ---
EOQ = (0 if h == 0 else (2*D*K/h)**0.5)
r = dbar * L + z * (sigma_d * (L**0.5))
st.session_state["g7_r"] = r
if not override:
    Q = max(1.0, EOQ * (1 + st.session_state["variation"]/100.0))
else:
    Q = Q_manual

ordering_cost = (D / Q) * K if Q > 0 else 0.0
holding_cost = (Q / 2.0) * h
annual_cost = ordering_cost + holding_cost
budget_delta = budget - annual_cost
try:
    _ = sigma_L
except NameError:
    sigma_L = sigma_d * (L ** 0.5)   # sigmad and L are already defined earlier

phi_z = norm.pdf(z)
Phi_z = norm.cdf(z)
Lz = phi_z - z * (1.0 - Phi_z)    # loss function term
ESC = sigma_L * Lz               # expected shortage per cycle (units)

cycles_per_year = max(1.0, D / max(Q, 1e-9))  # guard against tiny Q
annual_stockout_units = cycles_per_year * ESC
# ---- /Total Stockout block ----
# --- KPI Row ---
k1, k2, k3, k4, k5 = st.columns([1,1,1,1,1])
k1.metric("EOQ (Q*)", f"{EOQ:,.0f}")
k2.metric("Reorder point r", f"{r:,.0f}")
k3.metric("Annual cost", f"${annual_cost:,.0f}")
k4.metric("Budget Δ", f"+{budget_delta:,.0f}" if budget_delta >= 0 else f"{budget_delta:,.0f}")
k5.metric("Total Stockout (units/yr)", f"{annual_stockout_units:,.0f}")

# --- TWO MINI KPI TILES (no label) ---
hc_col, oc_col = st.columns(2)
hc_col.metric("Holding Cost", f"${holding_cost:,.0f}")
oc_col.metric("Ordering Cost", f"${ordering_cost:,.0f}")

# --- Row 1 Charts ---
colA, colB = st.columns(2)
with colA:
    st.markdown("**1) Budget vs. Inventory Cost**")
    df = pd.DataFrame({"Category":["Budget (After)","Inventory Cost"],"$ / year":[budget, annual_cost]})
    st.altair_chart(alt.Chart(df).mark_bar().encode(x=alt.X("Category:N", sort=None), y=alt.Y("$ / year:Q")), use_container_width=True)

with colB:
    st.markdown("**2) Cost components ($/yr)**")
    df2 = pd.DataFrame({"Component":["Holding","Ordering"], "$ / year":[holding_cost, ordering_cost]})
    st.altair_chart(alt.Chart(df2).mark_bar().encode(x=alt.X("Component:N", sort=None), y=alt.Y("$ / year:Q")), use_container_width=True)

# --- Row 2 Charts ---
colC, colD = st.columns(2)
with colC:
    st.markdown("**3) Remaining Budget & Simple Runway**")
    remaining = max(budget - annual_cost, 0.0)
    monthly_burn = max(annual_cost/12.0, 1e-6)
    runway_months = remaining / monthly_burn
    df3 = pd.DataFrame({"Metric":["Remaining ($)","Runway (months)"],"Value":[remaining, runway_months]})
    st.altair_chart(alt.Chart(df3).mark_bar().encode(x=alt.X("Metric:N", sort=None), y=alt.Y("Value:Q")), use_container_width=True)

with colD:
    st.markdown("**4) What-if: Total Cost vs Q**")
    # Q variation slider placed contextually above this curve
    st.session_state["variation"] = st.slider("Q variation around EOQ (%)", min_value=0, max_value=80, value=st.session_state["variation"])
    # Recompute when slider moves
    if not override:
        Q = max(1.0, EOQ * (1 + st.session_state["variation"]/100.0))
        ordering_cost = (D / Q) * K if Q > 0 else 0.0
        holding_cost = (Q / 2.0) * h
        annual_cost = ordering_cost + holding_cost
        budget_delta = budget - annual_cost
    q_vals = np.linspace(max(1.0, EOQ*0.3), EOQ*1.7 if EOQ>0 else 1000.0, 60)
    tot = (D/q_vals)*K + (q_vals/2.0)*h
    df4 = pd.DataFrame({"Q": q_vals, "Total Cost": tot})
    st.altair_chart(alt.Chart(df4).mark_line().encode(x="Q:Q", y="Total Cost:Q"), use_container_width=True)

# --- Row 3 Charts ---
colE, colF = st.columns(2)
with colE:
    st.markdown("**5) Inventory Efficiency**")
    efficiency_score = max(0.0, 100.0 - (abs(Q-EOQ)/max(EOQ,1e-6))*100.0)
    turns = (D/Q) if Q>0 else 0.0
    df5 = pd.DataFrame({"Metric":["EOQ","Efficiency score","Turns (D/Q)"],"Value":[EOQ, efficiency_score, turns]})
    st.altair_chart(alt.Chart(df5).mark_bar().encode(x=alt.X("Metric:N", sort=None), y=alt.Y("Value:Q")), use_container_width=True)

with colF:
    st.markdown("**6) Inventory Posture**")
    df6 = pd.DataFrame({"Posture":["Holding","Ordering"],"$ / year":[holding_cost, ordering_cost]})
    st.altair_chart(alt.Chart(df6).mark_bar().encode(x=alt.X("Posture:N", sort=None), y=alt.Y("$ / year:Q")), use_container_width=True)

st.markdown("---")

# --- 7) New chart ---
# render_graph7_sidebar()
# NEW
# --- 7) New chart ---
# --- 7) New chart ---

# put the live, calculated reorder point into session
st.session_state["g7_r"] = r   # r = dbar*L + z*sigma_d*sqrt(L) computed above

# (optional) sidebar sliders for Graph 7 -> writes df to st.session_state["g7_df"]
render_graph7_sidebar(state_key_df="g7_df")

# draw chart; chart will read r from session
render_graph7_chart(title_prefix="7", state_key_df="g7_df", state_key_r="g7_r")




