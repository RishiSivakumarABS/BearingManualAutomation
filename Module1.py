import streamlit as st
import pandas as pd
import math

# Load SKF roller tables
roller_df = pd.read_excel("Cylindrical Roller Table.xlsx")
tolerance_df = pd.read_excel("Roller_Tolerances_SKF.xlsx")

# Normalize column names
roller_df.columns = [col.strip().lower().replace(" ", "_") for col in roller_df.columns]

# Mass calculation function for custom rollers
def calculate_mass_per_100(dw_mm, lw_mm):
    dw_m = dw_mm / 1000
    lw_m = lw_mm / 1000
    volume = math.pi * (dw_m ** 2) / 4 * lw_m
    return round(100 * volume * 7850, 3)  # 7850 kg/m³ is chrome steel density

# Page setup
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")
st.markdown("---")

# Geometry Inputs
with st.container():
    st.subheader("📐 Bearing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        shaft_d = st.number_input("🔩 Shaft Diameter (d) [mm]", min_value=50.0, max_value=1000.0, value=180.0)
        width_B = st.number_input("↔️ Available Width (B) [mm]", min_value=10.0, max_value=500.0, value=160.0)
    with col2:
        housing_D = st.number_input("🏠 Housing Bore Diameter (D) [mm]", min_value=shaft_d+10, max_value=1200.0, value=250.0)

st.markdown("---")

# Load and Speed
with st.container():
    st.subheader("⚙️ Load and Speed Requirements")
    col3, col4 = st.columns(2)
    with col3:
        Fr = st.number_input("📏 Radial Load (Fr) [kN]", min_value=0.0, value=400.0)
        RPM = st.number_input("⏱️ Speed (RPM)", min_value=0, value=500)
    with col4:
        Fa = st.number_input("📏 Axial Load (Fa) [kN]", min_value=0.0, value=50.0)
        life_hours = st.number_input("⏳ Expected Life (hours)", min_value=0.0, value=20000.0)

st.markdown("---")

# Environment
with st.container():
    st.subheader("🌡️ Operating Conditions")
    col5, col6 = st.columns(2)
    with col5:
        temperature = st.number_input("🌡️ Operating Temperature (°C)", min_value=-50.0, max_value=250.0, value=80.0)
    with col6:
        mounting = st.selectbox("⚙️ Mounting Type", ["Fixed", "Floating"])
        environment = st.selectbox("🌍 Environment", ["Clean", "Dirty", "Corrosive"])

st.markdown("---")

# Proceed Button
if st.button("✅ Proceed to Design Calculations"):
    st.success("Inputs captured successfully!")
    st.write("### 📋 Input Summary")
    st.json({
        "Shaft Diameter (d)": shaft_d,
        "Housing Bore Diameter (D)": housing_D,
        "Available Width (B)": width_B,
        "Radial Load (Fr)": Fr,
        "Axial Load (Fa)": Fa,
        "Speed (RPM)": RPM,
        "Life (hours)": life_hours,
        "Temperature (°C)": temperature,
        "Mounting Type": mounting,
        "Environment": environment
    })

    # Module 2 - Roller Size Estimation
    st.markdown("### 🧩 Module 2: Roller Diameter Recommendation")
    safety_margin = st.slider("📏 Safety Margin for Wall & Cage (mm)", min_value=2.0, max_value=10.0, value=5.0)

    if housing_D > shaft_d:
        reference_dia = (shaft_d + housing_D) / 2
        total_radial_space = (housing_D - shaft_d) / 2
        usable_space = total_radial_space - safety_margin

        st.markdown("### 📐 Cross-Section Calculation")
        st.write(f"- Reference Diameter: `{reference_dia:.2f} mm`")
        st.write(f"- Total Radial Space: `{total_radial_space:.2f} mm`")
        st.write(f"- Usable Height (after safety margin): `{usable_space:.2f} mm`")

        valid = roller_df[roller_df["dw"] <= usable_space].copy()

        if not valid.empty:
            st.success(f"✅ {len(valid)} roller options available within usable space.")
            st.dataframe(valid[["dw", "lw", "r_min", "r_max", "mass_per_100"]].sort_values(by=["dw", "lw"]))
        else:
            st.error("❌ No standard rollers fit in the available space. Consider custom roller.")
            st.markdown("#### 🔧 Enter Custom Roller Details")
            custom_dw = st.number_input("🌀 Custom Roller Diameter (Dw) [mm]", min_value=1.0, max_value=usable_space)
            custom_lw = st.number_input("📏 Custom Roller Length (Lw) [mm]", min_value=1.0, max_value=width_B)
            r_min = 0.3
            r_max = 0.7
            custom_mass = calculate_mass_per_100(custom_dw, custom_lw)
            st.info(f"📍 Using custom roller: Dw = {custom_dw} mm, Lw = {custom_lw} mm")
            st.write(f"Estimated r_min = {r_min} mm | r_max = {r_max} mm | Mass per 100 pcs = {custom_mass} kg")
    else:
        st.warning("⚠️ Housing diameter must be greater than shaft diameter.")
