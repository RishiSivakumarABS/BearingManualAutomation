import streamlit as st
from docx import Document
from datetime import datetime
import pandas as pd
import io

st.set_page_config(page_title="ABS Bearing Design Tool", layout="centered")

st.title("🛠️ ABS Bearing Design Automation Tool")
st.markdown("This tool assists in selecting bearing specifications and calculating tolerance deviations based on ABS internal standards.")

# Load Tolerance Data
@st.cache_data
def load_tolerance_tables():
    df_normal = pd.read_excel("Table1_Normal_Tolerances.xlsx")
    df_p6 = pd.read_excel("Table2_P6_Tolerances.xlsx")
    df_p5 = pd.read_excel("Table3_P5_Tolerances.xlsx")
    return df_normal, df_p6, df_p5

df_normal, df_p6, df_p5 = load_tolerance_tables()

# Mapping tables
class_tables = {
    'Normal': df_normal,
    'P6': df_p6,
    'P5': df_p5
}

# Helper function for Module 2
def find_tolerance(bore_diameter, tolerance_class):
    df = class_tables.get(tolerance_class)
    if df is None:
        return None, None
    for _, row in df.iterrows():
        if row['Min Diameter (mm)'] < bore_diameter <= row['Max Diameter (mm)']:
            return row['Upper Deviation (µm)'], row['Lower Deviation (µm)']
    return None, None

# --- Tabs for Module 1 and Module 2 ---
tab1, tab2 = st.tabs(["Module 1 – Smart Specification Selector", "Module 2 – Tolerance & Fit Calculator"])

# --- Module 1 ---
with tab1:
    st.header("🔧 Module 1: Smart Specification Selector")
    
    bore_diameter = st.number_input("Bore Diameter (mm)", value=250)
    wall_thickness = st.number_input("Effective Wall Thickness (mm)", value=20)
    roller_diameter = st.number_input("Roller Diameter (mm)", value=35)
    
    application_type = st.selectbox("Application Type", ["standard", "precision", "high load"])
    speed_rpm = st.number_input("Operating Speed (RPM)", value=300)
    mill_type = st.selectbox("Mill Type (optional)", [None, "hot mill", "cold mill"])
    load_type = st.selectbox("Load Type", ["standard", "impact"])
    
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
    
    if st.button("Generate Specification Recommendation"):
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
        st.success("Module 1 recommendations generated successfully!")

        # Generate report
        doc = Document()
        doc.add_heading('ABS Bearing Design Report', level=1)
        doc.add_paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        doc.add_heading('Module 1 – Smart Specification Selector', level=2)
        doc.add_paragraph(f"Bore Diameter: {bore_diameter} mm")
        doc.add_paragraph(f"Bearing Class: {bearing_class}")
        doc.add_paragraph(f"Clearance Class: {clearance}")
        doc.add_paragraph(f"Steel Type: {steel}")
        doc.add_paragraph(f"Heat Treatment: {heat_treatment}")
        doc.add_paragraph(f"Cage Type: {cage_type}")
        doc.add_paragraph(f"Cage Material: {cage_material}")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="📄 Download Report (DOCX)",
            data=buffer,
            file_name="ABS_Bearing_Design_Report_Module1.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# --- Module 2 ---
with tab2:
    st.header("📏 Module 2: Tolerance & Fit Calculator")
    
    bore_dia_mod2 = st.number_input("Enter Bore Diameter for Tolerance Calculation (mm)", min_value=0.0, step=0.01, value=280.0)
    tolerance_class_mod2 = st.selectbox("Select Tolerance Class", ["Normal", "P6", "P5"])
    
    if st.button("Calculate Tolerances and Bore Dimensions"):
        upper_dev, lower_dev = find_tolerance(bore_dia_mod2, tolerance_class_mod2)
        
        if upper_dev is not None and lower_dev is not None:
            # Calculate Max and Min Bore
            max_bore = bore_dia_mod2 + (upper_dev / 1000)  # µm to mm
            min_bore = bore_dia_mod2 + (lower_dev / 1000)
            
            st.success("✅ Tolerance and Dimensions Found:")
            st.write(f"**Upper Deviation:** +{upper_dev} µm")
            st.write(f"**Lower Deviation:** {lower_dev} µm")
            st.write(f"**Maximum Bore Diameter:** {max_bore:.3f} mm")
            st.write(f"**Minimum Bore Diameter:** {min_bore:.3f} mm")
        else:
            st.error("⚠️ Bore diameter not found in the selected tolerance class table. Please verify input.")

