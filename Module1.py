import streamlit as st

# ----------------------------
# Page Setup
# ----------------------------
st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool helps design custom Four-Row Cylindrical Roller Bearings based on real input constraints.")

# ----------------------------
# Module 1 – Custom Bearing Design Inputs
# ----------------------------
st.header("🔧 Module 1: Custom Bearing Design Inputs")
st.markdown("Enter the known design parameters to begin the custom bearing specification process.")

# Input Fields
col1, col2, col3 = st.columns(3)

with col1:
    shaft_d = st.number_input("🔩 Shaft Diameter (d) [mm]", min_value=50.0, max_value=1000.0, value=180.0)
    Fr = st.number_input("📏 Radial Load (Fr) [kN]", min_value=0.0, value=400.0)
    RPM = st.number_input("⏱️ Speed (RPM)", min_value=0, value=500)

with col2:
    housing_D = st.number_input("🏠 Housing Bore Diameter (D) [mm]", min_value=60.0, max_value=1200.0, value=250.0)
    Fa = st.number_input("📏 Axial Load (Fa) [kN]", min_value=0.0, value=50.0)
    life_hours = st.number_input("⏳ Expected Life (hours)", min_value=0.0, value=20000.0)

with col3:
    width_B = st.number_input("↔️ Available Width (B) [mm]", min_value=10.0, max_value=500.0, value=160.0)
    temperature = st.number_input("🌡️ Operating Temperature (°C)", min_value=-50.0, max_value=250.0, value=80.0)
    mounting = st.selectbox("⚙️ Mounting Type", ["Fixed", "Floating"])
    environment = st.selectbox("🌍 Environment", ["Clean", "Dirty", "Corrosive"])

# Submit Button
if st.button("✅ Proceed to Design Calculations"):
    st.success("Inputs captured successfully!")
    st.write("### 📋 Input Summary")
    st.write({
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

    # Placeholder for next module
    st.info("👉 Next step: calculate cross-section, pick roller size, and compute load ratings (Cr, Cor).")
