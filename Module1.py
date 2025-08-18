import streamlit as st
import pandas as pd
import numpy as np
import os

# ----------------------------
# Load data
# ----------------------------
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")
ira_df = pd.read_excel("Cylindrical Roller Bearings.xlsx")

# Normalize column names
ira_df.columns = ira_df.columns.str.strip().str.lower().str.replace(" ", "_")
roller_df.columns = roller_df.columns.str.strip().str.lower().str.replace(" ", "_")

# Convert IRA columns to numeric
ira_df["inner_diameter"] = pd.to_numeric(ira_df["inner_diameter"], errors="coerce")
ira_df["outer_diameter"] = pd.to_numeric(ira_df["outer_diameter"], errors="coerce")
ira_df["f"] = pd.to_numeric(ira_df["f"], errors="coerce")
ira_df.dropna(subset=["inner_diameter", "outer_diameter", "f"], inplace=True)

# Optional: SKF catalog for prefilling d, D, B
catalog_df, catalog_choice = None, None
if os.path.exists("SKFCatalog_CRB.xlsx"):
    try:
        catalog_df = pd.read_excel("SKFCatalog_CRB.xlsx")
        catalog_df.columns = catalog_df.columns.str.strip().str.lower().str.replace(" ", "_")

        def first_match(cols, options):
            for opt in options:
                if opt in cols:
                    return opt
            return None

        cols = set(catalog_df.columns)
        col_des = first_match(cols, ["designation", "bearing", "name"])
        col_d   = first_match(cols, ["bore_diameter", "d", "bore"])
        col_D   = first_match(cols, ["outside_diameter", "od", "outside"])
        col_B   = first_match(cols, ["width", "b"])
        # try to find catalog dynamic load rating column
        col_C   = first_match(cols, [
            "basic_dynamic_load_rating", "c", "cr", "dynamic_load_rating", "basic_dynamic"
        ])

        if all([col_des, col_d, col_D, col_B]):
            keep = ["designation","d","D","B"]
            rename_map = {col_des: "designation", col_d:"d", col_D:"D", col_B:"B"}
            if col_C: 
                keep.append(col_C)
                rename_map[col_C] = "C_catalog"
            catalog_df = catalog_df[[col_des, col_d, col_D, col_B] + ([col_C] if col_C else [])].rename(columns=rename_map)
            for c in ["d", "D", "B"]:
                catalog_df[c] = pd.to_numeric(catalog_df[c], errors="coerce")
            if "C_catalog" in catalog_df.columns:
                catalog_df["C_catalog"] = pd.to_numeric(catalog_df["C_catalog"], errors="coerce")
            catalog_df.dropna(subset=["d", "D", "B"], inplace=True)
        else:
            catalog_df = None
    except Exception:
        catalog_df = None

# ----------------------------
# Streamlit setup
# ----------------------------
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

# ----------------------------
# Bearing selection (optional catalog)
# ----------------------------
prefill = None
if catalog_df is not None and not catalog_df.empty:
    with st.expander("📚 Prefill from SKF Catalog (optional)"):
        names = catalog_df["designation"].astype(str).tolist()
        pick = st.selectbox("Choose a bearing from catalog (to prefill d, D, B)", ["— none —"] + names, index=0)
        if pick != "— none —":
            row = catalog_df.loc[catalog_df["designation"] == pick].iloc[0]
            prefill = {"d": float(row["d"]), "D": float(row["D"]), "B": float(row["B"])}
            catalog_choice = pick  # remember choice
else:
    st.caption("Catalog prefill: *SKFCatalog_CRB.xlsx* not found (optional).")

# ----------------------------
# Inputs
# ----------------------------
with st.container():
    st.subheader("📜 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        d = st.number_input(
            "🔩 Inner Diameter (d) [mm]", min_value=50.0, max_value=1000.0,
            value=(prefill["d"] if prefill else 280.0)
        )
        B = st.number_input(
            " Available Width (B) [mm]", min_value=10.0, max_value=500.0,
            value=(prefill["B"] if prefill else 220.0)
        )
    with col2:
        D = st.number_input(
            "🏠 Outer Diameter (D) [mm]", min_value=d + 10, max_value=1200.0,
            value=(prefill["D"] if prefill else 390.0)
        )

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

