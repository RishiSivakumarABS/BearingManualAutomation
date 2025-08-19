import streamlit as st
import pandas as pd
import numpy as np

# ---------- Helpers ----------
def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (df.columns
                  .str.strip()
                  .str.lower()
                  .str.replace(r"\[.*?\]", "", regex=True)
                  .str.replace("  ", " ")
                  .str.replace(" ", "_"))
    return df

def pick_col(df: pd.DataFrame, candidates) -> str:
    for c in candidates:
        if c in df.columns: 
            return c
    raise KeyError(f"None of {candidates} found in columns: {list(df.columns)}")

def load_catalog(which: str) -> pd.DataFrame:
    # which: "Super-precision" or "Standard"
    path = "SKFCatalog_CRB.xlsx" if which == "Super-precision" else "SKF_CRB_Full.xlsx"
    cat = pd.read_excel(path)
    cat = normalize_cols(cat)

    # Try to standardize expected columns across both files
    designation_col = pick_col(cat, ["designation", "bearing_designation", "type"])
    d_col = pick_col(cat, ["bore_diameter", "bore", "d", "inner_diameter"])
    D_col = pick_col(cat, ["outside_diameter", "od", "outer_diameter", "d2", "d_2"])
    B_col = pick_col(cat, ["width", "b"])
    cr_col = pick_col(cat, ["basic_dynamic_load_rating", "c", "cr", "basic_dynamic_load_rating_c"])

    cat = cat.rename(columns={
        designation_col: "designation",
        d_col: "d",
        D_col: "D",
        B_col: "B",
        cr_col: "cr_kN"
    })
    # coerce numeric
    for c in ["d", "D", "B", "cr_kN"]:
        cat[c] = pd.to_numeric(cat[c], errors="coerce")
    cat.dropna(subset=["d", "D", "B"], inplace=True)
    return cat[["designation", "d", "D", "B", "cr_kN"]]

# ---------- Load base tables ----------
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")
ira_df = pd.read_excel("Cylindrical Roller Bearings.xlsx")

# Normalize names
roller_df = normalize_cols(roller_df)
ira_df = normalize_cols(ira_df)

# IRA numeric
for c in ["inner_diameter", "outer_diameter", "f"]:
    ira_df[c] = pd.to_numeric(ira_df[c], errors="coerce")
ira_df.dropna(subset=["inner_diameter", "outer_diameter", "f"], inplace=True)

# Streamlit UI
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.caption("Now with catalog source selection (Super-precision vs Standard).")
st.markdown("---")

# ----------------- Catalog source & prefill -----------------
st.subheader("📚 Catalog Source & Prefill")
colc1, colc2 = st.columns([1, 2])
with colc1:
    catalog_choice = st.radio(
        "Select catalog",
        ["Super-precision", "Standard"],
        index=0,
        help="Super-precision → SKFCatalog_CRB.xlsx   |   Standard → SKF_CRB_Full.xlsx"
    )
cat_df = load_catalog(catalog_choice)

with colc2:
    # Let user pick a designation (or 'None / manual')
    options = ["— None (enter d, D, B manually) —"] + list(cat_df["designation"].astype(str).unique())
    chosen = st.selectbox("Pick a bearing from catalog (optional)", options, index=0)

prefill = None
if chosen != "— None (enter d, D, B manually) —":
    prefill = cat_df.loc[cat_df["designation"].astype(str) == chosen].iloc[0]

st.markdown("---")

# ----------------- Geometry inputs -----------------
st.subheader("📜 Bearing Geometry")
col1, col2 = st.columns(2)
with col1:
    d = st.number_input("🔩 Inner Diameter (d) [mm]", min_value=10.0, max_value=2000.0,
                        value=float(prefill["d"]) if prefill is not None else 280.0, step=0.1)
    B = st.number_input("↔️ Available Width (B) [mm]", min_value=5.0, max_value=1000.0,
                        value=float(prefill["B"]) if prefill is not None else 220.0, step=0.1)
with col2:
    D = st.number_input("🏠 Outer Diameter (D) [mm]", min_value=d + 5.0, max_value=2500.0,
                        value=float(prefill["D"]) if prefill is not None else 390.0, step=0.1)

st.markdown("---")

# ----------------- Operating conditions -----------------
st.subheader("⚙️ Operating Conditions")
col3, col4 = st.columns(2)
with col3:
    Fr = st.number_input("📏 Radial Load (Fr) [kN]", min_value=0.0, value=1980.0, step=1.0)
    RPM = st.number_input("⏱️ Speed (RPM)", min_value=0, value=500, step=10)
with col4:
    Fa = st.number_input("📏 Axial Load (Fa) [kN]", min_value=0.0, value=50.0, step=1.0)
    temperature = st.number_input("🌡️ Operating Temperature (°C)", min_value=-50.0, max_value=300.0, value=80.0, step=1.0)

st.markdown("---")

