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
ira_df['outer_diameter']  = pd.to_numeric(ira_df['outer_diameter'], errors='coerce')
ira_df['f'] = pd.to_numeric(ira_df['f'], errors='coerce')
ira_df.dropna(subset=['inner_diameter', 'outer_diameter', 'f'], inplace=True)

# Streamlit setup
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

# Inputs
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
        Fr  = st.number_input("📏 Radial Load (Fr) [kN]", min_value=0.0, value=1980.0)
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

    # ---------- Interpolate F from table ----------
    lower = ira_df[(ira_df['inner_diameter'] <= d) & (ira_df['outer_diameter'] <= D)].sort_values(
        by=['inner_diameter', 'outer_diameter'], ascending=False).head(1)
    upper = ira_df[(ira_df['inner_diameter'] >= d) & (ira_df['outer_diameter'] >= D)].sort_values(
        by=['inner_diameter', 'outer_diameter'], ascending=True).head(1)

    if not lower.empty and not upper.empty:
        x0, y0, f0 = lower.iloc[0][['inner_diameter', 'outer_diameter', 'f']]
        x1, y1, f1 = upper.iloc[0][['inner_diameter', 'outer_diameter', 'f']]
        weight = ((d - x0) + (D - y0)) / ((x1 - x0) + (y1 - y0) + 1e-6)
        F_interpolated = float(f0 + weight * (f1 - f0))
    else:
        F_interpolated = float(ira_df.loc[
            ((ira_df['inner_diameter'] - d).abs() + (ira_df['outer_diameter'] - D).abs()).idxmin(), 'f'
        ])

    # ---------- Manual override control for F ----------
    st.write(f"- Interpolated F: `{F_interpolated:.2f} mm`")
    use_override = st.checkbox("Override F manually")
    if use_override:
        F_used = st.number_input(
            "Enter F [mm]", min_value=0.0, value=round(F_interpolated, 2), step=0.01,
            help="Override the interpolated F. All downstream calculations will use this value."
        )
    else:
        F_used = F_interpolated
    st.write(f"- F used in calculations: `{F_used:.2f} mm`")

    # ---------- Geometry from F (used value) ----------
    ira_half = F_used / 2.0
    roller_max_possible = 2.0 * ((pitch_dia / 2.0) - ira_half)
    st.write(f"- Max Roller Diameter Allowed: `{roller_max_possible:.2f} mm`")

    # Z is computed from the *max* possible roller diameter (as requested)
    try:
        Z = int(np.pi / np.arcsin(roller_max_possible / pitch_dia))
    except ValueError:
        st.error("❌ Invalid configuration: asin out of domain.")
        Z = 0

    # Apply 2% pitch-diameter margin *only for catalog selection*
    adjusted_max_dw = roller_max_possible - (0.02 * pitch_dia)
    st.write(f"- Adjusted Max Dw for Selection: `{adjusted_max_dw:.2f} mm`")

    # ---------- Select roller from catalog ----------
    roller_df_filtered = roller_df[(roller_df['dw'] <= adjusted_max_dw) & (roller_df['lw'] <= B)].copy()

    if roller_df_filtered.empty:
        st.error("❌ No rollers available for the adjusted conditions.")
    else:
        # Largest Dw that fits
        top_dw = roller_df_filtered['dw'].max()
        candidates = roller_df_filtered[roller_df_filtered['dw'] == top_dw].sort_values('lw', ascending=False).reset_index(drop=True)

        # Show all candidates with same Dw and let the user pick
        st.success("✅ Recommended Rollers (same Dw, choose one)")
        st.dataframe(candidates[['dw', 'lw', 'r_min', 'r_max', 'mass_per_100']])

        # Build nice labels for selection
        option_labels = [
            f"Option {i+1}: Lw={row.lw} mm | r_min={row.r_min} mm | r_max={row.r_max} mm | mass/100={row.mass_per_100}"
            for i, row in candidates.iterrows()
        ]
        choice_idx = st.selectbox(
            "Pick a roller option (same Dw)",
            options=list(range(len(option_labels))),
            format_func=lambda i: option_labels[i],
            index=0
        )

        chosen = candidates.iloc[choice_idx]

        selected_dw = float(chosen['dw'])
        selected_lw = float(chosen['lw'])
        r_max = float(chosen['r_max'])
        r = 0.75 * r_max
        Lwe = selected_lw - 2.0 * r

        st.info(f"Selected: Dw = {selected_dw}, Lw = {selected_lw}, r = {r:.2f}, Lwe = {Lwe:.2f}, Z = {Z}")

        # ---------- Load rating calculations ----------
        i = st.number_input("🔢 Number of Roller Rows (i)", min_value=1, max_value=8, value=4)

        fc_df = pd.read_excel("ISO_Table_7_fc_values.xlsx")
        fc_df.columns = fc_df.columns.str.lower()
        fc_ratio = selected_dw / pitch_dia
        fc_ratio = np.clip(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"].min(), fc_df["dwe_cos_alpha_over_dpw"].max())
        fc = np.interp(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"], fc_df["fc"])

        bm = 1.1
        Cr = bm * fc * ((i * Lwe) ** (7.0 / 9.0)) * (Z ** (3.0 / 4.0)) * (selected_dw ** (29.0 / 27.0))
        Cor = 44.0 * (1.0 - (selected_dw / pitch_dia)) * i * Z * Lwe * selected_dw

        st.success(f"**Cr = {Cr:,.2f} N**")
        st.success(f"**Cor = {Cor:,.2f} N**")
