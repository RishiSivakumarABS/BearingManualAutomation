import streamlit as st
import pandas as pd
import numpy as np

# =========================
# Helpers
# =========================
def normalize_cols(df):
    df = df.copy()
    df.columns = (
        pd.Index(df.columns)
        .map(lambda x: " ".join([str(p) for p in x if str(p) != "nan"]) if isinstance(x, tuple) else str(x))
        .str.strip().str.lower().str.replace(r"\s+", "_", regex=True)
    )
    return df

def find_col(df, *contains):
    """Find a column whose name includes all 'contains' tokens (case-insensitive)."""
    for c in df.columns:
        s = str(c).lower()
        if all(tok in s for tok in contains):
            return c
    return None

def load_catalog(path="SKFCatalog_CRB.xlsx"):
    # Try reading with multirow header (some SKF sheets have a units row)
    try:
        cat = pd.read_excel(path, header=[0,1])
        cat = normalize_cols(cat)
    except Exception:
        cat = pd.read_excel(path)
        cat = normalize_cols(cat)

    # Map columns by fuzzy matching
    c_designation = find_col(cat, "designation")
    c_bore = find_col(cat, "bore", "diameter")
    c_od = find_col(cat, "outside", "diameter")
    c_width = find_col(cat, "width")
    c_c = find_col(cat, "basic", "dynamic", "load") or find_col(cat, "c_") or find_col(cat, "cr")

    needed = [c_designation, c_bore, c_od, c_width]
    if any(col is None for col in needed):
        raise ValueError("Could not find required columns in SKFCatalog_CRB.xlsx "
                         "(need Designation, Bore diameter, Outside diameter, Width).")

    out = cat[[c_designation, c_bore, c_od, c_width] + ([c_c] if c_c else [])].copy()
    out.columns = ["designation", "d", "D", "B"] + (["C_catalog"] if c_c else [])
    # Clean numerics
    for col in ["d", "D", "B", "C_catalog"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["designation", "d", "D", "B"])
    return out

# =========================
# Load files
# =========================
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")
ira_df = pd.read_excel("Cylindrical Roller Bearings.xlsx")

ira_df = normalize_cols(ira_df)
roller_df = normalize_cols(roller_df)

# Convert IRA columns to numeric
ira_df['inner_diameter'] = pd.to_numeric(ira_df['inner_diameter'], errors='coerce')
ira_df['outer_diameter'] = pd.to_numeric(ira_df['outer_diameter'], errors='coerce')
ira_df['f'] = pd.to_numeric(ira_df['f'], errors='coerce')
ira_df.dropna(subset=['inner_diameter', 'outer_diameter', 'f'], inplace=True)

# =========================
# Streamlit setup
# =========================
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

# =========================
# Catalog selection (NEW)
# =========================
with st.expander("📘 Choose a bearing from SKF catalog (optional)", expanded=False):
    try:
        catalog = load_catalog("SKFCatalog_CRB.xlsx")
        # Quick search
        q = st.text_input("Search designation (contains)", value="")
        filtered = catalog[catalog["designation"].str.contains(q, case=False, na=False)] if q else catalog

        # Build options label
        def label_row(row):
            base = f"{row['designation']}  |  d={row['d']:.0f} mm, D={row['D']:.0f} mm, B={row['B']:.0f} mm"
            if "C_catalog" in filtered.columns and pd.notna(row["C_catalog"]):
                base += f"  |  C={row['C_catalog']:.1f} kN"
            return base

        options = filtered.index.tolist()
        labels = [label_row(filtered.loc[idx]) for idx in options]
        chosen_idx = st.selectbox("Catalog result", options=options, format_func=lambda ix: label_row(filtered.loc[ix]) if ix in filtered.index else "")

        colA, colB = st.columns([1,1])
        with colA:
            if st.button("Use these dimensions"):
                row = filtered.loc[chosen_idx]
                # Prefill session state so the inputs pick these values as defaults
                st.session_state["geo_d"] = float(row["d"])
                st.session_state["geo_D"] = float(row["D"])
                st.session_state["geo_B"] = float(row["B"])
                st.success(f"Loaded from catalog → d={row['d']:.0f}, D={row['D']:.0f}, B={row['B']:.0f}")
        with colB:
            if "C_catalog" in filtered.columns:
                row = filtered.loc[chosen_idx]
                if pd.notna(row["C_catalog"]):
                    st.info(f"Catalog basic dynamic load rating **C = {row['C_catalog']:.1f} kN** (for reference)")

    except Exception as e:
        st.warning(f"Could not load catalog: {e}")

st.markdown("---")

if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

# =========================
# Inputs
# =========================
with st.container():
    st.subheader("📜 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        d = st.number_input(
            "🔩 Inner Diameter (d) [mm]",
            min_value=50.0, max_value=1000.0,
            value=float(st.session_state.get("geo_d", 280.0)),
            key="input_d"
        )
        B = st.number_input(
            " Available Width (B) [mm]",
            min_value=10.0, max_value=500.0,
            value=float(st.session_state.get("geo_B", 220.0)),
            key="input_B"
        )
    with col2:
        D = st.number_input(
            "🏠 Outer Diameter (D) [mm]",
            min_value=d + 10, max_value=1200.0,
            value=float(st.session_state.get("geo_D", 390.0)),
            key="input_D"
        )

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

# =========================
# Main logic
# =========================
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
        F_used = st.number_input("Enter F [mm]", min_value=0.0, value=round(F_interpolated, 2), step=0.01,
                                 help="Override the interpolated F. All downstream calculations will use this value.")
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
        # Choose largest Dw, and among those, the largest Lw
        top_dw = roller_df_filtered['dw'].max()
        top_roller = roller_df_filtered[roller_df_filtered['dw'] == top_dw].sort_values('lw', ascending=False).iloc[0]

        selected_dw = float(top_roller['dw'])
        selected_lw = float(top_roller['lw'])
        r_max = float(top_roller['r_max'])
        r = 0.75 * r_max
        Lwe = selected_lw - 2.0 * r

        st.info(f"Selected: Dw = {selected_dw}, Lw = {selected_lw}, r = {r:.2f}, Lwe = {Lwe:.2f}, Z = {Z}")

        # ---------- Load rating calculations ----------
        i = st.number_input("🔢 Number of Roller Rows (i)", min_value=1, max_value=8, value=4)

        fc_df = pd.read_excel("ISO_Table_7_fc_values.xlsx")
        fc_df = normalize_cols(fc_df)
        fc_ratio = selected_dw / pitch_dia
        fc_ratio = np.clip(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"].min(), fc_df["dwe_cos_alpha_over_dpw"].max())
        fc = np.interp(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"], fc_df["fc"])

        bm = 1.1
        Cr = bm * fc * ((i * Lwe) ** (7.0 / 9.0)) * (Z ** (3.0 / 4.0)) * (selected_dw ** (29.0 / 27.0))
        Cor = 44.0 * (1.0 - (selected_dw / pitch_dia)) * i * Z * Lwe * selected_dw

        st.success(f"**Cr = {Cr:,.2f} N**")
        st.success(f"**Cor = {Cor:,.2f} N**")