# ----------------------------
# Main logic
# ----------------------------
if st.session_state["proceed_clicked"]:
    st.success("Inputs captured successfully!")
    st.write("### 📋 Input Summary")
    st.json({"d": d, "D": D, "B": B, "Fr": Fr, "Fa": Fa, "RPM": RPM, "Temp": temperature})

    pitch_dia = (d + D) / 2.0
    st.markdown(f"### 🎯 Pitch Diameter = `{pitch_dia:.2f} mm`")

    # ---------- Interpolate F from IRA table ----------
    lower = ira_df[
        (ira_df["inner_diameter"] <= d) & (ira_df["outer_diameter"] <= D)
    ].sort_values(by=["inner_diameter", "outer_diameter"], ascending=False).head(1)

    upper = ira_df[
        (ira_df["inner_diameter"] >= d) & (ira_df["outer_diameter"] >= D)
    ].sort_values(by=["inner_diameter", "outer_diameter"], ascending=True).head(1)

    if not lower.empty and not upper.empty:
        x0, y0, f0 = lower.iloc[0][["inner_diameter", "outer_diameter", "f"]]
        x1, y1, f1 = upper.iloc[0][["inner_diameter", "outer_diameter", "f"]]
        weight = ((d - x0) + (D - y0)) / ((x1 - x0) + (y1 - y0) + 1e-6)
        F_interpolated = float(f0 + weight * (f1 - f0))
    else:
        F_interpolated = float(
            ira_df.loc[
                ((ira_df["inner_diameter"] - d).abs() + (ira_df["outer_diameter"] - D).abs()).idxmin(),
                "f"
            ]
        )

    # Manual override for F
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

    # Geometry using F_used
    ira_half = F_used / 2.0
    roller_max_possible = 2.0 * ((pitch_dia / 2.0) - ira_half)
    st.write(f"- Max Roller Diameter Allowed: `{roller_max_possible:.2f} mm`")

    # Z from *max* possible roller diameter (not adjusted)
    try:
        Z = int(np.pi / np.arcsin(roller_max_possible / pitch_dia))
    except ValueError:
        st.error("❌ Invalid configuration: asin out of domain.")
        Z = 0

    # Apply 2% PCD margin for catalog selection only
    adjusted_max_dw = roller_max_possible - (0.02 * pitch_dia)
    st.write(f"- Adjusted Max Dw for Selection: `{adjusted_max_dw:.2f} mm`")

    # ---------- Select roller from catalog (chooser for same Dw) ----------
    roller_df_filtered = roller_df[(roller_df["dw"] <= adjusted_max_dw) & (roller_df["lw"] <= B)].copy()

    if roller_df_filtered.empty:
        st.error("❌ No rollers available for the adjusted conditions.")
    else:
        top_dw = roller_df_filtered["dw"].max()
        candidates = (
            roller_df_filtered[roller_df_filtered["dw"] == top_dw]
            .sort_values("lw", ascending=False)
            .reset_index(drop=True)
        )

        st.success("✅ Recommended rollers at the maximum Dw")
        st.dataframe(candidates[["dw", "lw", "r_min", "r_max", "mass_per_100"]])

        if len(candidates) > 1:
            option_labels = [
                f"Option {i+1}: Lw={row.lw} mm | r_max={row.r_max} mm | mass/100={row.mass_per_100}"
                for i, row in candidates.iterrows()
            ]
            choice_idx = st.radio(
                "Choose one of the rollers with the same Dw",
                options=list(range(len(candidates))),
                format_func=lambda i: option_labels[i],
                index=0,
                horizontal=False,
            )
            chosen = candidates.iloc[choice_idx]
        else:
            chosen = candidates.iloc[0]
            st.info("Only one roller available at the maximum Dw; selected automatically.")

        selected_dw = float(chosen["dw"])
        selected_lw = float(chosen["lw"])
        r_max = float(chosen["r_max"])
        r = 0.75 * r_max
        Lwe = selected_lw - 2.0 * r

        st.info(f"Selected: Dw = {selected_dw}, Lw = {selected_lw}, r = {r:.2f}, Lwe = {Lwe:.2f}, Z = {Z}")

        # ---------- Load rating calculations ----------
        i = st.number_input("🔢 Number of Roller Rows (i)", min_value=1, max_value=8, value=4)

        # fc from ISO Table 7
        fc_df = pd.read_excel("ISO_Table_7_fc_values.xlsx")
        fc_df.columns = fc_df.columns.str.lower()
        fc_ratio = selected_dw / pitch_dia
        fc_ratio = np.clip(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"].min(), fc_df["dwe_cos_alpha_over_dpw"].max())
        fc = np.interp(fc_ratio, fc_df["dwe_cos_alpha_over_dpw"], fc_df["fc"])

        # Cr & Cor
        bm = 1.1  # cylindrical roller bearings
        Cr = bm * fc * ((i * Lwe) ** (7.0 / 9.0)) * (Z ** (3.0 / 4.0)) * (selected_dw ** (29.0 / 27.0))
        Cor = 44.0 * (1.0 - (selected_dw / pitch_dia)) * i * Z * Lwe * selected_dw

        st.success(f"**Cr = {Cr:,.2f} N**")
        st.success(f"**Cor = {Cor:,.2f} N**")

        # ---------- Catalog C (Cr) readout ----------
        if catalog_choice and (catalog_df is not None):
            row = catalog_df.loc[catalog_df["designation"] == catalog_choice].iloc[0]
            if "C_catalog" in row and pd.notna(row["C_catalog"]):
                # Most catalogs list C in kN. If the value is "reasonable" (< 1e4), convert kN → N.
                C_val = float(row["C_catalog"])
                C_N = C_val * 1000.0 if C_val < 1e4 else C_val
                st.info(f"Catalog C (Cr) for **{catalog_choice}**: **{C_N:,.0f} N**")
            else:
                st.info(f"Catalog C (Cr): not provided in file for **{catalog_choice}**.")
        else:
            st.info("Catalog C (Cr): **Not from catalog**")
