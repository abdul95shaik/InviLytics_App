# components/graph7.py
# --------------------
# Graph 7: Inventory Levels Over Time (Altair)
# Expects TWO items in st.session_state:
#   - state_key_df : a tidy DataFrame with columns ["Day","Series","Value"]
#   - state_key_r  : the live reorder point (float), e.g., r = d_bar*L + z*sigma*sqrt(L)
#
# In app.py (after you compute df_g7 and r), store them like:
#   st.session_state["g7_df"] = df_g7
#   st.session_state["g7_r"]  = r
# and call:
#   render_graph7_chart(title_prefix="7) ", state_key_df="g7_df", state_key_r="g7_r")

from __future__ import annotations
import pandas as pd
import altair as alt
import streamlit as st


def render_graph7_chart(
    title_prefix: str = "7",
    state_key_df: str = "g7_df",
    state_key_r: str = "g7_r",
) -> None:
    df_g7 = st.session_state.get(state_key_df)
    r_val = float(st.session_state.get(state_key_r, 0.0))


    st.markdown(f"### {title_prefix}Inventory Levels Over Time")

    # Guard rails
    if df_g7 is None or not isinstance(df_g7, pd.DataFrame) or df_g7.empty:
        st.info("Use the sidebar to set Graph 7 inputs — no data yet.")
        return
    if r_val is None:
        st.info("Reorder point not set. Make sure you stored it in session_state.")
        return

    # ---- Main lines (Backorders / Inventory Position / On-Hand) ----
    line_chart = (
        alt.Chart(df_g7)
        .mark_line()
        .encode(
            x=alt.X("Day:Q", axis=alt.Axis(title="Day")),
            y=alt.Y("Value:Q", axis=alt.Axis(title=None)),
            color=alt.Color("Series:N", legend=alt.Legend(title=None)),
            tooltip=[alt.Tooltip("Series:N"), alt.Tooltip("Day:Q"), alt.Tooltip("Value:Q")],
        )
    )

    # ---- Dynamic dashed reorder point line ----
    rule = (
    alt.Chart(pd.DataFrame({"y": [r_val]}))
    .mark_rule(strokeDash=[6, 4], color="red")
    .encode(y="y:Q")
    )

    label = (
    alt.Chart(pd.DataFrame({"y": [r_val], "x": [df_g7["Day"].min() + 5]}))
    .mark_text(align="left", dx=6, dy=-6, color="red")
    .encode(x="x:Q", y="y:Q", text=alt.value(f"Reorder Point (r={r_val:.0f})"))
    )


    chart = (line_chart + rule + label).properties(height=400)
    st.altair_chart(chart, use_container_width=True)
import streamlit as st
import pandas as pd

def render_graph7_sidebar(state_key_df: str = "g7_df") -> None:
    """Sidebar controls for Graph 7 (3 sliders per series). Writes df to session."""
    with st.sidebar.expander("Graph 7 • Manual Series (Backorders / Inv. Position / On-Hand)", expanded=False):
        # Backorders (0–50 units)
        bo1 = st.slider("Backorders pt 1", 0, 50, 0)
        bo2 = st.slider("Backorders pt 2", 0, 50, 10)
        bo3 = st.slider("Backorders pt 3", 0, 50, 0)

        # Inventory Position (0–300 units)
        ip1 = st.slider("Inventory Position pt 1", 0, 300, 140)
        ip2 = st.slider("Inventory Position pt 2", 0, 300, 80)
        ip3 = st.slider("Inventory Position pt 3", 0, 300, 150)

        # On-Hand Inventory (0–300 units)
        oh1 = st.slider("On-Hand pt 1", 0, 300, 121)
        oh2 = st.slider("On-Hand pt 2", 0, 300, 60)
        oh3 = st.slider("On-Hand pt 3", 0, 300, 140)

    days = [0, 75, 150]
    df = pd.DataFrame({
        "Day":    days * 3,
        "Series": (["Backorders"] * 3) + (["Inventory Position"] * 3) + (["On-Hand Inventory"] * 3),
        "Value":  [bo1, bo2, bo3, ip1, ip2, ip3, oh1, oh2, oh3],
    })
    st.session_state[state_key_df] = df
