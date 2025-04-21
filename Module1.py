import streamlit as st

st.set_page_config(page_title="ABS Bearing Spec Selector", layout="centered")

st.title("🛠️ ABS Smart Specification Selector – Module 1")
st.markdown("This tool recommends bearing specs based on ABS internal standards.")

# --- Input Section ---
st.header("🔧 Input Parameters")

bore_diameter = st.number_input("Bore Diameter (mm)", value=250)
wall_thickness = st.number_input("Effective Wall Thickness (mm)", value=20)
roller_diameter = st.number_input("Roller Diameter (mm)", value=35)

application_type = st.selectbox("Application Type", ["standard", "precision", "high load"])
speed_rpm = st.number_input("Operating Speed (RPM)", value=300)
mill_type = st.selectbox("Mill Type (optional)", [None, "hot mill", "cold mill"])
load_type = st.selectbox("Load Type", ["standard", "impact"])

# --- Logic Section ---

def suggest_bearing_class(application_type):
    if application_type == "precision":
        return "P5"
    else:
        return "P6"

def suggest_clearance(bore_diameter, mill_type=None):
    if mill_type == "hot mill":
        return "C4"
    elif mill_type == "cold mill":
        return "C3"
    elif bore_diameter <= 120:
        return "C2 or Normal"
    elif bore_diameter <= 250:
        return "Normal or C3"
    elif bore_diameter <= 500:
        return "C3 or C4"
    else:
        return "C4 or C5"

def suggest_material_and_heat_treatment(roller_dia, wall_thickness, load_type="standard"):
    if load_type == "impact":
        return ("G20Cr2Ni4A", "Carburizing Heat Treatment")
    if wall_thickness <= 17 and roller_dia <= 32:
        return ("GCr15", "Martensitic Quenching")
    elif wall_thickness > 17 and roller_dia > 32:
        return ("GCr15SiMn", "Martensitic Quenching")
    elif wall_thickness <= 25 and roller_dia <= 45:
        return ("GCr15", "Bainite Isothermal QT")
    elif wall_thickness > 25 and roller_dia > 45:
        return ("GCr18Mo", "Bainite Isothermal QT")
    elif roller_dia > 45:
        return ("GCr18Mo", "Bainite Isothermal QT")
    else:
        return ("GCr15SiMn", "Martensitic Quenching")

def suggest_cage_type(application_type, speed_rpm):
    if application_type == "high load":
        return ("Pin-Type", "Steel")
    elif application_type == "standard" and speed_rpm > 1000:
        return ("Polymer", "Nylon/PTFE")
    elif application_type == "standard" and speed_rpm <= 1000:
        return ("Riveted", "Steel, Mass")
    else:
        return ("Machined", "Steel, Mass")

# --- Output Section ---
if st.button("Generate Recommendation"):
    st.subheader("✅ Specification Recommendation")

    bearing_class = suggest_bearing_class(application_type)
    clearance = suggest_clearance(bore_diameter, mill_type)
    steel, heat_treatment = suggest_material_and_heat_treatment(roller_diameter, wall_thickness, load_type)
    cage_type, cage_material = suggest_cage_type(application_type, speed_rpm)

    st.write(f"**Bearing Class:** {bearing_class}")
    st.write(f"**Clearance Class:** {clearance}")
    st.write(f"**Steel Type:** {steel}")
    st.write(f"**Heat Treatment:** {heat_treatment}")
    st.write(f"**Cage Type & Material:** {cage_type} ({cage_material})")

    st.success("Recommendations generated successfully!")

