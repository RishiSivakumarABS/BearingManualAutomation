import streamlit as st
from docx import Document
from datetime import datetime
import pandas as pd
import io

st.set_page_config(page_title="ABS Bearing Design Tool", layout="wide")
st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool assists in selecting bearing specifications and calculating tolerance deviations based on ABS internal standards.")

# ----------------------------
# Module 3: Material & Heat Treatment Selector
# ----------------------------
def suggest_material_and_treatment_module3(roller_dia, wall_thickness, load_type="standard"):
    load_type = load_type.lower()
    if load_type == "impact":
        return "G20Cr2Ni4A", "Carburizing Heat Treatment"
    if wall_thickness <= 17 and roller_dia <= 32:
        return "GCr15", "Martensitic Quenching"
    elif wall_thickness > 17 and roller_dia > 32:
        return "GCr15SiMn", "Martensitic Quenching"
    elif wall_thickness <= 25 and roller_dia <= 45:
        return "GCr15", "Bainite Isothermal QT"
    elif wall_thickness > 25 and roller_dia > 45:
        return "GCr18Mo", "Bainite Isothermal QT"
    elif roller_dia > 45:
        return "GCr18Mo", "Bainite Isothermal QT"
    else:
        return "GCr15SiMn", "Martensitic Quenching"

# ----------------------------
# Module 4: Roller Profile Table
# ----------------------------
roller_profile_df = pd.DataFrame([
    {"Profile Type": "Logarithmic", "Min Dia (mm)": 20, "Max Dia (mm)": 40, "Max Deviation (µm)": 3.0},
    {"Profile Type": "Logarithmic", "Min Dia (mm)": 40, "Max Dia (mm)": 60, "Max Deviation (µm)": 4.0},
    {"Profile Type": "Crowned",     "Min Dia (mm)": 20, "Max Dia (mm)": 40, "Max Deviation (µm)": 2.0},
    {"Profile Type": "Crowned",     "Min Dia (mm)": 40, "Max Dia (mm)": 60, "Max Deviation (µm)": 3.0},
    {"Profile Type": "Flat",        "Min Dia (mm)": 20, "Max Dia (mm)": 60, "Max Deviation (µm)": 1.0},
])

def get_max_deviation(profile_type, diameter):
    for _, row in roller_profile_df.iterrows():
        if row['Profile Type'].lower() == profile_type.lower() and row['Min Dia (mm)'] <= diameter <= row['Max Dia (mm)']:
            return row['Max Deviation (µm)']
    return None

# ----------------------------
# Module 2: Load Tolerance Tables
# ----------------------------
@st.cache_data
def load_tolerance_tables():
    df_normal = pd.read_excel("Table1_Normal_Tolerances.xlsx")
    df_p6 = pd.read_excel("Table2_P6_Tolerances.xlsx")
    df_p5 = pd.read_excel("Table3_P5_Tolerances.xlsx")
    return df_normal, df_p6, df_p5

df_normal, df_p6, df_p5 = load_tolerance_tables()
class_tables = {"Normal": df_normal, "P6": df_p6, "P5": df_p5}

def find_tolerance(bore_dia, tolerance_class):
    df = class_tables.get(tolerance_class)
    if df is None:
        return None, None
    for _, row in df.iterrows():
        if row['Min Diameter (mm)'] < bore_dia <= row['Max Diameter (mm)']:
            return row['Upper Deviation (µm)'], row['Lower Deviation (µm)']
    return None, None

# ----------------------------
# Module 5: Clearance Class Checker
# ----------------------------
def suggest_clearance(bore_dia, mill_type=None):
    if mill_type == "hot mill":
        return "C4"
    elif mill_type == "cold mill":
        return "C3"
    elif bore_dia <= 120:
        return "C2 or Normal"
    elif bore_dia <= 250:
        return "Normal or C3"
    elif bore_dia <= 500:
        return "C3 or C4"
    else:
        return "C4 or C5"

# ----------------------------
# Tabs for Modules 1 to 6
# ----------------------------
tabs = st.tabs([
    "Smart Specification Selector", 
    "Tolerance & Fit Calculator",
    "Roller Profile Matching",
    "Material & Heat Treatment Selector",
    "Clearance Class Checker",
    "Final Compliance Validator"
])