if st.button("✅ Proceed to Design Calculations", type="primary"):
    st.session_state["go"] = True

if st.session_state.get("go"):
    st.success("Inputs captured successfully!")
    st.write("### 📋 Input Summary")
    st.json({"catalog": catalog_choice,
             "designation": None if prefill is None else prefill["designation"],
             "d": d, "D": D, "B": B, "Fr": Fr, "Fa": Fa, "RPM": RPM, "Temp": temperature})

    # Pitch diameter
    pitch_dia = (d + D) / 2.0
    st.markdown(f"### 🎯 Pitch Diameter = `{pitch_dia:.2f} mm`")

    # ---- Interpolate F from table ----
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

    st.write(f"- Interpolated F: `{F_interpolated:.2f} mm`")
    use_override = st.checkbox("Override F manually")
    if use_override:
        F_used = st.number_input("Enter F [mm]", min_value=0.0, value=round(F_interpolated, 2), step=0.01)
    else:
        F_used = F_interpolated
    st.write(f"- F used in calculations: `{F_used:.2f} mm`")

    # Max possible Dw from F_used
    ira_half = F_used / 2.0
    roller_max_possible = 2.0 * ((pitch_dia / 2.0) - ira_half)
    st.write(f"- Max Roller Diameter Allowed: `{roller_max_possible:.2f} mm`")

    # Z based on *max possible* Dw
    try:
        Z = int(np.pi / np.arcsin(roller_max_possible / pitch_dia))
    except ValueError:
        st.error("❌ Invalid configuration: asin out of domain.")
        Z = 0

    # Only for selecting from catalog: subtract 2% of pitch diameter
    adjusted_max_dw = roller_max_possible - (0.02 * pitch_dia)
    st.write(f"- Adjusted Max Dw for Selection: `{adjusted_max_dw:.2f} mm`")

    # ---------- Roller selection with tie-handling ----------
    roller_df = roller_df.copy()
    # enforce numeric
    for c in ["dw", "lw", "r_min", "r_max", "mass_per_100"]:
        if c in roller_df.columns:
            roller_df[c] = pd.to_numeric(roller_df[c], errors="coerce")
    roller_df = roller_df.dropna(subset=["dw", "lw"])

    pool = roller_df[(roller_df["dw"] <= adjusted_max_dw) & (roller_df["lw"] <= B)].copy()
    if pool.empty:
        st.error("❌ No rollers available for the adjusted conditions.")
        st.stop()

    # Find max Dw in pool
    max_dw = pool["dw"].max()
    candidates = pool[pool["dw"] == max_dw].sort_values("lw", ascending=False)

    st.success("✅ Candidate rollers (same Dw; choose one):")
    st.dataframe(candidates[["dw", "lw", "r_min", "r_max", "mass_per_100"]])

    cand_labels = [f"Dw={row.dw:.1f}, Lw={row.lw:.1f} (r_max={row.r_max})" for _, row in candidates.iterrows()]
    pick_label = st.selectbox("Pick one roller to use", cand_labels, index=0)
    picked = candidates.iloc[cand_labels.index(pick_label)]

    selected_dw = float(picked["dw"])
    selected_lw = float(picked["lw"])
    r_max = float(picked.get("r_max", 0.0))
    r = 0.75 * r_max
    Lwe = selected_lw - 2.0 * r

    st.info(f"Selected: Dw = {selected_dw}, Lw = {selected_lw}, r = {r:.2f}, Lwe = {Lwe:.2f}, Z = {Z}")

    # ---------- Load ratings ----------
    i = st.number_input("🔢 Number of Roller Rows (i)", min_value=1, max_value=8, value=4)

    fc_df = pd.read_excel("ISO_Table_7_fc_values.xlsx")
    fc_df = normalize_cols(fc_df)
    fc_ratio = selected_dw / pitch_dia
    fc_ratio = np.clip(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"].min(), fc_df["dwe_cos_alpha_over_dpw"].max())
    fc = np.interp(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"], fc_df["fc"])

    bm = 1.1
    Cr = bm * fc * ((i * Lwe) ** (7.0 / 9.0)) * (Z ** (3.0 / 4.0)) * (selected_dw ** (29.0 / 27.0))
    Cor = 44.0 * (1.0 - (selected_dw / pitch_dia)) * i * Z * Lwe * selected_dw

    st.success(f"Cr = {Cr:,.2f} N")
    st.success(f"Cor = {Cor:,.2f} N")

    # ---------- Catalog Cr display ----------
    # Only show “Catalog Cr” if dimensions match exactly to a row in the chosen catalog
    exact = cat_df[(cat_df["d"] == d) & (cat_df["D"] == D) & (cat_df["B"] == B)]
    if not exact.empty and not np.isnan(exact.iloc[0]["cr_kN"]):
        st.info(f"Catalog Cr ({catalog_choice}) = {float(exact.iloc[0]['cr_kN']):,.2f} kN")
    else:
        st.info("Catalog Cr: Not from Catalog")
