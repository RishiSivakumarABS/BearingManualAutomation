import streamlit as st
import pandas as pd
import numpy as np

# Load data
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")
ira_df = pd.read_excel("Cylindrical Roller Bearings.xlsx")

# Rename IRA columns explicitly
ira_df.rename(columns={
    'd': 'd_inner',
    'd.1': 'D_outer',
    'b': 'B_width',
    'f': 'F_ira'
}, inplace=True)

# Convert to numeric and drop any rows with missing values
ira_df['d_inner'] = pd.to_numeric(ira_df['d_inner'], errors='coerce')
ira_df['D_outer'] = pd.to_numeric(ira_df['D_outer'], errors='coerce')
ira_df['B_width'] = pd.to_numeric(ira_df['B_width'], errors='coerce')
ira_df['F_ira'] = pd.to_numeric(ira_df['F_ira'], errors='coerce')
ira_df.dropna(subset=['d_inner', 'D_outer', 'B_width', 'F_ira'], inplace=True)

# Normalize roller table column names
roller_df.columns = [col.strip().lower().replace(" ", "_") for col in roller_df.columns]

# Streamlit config
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

# Session
if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

# Section 1: Inputs
with st.container():
    st.subheader("📐 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        d = st.number_input("🔩 Inner Diameter (d) [mm]", min_value=50.0, max_value=1000.0, value=180.0)
        B = st.number_input("↔️ Available Width (B) [mm]", min_value=10.0, max_value=500.0, value=160.0)
    with col2:
        D = st.number_input("🏠 Outer Diameter (D) [mm]", min_value=d + 10, max_value=1200.0, value=250.0)

st.markdown("---")

with st.container():
    st.subheader("⚙️ Operating Conditions")
    col3, col4 = st.columns(2)
    with col3:
        Fr = st.number_input("📏 Radial Load (Fr) [kN]", min_value=0.0, value=400.0)
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

    # Pitch diameter
    pitch_dia = (d + D) / 2
    st.markdown(f"### 🎯 Pitch Diameter = `{pitch_dia:.2f} mm`")

    # Find closest IRa (F)
    ira_match = ira_df.loc[
        ((ira_df['d_inner'] - d).abs() + (ira_df['D_outer'] - D).abs() + (ira_df['B_width'] - B).abs()).idxmin()
    ]
    F = ira_match['F_ira']
    ira_half = F / 2
    roller_max_possible = 2 * ((pitch_dia / 2) - ira_half)
    st.write(f"- Closest IRa (F): `{F:.2f} mm`")
    st.write(f"- Max Roller Diameter Allowed: `{roller_max_possible:.2f} mm`")

    # Suggest roller(s) from SKF table
    roller_df_filtered = roller_df[(roller_df['dw'] <= roller_max_possible) & (roller_df['lw'] <= B)]

    if roller_df_filtered.empty:
        st.error("❌ No rollers available below max roller diameter and width.")
    else:
        roller_df_filtered['diff'] = abs(roller_df_filtered['dw'] - roller_max_possible)
        best_dw = roller_df_filtered.sort_values(['diff', 'lw']).groupby('dw').first().reset_index()
        st.success("✅ Recommended Rollers")
        st.dataframe(best_dw[['dw', 'lw', 'r_min', 'r_max', 'mass_per_100']])

        # Select preferred
        selected_dw = best_dw.iloc[0]['dw']
        selected_lw = best_dw.iloc[0]['lw']
        r_min = best_dw.iloc[0]['r_min']
        r_max = best_dw.iloc[0]['r_max']
        selected_mass = best_dw.iloc[0]['mass_per_100']
        space_bw_rollers = roller_max_possible - selected_dw

        st.info(f"Selected: Dw = {selected_dw}, Lw = {selected_lw}, Space b/w rollers = {space_bw_rollers:.2f} mm")

        # Z Calculation
        try:
            Z = int(np.pi / np.arcsin(selected_dw / pitch_dia))
            st.write(f"- Number of rollers (Z): `{Z}`")
        except ValueError:
            st.error("❌ Invalid configuration: asin out of domain. Adjust Dw or Dpw.")
            Z = 0

        # Input: number of rows (i)
        i = st.number_input("🔢 Number of Roller Rows (i)", min_value=1, max_value=8, value=4)

        # Load fc table
        fc_df = pd.read_excel("ISO_Table_7_fc_values.xlsx")
        fc_df.columns = fc_df.columns.str.lower()

        # Interpolate fc
        fc_ratio = selected_dw / pitch_dia
        fc_ratio = np.clip(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"].min(), fc_df["dwe_cos_alpha_over_dpw"].max())
        fc = np.interp(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"], fc_df["fc"])

        # Cr Calculation
        bm = 1.1
        Cr = bm * fc * ((i * selected_lw) ** (7 / 9)) * (Z ** (3 / 4)) * (selected_dw ** (29 / 27))
        st.success(f"**Cr = {Cr:,.2f} N**")

        # Cor Calculation
        Cor = 44 * (1 - (selected_dw / pitch_dia)) * i * Z * selected_lw * selected_dw
        st.success(f"**Cor = {Cor:,.2f} N**")
