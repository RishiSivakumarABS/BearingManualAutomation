import streamlit as st
import pandas as pd

# Load SKF roller tables
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")

# Normalize column names
roller_df.columns = [col.strip().lower().replace(" ", "_") for col in roller_df.columns]

# Set Streamlit page config
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

# Initialize session state
if "proceed_clicked" not in st.session_state:
    st.session_state["proceed_clicked"] = False

# ----------------------------
# Section 1: Bearing Geometry
# ----------------------------
with st.container():
    st.subheader("📐 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        d = st.number_input("🔩 Inner Diameter (d) [mm]", min_value=50.0, max_value=1000.0, value=180.0, key="d")
        B = st.number_input("↔️ Available Width (B) [mm]", min_value=10.0, max_value=500.0, value=160.0, key="B")
    with col2:
        D = st.number_input("🏠 Outer Diameter (D) [mm]", min_value=d + 10, max_value=1200.0, value=250.0, key="D")

st.markdown("---")

# ----------------------------
# Section 2: Operating Conditions
# ----------------------------
with st.container():
    st.subheader("⚙️ Operating Conditions")
    col3, col4 = st.columns(2)
    with col3:
        Fr = st.number_input("📏 Radial Load (Fr) [kN]", min_value=0.0, value=400.0, key="Fr")
        RPM = st.number_input("⏱️ Speed (RPM)", min_value=0, value=500, key="RPM")
    with col4:
        Fa = st.number_input("📏 Axial Load (Fa) [kN]", min_value=0.0, value=50.0, key="Fa")
        temperature = st.number_input("🌡️ Operating Temperature (°C)", min_value=-50.0, max_value=250.0, value=80.0, key="temperature")

st.markdown("---")

# ----------------------------
# Proceed Button
# ----------------------------
if st.button("✅ Proceed to Design Calculations"):
    st.session_state["proceed_clicked"] = True

# ----------------------------
# Proceed Logic
# ----------------------------
if st.session_state["proceed_clicked"]:
    st.success("Inputs captured successfully!")
    st.write("### 📋 Input Summary")
    st.json({
        "Inner Diameter (d)": d,
        "Outer Diameter (D)": D,
        "Available Width (B)": B,
        "Radial Load (Fr)": Fr,
        "Axial Load (Fa)": Fa,
        "Speed (RPM)": RPM,
        "Temperature (°C)": temperature
    })

    # ----------------------------
    # Module 2: Roller Recommendation
    # ----------------------------
    st.markdown("### 🧩 Module 2: Roller Diameter Recommendation")

    safety_margin = st.slider("📏 Safety Margin for Wall & Cage (mm)", min_value=2.0, max_value=10.0, value=5.0)

    if D > d:
        pitch_dia = (d + D) / 2
        total_radial_space = (D - d) / 2
        usable_space = total_radial_space - safety_margin

        st.markdown("### 📐 Cross-Section Calculation")
        st.write(f"- Pitch Diameter: `{pitch_dia:.2f} mm`")
        st.write(f"- Total Radial Space: `{total_radial_space:.2f} mm`")
        st.write(f"- Usable Height (after safety margin): `{usable_space:.2f} mm`")

        valid = roller_df[roller_df["dw"] <= usable_space].copy()

        if not valid.empty:
            st.success(f"✅ {len(valid)} roller options available within usable space.")
            st.dataframe(valid[["dw", "lw", "r_min", "r_max", "mass_per_100"]].sort_values(by=["dw", "lw"]))

            recommended = valid.sort_values(by=["dw", "lw"], ascending=[False, False]).iloc[0]
            st.markdown("### 🎯 Recommended Roller")
            st.info(
                f"**Dw:** {recommended.dw} mm  "
                f"**Lw:** {recommended.lw} mm  "
                f"**r_min:** {recommended.r_min} mm  "
                f"**r_max:** {recommended.r_max} mm  "
                f"**Mass/100:** {recommended.mass_per_100} kg"
            )

            # ----------------------------
            # Designer Roller Selection
            # ----------------------------
            st.markdown("### ✍️ Designer Selection")
            use_custom = st.radio("Would you like to use the recommended roller or input your own?", ["Use Recommended", "Input Custom"], index=0)

            if use_custom == "Use Recommended":
                selected_dw = recommended.dw
                selected_lw = recommended.lw
                selected_r_min = recommended.r_min
                selected_r_max = recommended.r_max
                selected_mass = recommended.mass_per_100
            else:
                selected_dw = st.number_input("🌀 Custom Roller Diameter (Dw) [mm]", min_value=1.0, max_value=usable_space, key="custom_dw")
                selected_lw = st.number_input("📏 Custom Roller Length (Lw) [mm]", min_value=1.0, max_value=B, key="custom_lw")

                # Estimate values for custom roller
                selected_r_min = 0.2
                selected_r_max = 0.6
                density_steel = 7.85  # g/cm³
                volume_mm3 = 3.14 * (selected_dw / 2) ** 2 * selected_lw
                mass_grams = (volume_mm3 * density_steel) / 1000
                selected_mass = round((mass_grams * 100) / 1000, 3)

            st.markdown("### ✅ Final Roller Configuration")
            st.write(f"- Roller Diameter (Dw): `{selected_dw} mm`")
            st.write(f"- Roller Length (Lw): `{selected_lw} mm`")
            st.write(f"- r_min: `{selected_r_min} mm`")
            st.write(f"- r_max: `{selected_r_max} mm`")
            st.write(f"- Mass per 100 rollers: `{selected_mass} kg`")

        else:
            st.error("❌ No standard rollers fit in the available space.")
            st.info("Please proceed by inputting a custom roller configuration.")

            selected_dw = st.number_input("🌀 Custom Roller Diameter (Dw) [mm]", min_value=1.0, max_value=usable_space, key="custom_dw_only")
            selected_lw = st.number_input("📏 Custom Roller Length (Lw) [mm]", min_value=1.0, max_value=B, key="custom_lw_only")

            selected_r_min = 0.2
            selected_r_max = 0.6
            density_steel = 7.85
            volume_mm3 = 3.14 * (selected_dw / 2) ** 2 * selected_lw
            mass_grams = (volume_mm3 * density_steel) / 1000
            selected_mass = round((mass_grams * 100) / 1000, 3)

            st.markdown("### ✅ Final Roller Configuration")
            st.write(f"- Roller Diameter (Dw): `{selected_dw} mm`")
            st.write(f"- Roller Length (Lw): `{selected_lw} mm`")
            st.write(f"- r_min: `{selected_r_min} mm`")
            st.write(f"- r_max: `{selected_r_max} mm`")
            st.write(f"- Mass per 100 rollers: `{selected_mass} kg`")
    else:
        st.warning("⚠️ Outer diameter must be greater than inner diameter.")
