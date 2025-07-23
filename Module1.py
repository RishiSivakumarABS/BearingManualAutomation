import streamlit as st
import pandas as pd
import numpy as np

# Load data
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")
ira_df = pd.read_excel("Cylindrical Roller Bearings.xlsx")

# Normalize column names
ira_df.columns = ira_df.columns.str.strip().str.lower().str.replace(" ", "_")
roller_df.columns = roller_df.columns.str.strip().str.lower().str.replace(" ", "_")

# Convert columns to numeric
ira_df['inner_diameter'] = pd.to_numeric(ira_df['inner_diameter'], errors='coerce')
ira_df['outer_diameter'] = pd.to_numeric(ira_df['outer_diameter'], errors='coerce')
ira_df['f'] = pd.to_numeric(ira_df['f'], errors='coerce')
ira_df.dropna(subset=['inner_diameter', 'outer_diameter', 'f'], inplace=True)

# Streamlit setup
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

# Session state
if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

# Input Section
with st.container():
    st.subheader("📜 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        d = st.number_input("🔩 Inner Diameter (d) [mm]", min_value=50.0, max_value=1000.0, value=280.0)
        B = st.number_input(" Available Width (B) [mm]", min_value=10.0, max_value=500.0, value=220.0)
    with col2:
        D = st.number_input("🏠 Outer Diameter (D) [mm]", min_value=d + 10, max_value=1200.0, value=390.0)

st.markdown("---")

with st.container():
    st.subheader("⚙️ Operating Conditions")
    col3, col4 = st.columns(2)
    with col3:
        Fr = st.number_input("📏 Radial Load (Fr) [kN]", min_value=0.0, value=1980.0)
        RPM = st.number_input("⏱️ Speed (RPM)", min_value=0, value=500)
    with col4:
        Fa = st.number_input("📏 Axial Load (Fa) [kN]", min_value=0.0, value=50.0)
        temperature = st.number_input("🌡️ Operating Temperature (°C)", min_value=-50.0, max_value=250.0, value=80.0)

st.markdown("---")

if st.button("✅ Proceed to Design Calculations"):
    st.session_state["proceed_clicked"] = True

if st.session_state["proceed_clicked"]:
    st.success("Inputs captured successfully!")
    st.write("### 📋 Input Summary")
    st.json({"d": d, "D": D, "B": B, "Fr": Fr, "Fa": Fa, "RPM": RPM, "Temp": temperature})

    pitch_dia = (d + D) / 2
    st.markdown(f"### 🎯 Pitch Diameter = `{pitch_dia:.2f} mm`")

    # Interpolated F based on d and D
    lower = ira_df[(ira_df['inner_diameter'] <= d) & (ira_df['outer_diameter'] <= D)].sort_values(
        by=['inner_diameter', 'outer_diameter'], ascending=False).head(1)
    upper = ira_df[(ira_df['inner_diameter'] >= d) & (ira_df['outer_diameter'] >= D)].sort_values(
        by=['inner_diameter', 'outer_diameter'], ascending=True).head(1)

    if not lower.empty and not upper.empty:
        x0, y0, f0 = lower.iloc[0][['inner_diameter', 'outer_diameter', 'f']]
        x1, y1, f1 = upper.iloc[0][['inner_diameter', 'outer_diameter', 'f']]
        weight = ((d - x0) + (D - y0)) / ((x1 - x0) + (y1 - y0) + 1e-6)
        F = f0 + weight * (f1 - f0)
    else:
        F = ira_df.loc[((ira_df['inner_diameter'] - d).abs() + (ira_df['outer_diameter'] - D).abs()).idxmin(), 'f']

    ira_half = F / 2
    roller_max_possible = 2 * ((pitch_dia / 2) - ira_half)
    adjusted_dw_limit = roller_max_possible - 0.02 * pitch_dia

    st.write(f"- Interpolated F: `{F:.2f} mm`")
    st.write(f"- Max Roller Diameter Allowed: `{roller_max_possible:.2f} mm`")
    st.write(f"- Adjusted Dw Limit (2% pitch dia margin): `{adjusted_dw_limit:.2f} mm`")

    # Filter and select best roller
    valid_rollers = roller_df[(roller_df['dw'] <= adjusted_dw_limit) & (roller_df['lw'] <= B)]

    if valid_rollers.empty:
        st.error("❌ No valid roller found after applying 2% pitch diameter margin.")
    else:
        # Choose roller with max dw, then max lw
        top_dw = valid_rollers['dw'].max()
        best_rollers = valid_rollers[valid_rollers['dw'] == top_dw]
        selected = best_rollers.loc[best_rollers['lw'].idxmax()]

        selected_dw = selected['dw']
        selected_lw = selected['lw']
        r_min = selected['r_min']
        r_max = selected['r_max']
        selected_mass = selected['mass_per_100']
        space_bw_rollers = roller_max_possible - selected_dw

        st.success("✅ Selected Roller")
        st.dataframe(pd.DataFrame([selected[['dw', 'lw', 'r_min', 'r_max', 'mass_per_100']]]))
        st.info(f"Selected: Dw = {selected_dw}, Lw = {selected_lw}, Space b/w rollers = {space_bw_rollers:.2f} mm")

        # Z calculation
        try:
            Z = int(np.pi / np.arcsin(selected_dw / pitch_dia))
            st.write(f"- Number of rollers (Z): `{Z}`")
        except ValueError:
            st.error("❌ Invalid configuration: asin out of domain. Adjust Dw or Dpw.")
            Z = 0

        # Number of rows
        i = st.number_input("🔢 Number of Roller Rows (i)", min_value=1, max_value=8, value=4)

        # Load fc table
        fc_df = pd.read_excel("ISO_Table_7_fc_values.xlsx")
        fc_df.columns = fc_df.columns.str.lower()
        fc_ratio = selected_dw / pitch_dia
        fc_ratio = np.clip(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"].min(), fc_df["dwe_cos_alpha_over_dpw"].max())
        fc = np.interp(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"], fc_df["fc"])

        # Cr and Cor
        bm = 1.1
        Cr = bm * fc * ((i * selected_lw) ** (7 / 9)) * (Z ** (3 / 4)) * (selected_dw ** (29 / 27))
        Cor = 44 * (1 - (selected_dw / pitch_dia)) * i * Z * selected_lw * selected_dw

        st.success(f"**Cr = {Cr:,.2f} N**")
        st.success(f"**Cor = {Cor:,.2f} N**")
