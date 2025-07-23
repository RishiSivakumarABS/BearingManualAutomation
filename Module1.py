import streamlit as st
import pandas as pd
import numpy as np

# Load data
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")
ira_df = pd.read_excel("Cylindrical Roller Bearings.xlsx")

ira_df.columns = ira_df.columns.str.lower().str.strip().str.replace(" ", "_")

def interpolate_ira_F(d, D, ira_df):
    # Try exact match
    exact = ira_df[(ira_df['inner_diameter'] == d) & (ira_df['outer_diameter'] == D)]
    if not exact.empty:
        return exact.iloc[0]['F'], "Exact Match"

    # Try 1D interpolation over D at nearest d
    d_unique = np.sort(ira_df['inner_diameter'].unique())
    d_below = d_unique[d_unique <= d]
    d_above = d_unique[d_unique > d]

    if len(d_below) > 0 and len(d_above) > 0:
        d1 = d_below[-1]
        d2 = d_above[0]
        subset1 = ira_df[ira_df['inner_diameter'] == d1].sort_values('outer_diameter')
        subset2 = ira_df[ira_df['inner_diameter'] == d2].sort_values('outer_diameter')

        if not subset1.empty and not subset2.empty:
            f1 = np.interp(D, subset1['outer_diameter'], subset1['F'])
            f2 = np.interp(D, subset2['outer_diameter'], subset2['F'])
            # Linear interpolation over d
            F_interp = f1 + ((d - d1) / (d2 - d1)) * (f2 - f1)
            return F_interp, "Interpolated from (d1, d2) and (D1, D2)"

    # Try 1D fallback: only same d
    same_d_rows = ira_df[np.isclose(ira_df['inner_diameter'], d, atol=2)]
    if not same_d_rows.empty:
        same_d_rows = same_d_rows.sort_values('outer_diameter')
        F_interp = np.interp(D, same_d_rows['outer_diameter'], same_d_rows['F'])
        return F_interp, "Interpolated over D"

    # Fallback to closest
    closest = ira_df.loc[((ira_df['inner_diameter'] - d).abs() + (ira_df['outer_diameter'] - D).abs()).idxmin()]
    return closest['F'], "Closest Match"

# Clean up IRA table column types
ira_df['inner_diameter'] = pd.to_numeric(ira_df['inner_diameter'], errors='coerce')
ira_df['outer_diameter'] = pd.to_numeric(ira_df['outer_diameter'], errors='coerce')
ira_df['f'] = pd.to_numeric(ira_df['f'], errors='coerce')
ira_df.dropna(subset=['inner_diameter', 'outer_diameter', 'f'], inplace=True)

# Normalize roller table columns
roller_df.columns = [col.strip().lower().replace(" ", "_") for col in roller_df.columns]

# Streamlit setup
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

# Session
if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

# Input section
with st.container():
    st.subheader("📐 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        d = st.number_input("🔩 Inner Diameter (d) [mm]", min_value=50.0, max_value=1000.0, value=180.0)
        B = st.number_input("↔️ Available Width (B) [mm]", min_value=10.0, max_value=500.0, value=160.0)
    with col2:
        D_default = max(250.0, d + 10)
        D = st.number_input("🏠 Outer Diameter (D) [mm]", min_value=d + 10, max_value=1200.0, value=D_default)

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

# Proceed button
if st.button("✅ Proceed to Design Calculations"):
    st.session_state["proceed_clicked"] = True

# Main logic
if st.session_state["proceed_clicked"]:
    st.success("Inputs captured successfully!")
    st.write("### 📋 Input Summary")
    st.json({"d": d, "D": D, "B": B, "Fr": Fr, "Fa": Fa, "RPM": RPM, "Temp": temperature})

    # Pitch diameter
    pitch_dia = (d + D) / 2
    st.markdown(f"### 🎯 Pitch Diameter = `{pitch_dia:.2f} mm`")

    # Match closest IRa (F) using d & D only
    # Find F using interpolation logic
    F, match_type = interpolate_ira_F(d, D, ira_df)
    st.write(f"- {match_type} IRa (F): `{F:.2f} mm`")

    ira_half = F / 2
    roller_max_possible = 2 * ((pitch_dia / 2) - ira_half)
    st.write(f"- Closest IRa (F): `{F:.2f} mm`")
    st.write(f"- Max Roller Diameter Allowed: `{roller_max_possible:.2f} mm`")

    # Suggest roller(s)
    roller_df_filtered = roller_df[(roller_df['dw'] <= roller_max_possible) & (roller_df['lw'] <= B)]

    if roller_df_filtered.empty:
        st.error("❌ No rollers available below max roller diameter and width.")
    else:
        # Sort by largest dw for max capacity
        roller_df_filtered = roller_df_filtered.sort_values(by=['dw'], ascending=False)
        top_dw = roller_df_filtered['dw'].iloc[0]
        top_rollers = roller_df_filtered[roller_df_filtered['dw'] == top_dw]

        st.success("✅ Recommended Rollers (Closest to Max Diameter)")
        st.dataframe(top_rollers[['dw', 'lw', 'r_min', 'r_max', 'mass_per_100']])

        selected_dw = top_rollers.iloc[0]['dw']
        selected_lw = top_rollers.iloc[0]['lw']
        r_min = top_rollers.iloc[0]['r_min']
        r_max = top_rollers.iloc[0]['r_max']
        selected_mass = top_rollers.iloc[0]['mass_per_100']
        space_bw_rollers = roller_max_possible - selected_dw

        st.info(f"Selected: Dw = {selected_dw}, Lw = {selected_lw}, Space b/w rollers = {space_bw_rollers:.2f} mm")

        # Z calculation
        try:
            Z = int(np.pi / np.arcsin(selected_dw / pitch_dia))
            st.write(f"- Number of rollers (Z): `{Z}`")
        except ValueError:
            st.error("❌ Invalid configuration: asin out of domain. Adjust Dw or Dpw.")
            Z = 0

        # Number of rows input
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
