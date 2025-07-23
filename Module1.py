import streamlit as st
import pandas as pd
import numpy as np

# Load data
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")
ira_df = pd.read_excel("Cylindrical Roller Bearings.xlsx")

ira_df.columns = ira_df.columns.str.strip().str.lower().str.replace(" ", "_")
ira_df['inner_diameter'] = pd.to_numeric(ira_df['inner_diameter'], errors='coerce')
ira_df['outer_diameter'] = pd.to_numeric(ira_df['outer_diameter'], errors='coerce')
ira_df['F'] = pd.to_numeric(ira_df['f'], errors='coerce')
ira_df.dropna(subset=['inner_diameter', 'outer_diameter', 'f'], inplace=True)

roller_df.columns = roller_df.columns.str.strip().str.lower().str.replace(" ", "_")

st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("---")

if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

with st.container():
    st.subheader("📐 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        d = st.number_input("🔩 Inner Diameter (d)", min_value=50.0, max_value=1000.0, value=280.0)
        B = st.number_input("↔️ Available Width (B)", min_value=10.0, max_value=500.0, value=160.0)
    with col2:
        D = st.number_input("🏠 Outer Diameter (D)", min_value=d + 10, max_value=1200.0, value=390.0)

st.markdown("---")

if st.button("✅ Proceed to Design Calculations"):
    st.session_state["proceed_clicked"] = True

if st.session_state["proceed_clicked"]:
    pitch_dia = (d + D) / 2
    st.markdown(f"### 🎯 Pitch Diameter = `{pitch_dia:.2f} mm`")

    # Interpolate F
    same_d = ira_df[ira_df['inner_diameter'] == d]
    same_D = ira_df[ira_df['outer_diameter'] == D]

    f_interp_d = np.interp(D, same_d['outer_diameter'], same_d['F']) if len(same_d) >= 2 else None
    f_interp_D = np.interp(d, same_D['inner_diameter'], same_D['F']) if len(same_D) >= 2 else None

    if f_interp_d and f_interp_D:
        F = (f_interp_d + f_interp_D) / 2
    elif f_interp_d:
        F = f_interp_d
    elif f_interp_D:
        F = f_interp_D
    else:
        closest_match = ira_df.loc[((ira_df['inner_diameter'] - d).abs() +
                                    (ira_df['outer_diameter'] - D).abs()).idxmin()]
        F = closest_match['F']

    st.write(f"🔧 **Interpolated F:** `{F:.2f} mm`")

    ira_half = F / 2
    roller_max_possible = 2 * ((pitch_dia / 2) - ira_half)
    st.write(f"🧮 **Max Roller Diameter Allowed:** `{roller_max_possible:.2f} mm`")

    # Suggest roller(s)
    roller_df_filtered = roller_df[(roller_df['dw'] <= roller_max_possible) & (roller_df['lw'] <= B)]
    if roller_df_filtered.empty:
        st.error("❌ No rollers available below max roller diameter and width.")
    else:
        roller_df_filtered = roller_df_filtered.sort_values(by='dw', ascending=False)
        top_dw = roller_df_filtered['dw'].iloc[0]
        top_rollers = roller_df_filtered[roller_df_filtered['dw'] == top_dw]

        st.success("✅ Recommended Rollers (Closest to Max Diameter)")
        st.dataframe(top_rollers[['dw', 'lw', 'r_min', 'r_max', 'mass_per_100']])

        selected_dw = top_rollers.iloc[0]['dw']
        selected_lw = top_rollers.iloc[0]['lw']
        pitch_dia = (d + D) / 2
        try:
            Z = int(np.pi / np.arcsin(selected_dw / pitch_dia))
        except:
            Z = 0

        st.write(f"- Selected: Dw = `{selected_dw}`, Lw = `{selected_lw}`, Z = `{Z}`")

        i = st.number_input("🔢 Number of Roller Rows (i)", min_value=1, max_value=8, value=4)

        fc_df = pd.read_excel("ISO_Table_7_fc_values.xlsx")
        fc_df.columns = fc_df.columns.str.lower()
        fc_ratio = selected_dw / pitch_dia
        fc_ratio = np.clip(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"].min(), fc_df["dwe_cos_alpha_over_dpw"].max())
        fc = np.interp(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"], fc_df["fc"])

        bm = 1.1
        Cr = bm * fc * ((i * selected_lw) ** (7 / 9)) * (Z ** (3 / 4)) * (selected_dw ** (29 / 27))
        st.success(f"**Cr = {Cr:,.2f} N**")

        Cor = 44 * (1 - (selected_dw / pitch_dia)) * i * Z * selected_lw * selected_dw
        st.success(f"**Cor = {Cor:,.2f} N**")