# ----------------------------
# Module 1 – Spec Selector
# ----------------------------
with tabs[0]:
    st.header("🔧 Module 1: Smart Specification Selector")
    bore = st.number_input("Bore Diameter (mm)", value=250, key="mod1_bore")
    wall = st.number_input("Wall Thickness (mm)", value=20, key="mod1_wall")
    roller = st.number_input("Roller Diameter (mm)", value=35, key="mod1_roller")
    app = st.selectbox("Application Type", ["standard", "precision", "high load"], key="mod1_app")
    rpm = st.number_input("Operating Speed (RPM)", value=300, key="mod1_rpm")
    mill = st.selectbox("Mill Type (optional)", [None, "hot mill", "cold mill"], key="mod1_mill")
    load = st.selectbox("Load Type", ["standard", "impact"], key="mod1_load")

    def bearing_class(app_type): return "P5" if app_type == "precision" else "P6"

    def cage(app_type, rpm_val):
        if app_type == "high load": return "Pin-Type", "Steel"
        elif app_type == "standard" and rpm_val > 1000: return "Polymer", "Nylon/PTFE"
        elif app_type == "standard": return "Riveted", "Steel, Mass"
        else: return "Machined", "Steel, Mass"

    if st.button("Generate Specification Recommendation", key="btn_mod1"):
        bc = bearing_class(app)
        cc = suggest_clearance(bore, mill)
        steel, ht = suggest_material_and_treatment_module3(roller, wall, load)
        ct, cm = cage(app, rpm)

        st.write(f"**Bearing Class:** {bc}")
        st.write(f"**Clearance Class:** {cc}")
        st.write(f"**Steel Type:** {steel}")
        st.write(f"**Heat Treatment:** {ht}")
        st.write(f"**Cage Type & Material:** {ct} ({cm})")
        st.success("✅ Recommendation generated.")

        doc = Document()
        doc.add_heading('ABS Bearing Design Report', level=1)
        doc.add_paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        doc.add_paragraph(f"Bore Diameter: {bore} mm")
        doc.add_paragraph(f"Bearing Class: {bc}")
        doc.add_paragraph(f"Clearance Class: {cc}")
        doc.add_paragraph(f"Steel Type: {steel}")
        doc.add_paragraph(f"Heat Treatment: {ht}")
        doc.add_paragraph(f"Cage Type: {ct}")
        doc.add_paragraph(f"Cage Material: {cm}")
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button(
            label="📄 Download Specification Report",
            data=buffer,
            file_name="ABS_Bearing_Design_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# ----------------------------
# Module 2 – Tolerance & Fit
# ----------------------------
with tabs[1]:
    st.header("📏 Module 2: Tolerance & Fit Calculator")
    dia2 = st.number_input("Enter Bore Diameter (mm)", value=280.0, key="mod2_dia")
    tol_class = st.selectbox("Tolerance Class", ["Normal", "P6", "P5"], key="mod2_class")
    if st.button("Calculate Tolerances", key="btn_mod2"):
        u, l = find_tolerance(dia2, tol_class)
        if u is not None:
            st.success("✅ Tolerance Found:")
            st.write(f"**Upper Deviation:** +{u} µm")
            st.write(f"**Lower Deviation:** {l} µm")
            st.write(f"**Max Bore Diameter:** {dia2 + u/1000:.3f} mm")
            st.write(f"**Min Bore Diameter:** {dia2 + l/1000:.3f} mm")
        else:
            st.error("Not found in table.")

# ----------------------------
# Module 3 – Roller Profile Matching
# ----------------------------
with tabs[2]:
    st.header("📊 Module 3: Roller Profile Matching")
    ptype = st.selectbox("Profile Type", ["Logarithmic", "Crowned", "Flat"], key="mod3_type")
    pr_dia = st.number_input("Roller Diameter (mm)", value=40.0, key="mod3_dia")
    if st.button("Check Max Deviation", key="btn_mod3"):
        dev = get_max_deviation(ptype, pr_dia)
        if dev is not None:
            st.success(f"✅ Max Deviation for {ptype} with {pr_dia} mm: {dev} µm")
        else:
            st.error("No matching record found.")

# ----------------------------
# Module 4 – Material Selector
# ----------------------------
with tabs[3]:
    st.header("⚙️ Module 4: Material & Heat Treatment Selector")
    rd4 = st.number_input("Roller Diameter (mm)", value=35.0, key="mod4_roller")
    wt4 = st.number_input("Wall Thickness (mm)", value=20.0, key="mod4_wall")
    load4 = st.selectbox("Load Type", ["standard", "impact"], key="mod4_load")
    if st.button("Get Recommendation", key="btn_mod4"):
        steel4, ht4 = suggest_material_and_treatment_module3(rd4, wt4, load4)
        st.write(f"**Steel:** {steel4}")
        st.write(f"**Heat Treatment:** {ht4}")

# ----------------------------
# Module 5 – Clearance Checker
# ----------------------------
with tabs[4]:
    st.header("📐 Module 5: Clearance Class Checker")
    bd5 = st.number_input("Bore Diameter (mm)", value=250.0, key="mod5_bore")
    mt5 = st.selectbox("Mill Type", [None, "hot mill", "cold mill"], key="mod5_mill")
    if st.button("Check Clearance", key="btn_mod5"):
        cc5 = suggest_clearance(bd5, mt5)
        st.success(f"✅ Recommended Clearance Class: {cc5}")

# ----------------------------
# Module 6 – Final Compliance Validator
# ----------------------------
with tabs[5]:
    st.header("✅ Module 6: Final Compliance Validator")
    entered_class = st.selectbox("Selected Bearing Class", ["P5", "P6", "Normal"], key="mod6_class")
    entered_clearance = st.selectbox("Selected Clearance Class", ["C2", "Normal", "C3", "C4", "C5"], key="mod6_clearance")
    entered_steel = st.text_input("Chosen Steel Type", key="mod6_steel")
    entered_heat = st.text_input("Chosen Heat Treatment", key="mod6_heat")
    if st.button("Validate Configuration", key="btn_mod6"):
        if not entered_steel or not entered_heat:
            st.warning("⚠️ Please fill out all fields.")
        else:
            st.success("✅ Configuration entered. Please review manually or consult Mr. Wu for validation.")
