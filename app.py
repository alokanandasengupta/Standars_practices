import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import time
from datetime import datetime
import io
import hashlib
from typing import Dict, List, Any, Tuple, Optional
from openai import OpenAI
import PyPDF2
from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from PIL import Image

# Configuration
st.set_page_config(
    page_title="Film Production Master App",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .violation-critical {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    .violation-high {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    .violation-medium {
        background-color: #fffde7;
        border-left: 5px solid #ffeb3b;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    .violation-low {
        background-color: #f3e5f5;
        border-left: 5px solid #9c27b0;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    .user-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #007bff;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False

# Authentication functions
def check_email_domain(email: str) -> bool:
    """Check if email belongs to authorized domain"""
    authorized_domains = ['@hoichoi.tv', '@gmail.com', '@example.com', '@test.com']
    return any(email.lower().strip().endswith(domain) for domain in authorized_domains)

def authenticate_user():
    """Handle user authentication"""
    init_session_state()
    
    if not st.session_state.authenticated:
        st.markdown("""
        <div class="main-header">
            <h1>🎬 Film Production Master App</h1>
            <h3>Standards & Practices + Production Design</h3>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.subheader("🔐 Login Required")
                email = st.text_input("Email Address", placeholder="yourname@hoichoi.tv")
                password = st.text_input("Password", type="password")
                
                if st.button("Login", type="primary", use_container_width=True):
                    if email and password and check_email_domain(email):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.session_state.user_name = email.split('@')[0].replace('.', ' ').title()
                        st.session_state.is_admin = email in ['admin@hoichoi.tv', 'sp@hoichoi.tv']
                        st.rerun()
                    else:
                        st.error("❌ Access denied. Please use an authorized email address.")
        
        return False
    return True

# API Key Management
def get_api_key():
    """Get API key from session state or user input"""
    if 'api_key' in st.session_state and st.session_state.api_key:
        return st.session_state.api_key
    return None

def set_api_key(key: str):
    """Set API key in session state"""
    st.session_state.api_key = key

# File Processing Class
class ScriptProcessor:
    def __init__(self, api_key: str):
        """Initialize the processor with API key"""
        if not api_key:
            raise ValueError("API key is required")
        
        self.client = OpenAI(
            api_key=api_key, 
            base_url="https://api.deepseek.com/v1"
        )
    
    def extract_text_from_pdf(self, file_data: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            text = ""
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")

    def extract_text_from_docx(self, file_data: bytes) -> str:
        """Extract text from DOCX bytes"""
        try:
            doc = Document(io.BytesIO(file_data))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading DOCX: {str(e)}")

    def extract_text_from_file(self, file_data: bytes, filename: str) -> str:
        """Extract text from file based on extension"""
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_data)
        elif file_extension in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_data)
        elif file_extension == '.txt':
            return file_data.decode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def analyze_standards(self, text: str) -> Dict[str, Any]:
        """Analyze script for standards and practices violations"""
        if not text.strip():
            return {"error": "No text content found"}
        
        try:
            prompt = f"""Analyze this film script for content violations. Return JSON format only.

Check for:
- Violence (excessive, graphic content)
- Language (profanity, offensive terms)
- Nudity/Sexual content
- Drug use depictions
- Copyright issues

Return exactly this JSON structure:
{{
    "violations": [
        {{
            "violationType": "violence",
            "severity": "high",
            "violationText": "specific text from script",
            "explanation": "why this violates standards",
            "suggestedAction": "recommended changes",
            "pageNumber": 1
        }}
    ],
    "summary": {{
        "totalViolations": 2,
        "criticalCount": 0,
        "highCount": 1,
        "mediumCount": 1,
        "lowCount": 0
    }}
}}

Script content: {text[:8000]}"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a film standards and practices expert. Analyze scripts for content violations and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Extract JSON from markdown if present
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                    return json.loads(json_content)
                else:
                    return {"error": "Invalid JSON response from API"}
                    
        except Exception as e:
            return {"error": f"API call failed: {str(e)}"}

    def analyze_production(self, text: str) -> Dict[str, Any]:
        """Analyze script for production elements"""
        if not text.strip():
            return {"error": "No text content found"}
        
        try:
            prompt = f"""Extract production elements from this film script. Return JSON format only.

Identify:
- Locations (sets, exteriors, interiors)
- Scenes and their details
- Props and set pieces
- Time of day requirements

Return exactly this JSON structure:
{{
    "location_breakdown": [
        {{
            "location_name": "Office Building",
            "location_type": "Interior",
            "scenes_in_location": [
                {{
                    "scene_number": 1,
                    "scene_heading": "INT. OFFICE - DAY",
                    "time_of_day": "DAY",
                    "brief_description": "Character walks into office",
                    "props_in_scene": ["desk", "computer", "coffee mug"]
                }}
            ]
        }}
    ],
    "unique_props": ["desk", "computer", "coffee mug"],
    "summary": {{
        "total_locations": 3,
        "total_scenes": 8,
        "total_props": 15
    }}
}}

Script content: {text[:8000]}"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a film production coordinator. Extract production elements from scripts and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Extract JSON from markdown if present
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                    return json.loads(json_content)
                else:
                    return {"error": "Invalid JSON response from API"}
                    
        except Exception as e:
            return {"error": f"API call failed: {str(e)}"}

# Report Generation Functions
def generate_standards_excel_report(violations: List[Dict]) -> bytes:
    """Generate Excel report for standards violations"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Standards Report"
    
    # Headers
    headers = ["Type", "Severity", "Page", "Violation Text", "Explanation", "Suggested Action"]
    ws.append(headers)
    
    # Style headers
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    
    # Add data
    for violation in violations:
        ws.append([
            violation.get('violationType', ''),
            violation.get('severity', ''),
            violation.get('pageNumber', ''),
            violation.get('violationText', '')[:100] + "..." if len(violation.get('violationText', '')) > 100 else violation.get('violationText', ''),
            violation.get('explanation', ''),
            violation.get('suggestedAction', '')
        ])
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def generate_production_excel_report(production_data: Dict) -> bytes:
    """Generate Excel report for production breakdown"""
    wb = Workbook()
    
    # Summary sheet
    ws_summary = wb.active
    ws_summary.title = "Summary"
    
    summary = production_data.get('summary', {})
    ws_summary.append(["Production Summary"])
    ws_summary.append(["Total Locations", summary.get('total_locations', 0)])
    ws_summary.append(["Total Scenes", summary.get('total_scenes', 0)])
    ws_summary.append(["Total Props", summary.get('total_props', 0)])
    
    # Locations sheet
    ws_locations = wb.create_sheet("Locations")
    ws_locations.append(["Location", "Type", "Scene Count"])
    
    for location in production_data.get('location_breakdown', []):
        ws_locations.append([
            location.get('location_name', ''),
            location.get('location_type', ''),
            len(location.get('scenes_in_location', []))
        ])
    
    # Props sheet
    ws_props = wb.create_sheet("Props")
    ws_props.append(["Prop Name"])
    
    for prop in production_data.get('unique_props', []):
        ws_props.append([prop])
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# Tab Functions
def tab_upload_script():
    """Upload and process script tab"""
    st.header("📤 Upload Script")
    st.markdown("Upload your script file for analysis")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a script file",
        type=['pdf', 'docx', 'txt'],
        help="Supported formats: PDF, DOCX, TXT"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        # Check API key
        api_key = get_api_key()
        if not api_key:
            st.error("❌ Please configure your DeepSeek API key in the sidebar")
            return
        
        # Process button
        if st.button("🔍 Analyze Script", type="primary"):
            try:
                processor = ScriptProcessor(api_key)
                
                with st.spinner("Extracting text from file..."):
                    text = processor.extract_text_from_file(uploaded_file.getvalue(), uploaded_file.name)
                
                if not text.strip():
                    st.error("❌ No text content found in the file")
                    return
                
                st.info(f"📄 Extracted {len(text)} characters from script")
                
                # Analyze for standards
                with st.spinner("Analyzing for standards violations..."):
                    standards_result = processor.analyze_standards(text)
                
                # Analyze for production
                with st.spinner("Analyzing for production elements..."):
                    production_result = processor.analyze_production(text)
                
                # Save results
                st.session_state.standards_results = standards_result
                st.session_state.production_results = production_result
                st.session_state.current_filename = uploaded_file.name
                st.session_state.script_text = text[:1000] + "..." if len(text) > 1000 else text
                
                st.success("🎉 Analysis complete! Check the other tabs for results.")
                
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")

def tab_standards_results():
    """Display standards and practices results"""
    if 'standards_results' not in st.session_state:
        st.info("ℹ️ Upload and analyze a script first to see Standards & Practices results")
        return
    
    st.header("📝 Standards & Practices Review")
    
    results = st.session_state.standards_results
    
    if 'error' in results:
        st.error(f"❌ Analysis error: {results['error']}")
        return
    
    violations = results.get('violations', [])
    summary = results.get('summary', {})
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Violations", summary.get('totalViolations', len(violations)))
    with col2:
        st.metric("Critical", summary.get('criticalCount', 0))
    with col3:
        st.metric("High", summary.get('highCount', 0))
    with col4:
        st.metric("Medium", summary.get('mediumCount', 0))
    
    # Display violations
    if violations:
        st.subheader("🚨 Violations Found")
        for i, violation in enumerate(violations, 1):
            severity = violation.get('severity', 'low')
            violation_class = f"violation-{severity}"
            
            st.markdown(f"""
            <div class="{violation_class}">
                <h4>{i}. {violation.get('violationType', 'Unknown').title()} Violation</h4>
                <p><strong>Severity:</strong> {severity.upper()}</p>
                <p><strong>Page:</strong> {violation.get('pageNumber', 'N/A')}</p>
                <p><strong>Content:</strong> "{violation.get('violationText', 'N/A')}"</p>
                <p><strong>Issue:</strong> {violation.get('explanation', 'N/A')}</p>
                <p><strong>Recommendation:</strong> {violation.get('suggestedAction', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No violations found!")
    
    # Download report
    if violations:
        st.subheader("📥 Download Report")
        if st.button("Generate Excel Report"):
            excel_data = generate_standards_excel_report(violations)
            st.download_button(
                label="📊 Download Standards Report",
                data=excel_data,
                file_name=f"{st.session_state.current_filename}_standards_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def tab_production_results():
    """Display production design results"""
    if 'production_results' not in st.session_state:
        st.info("ℹ️ Upload and analyze a script first to see Production Design results")
        return
    
    st.header("🎬 Production Design Breakdown")
    
    results = st.session_state.production_results
    
    if 'error' in results:
        st.error(f"❌ Analysis error: {results['error']}")
        return
    
    locations = results.get('location_breakdown', [])
    props = results.get('unique_props', [])
    summary = results.get('summary', {})
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Locations", summary.get('total_locations', len(locations)))
    with col2:
        st.metric("Total Scenes", summary.get('total_scenes', 0))
    with col3:
        st.metric("Total Props", summary.get('total_props', len(props)))
    
    # Location breakdown
    if locations:
        st.subheader("📍 Location Breakdown")
        for location in locations:
            with st.expander(f"📍 {location.get('location_name', 'Unknown Location')} ({len(location.get('scenes_in_location', []))} scenes)"):
                for scene in location.get('scenes_in_location', []):
                    st.write(f"**Scene {scene.get('scene_number', 'N/A')}:** {scene.get('scene_heading', 'N/A')}")
                    st.write(f"*Time:* {scene.get('time_of_day', 'N/A')}")
                    st.write(f"*Description:* {scene.get('brief_description', 'N/A')}")
                    if scene.get('props_in_scene'):
                        st.write(f"*Props:* {', '.join(scene.get('props_in_scene', []))}")
                    st.divider()
    
    # Props list
    if props:
        st.subheader("🎭 Master Props List")
        props_df = pd.DataFrame({
            'Prop Name': props,
            'Index': range(1, len(props) + 1)
        })
        st.dataframe(props_df, use_container_width=True)
    
    # Download report
    if locations or props:
        st.subheader("📥 Download Report")
        if st.button("Generate Production Report"):
            excel_data = generate_production_excel_report(results)
            st.download_button(
                label="📊 Download Production Report",
                data=excel_data,
                file_name=f"{st.session_state.current_filename}_production_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# Main Application
def main():
    """Main application function"""
    # Check authentication
    if not authenticate_user():
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div class="user-info">
            <h3>👤 User Information</h3>
            <p><b>Name:</b> {st.session_state.get('user_name', 'Unknown')}</p>
            <p><b>Email:</b> {st.session_state.get('user_email', 'unknown')}</p>
            <p><b>Role:</b> {'Admin' if st.session_state.get('is_admin', False) else 'User'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # API Key Configuration
        st.subheader("🔑 API Configuration")
        current_key = get_api_key()
        
        if current_key:
            st.success("✅ DeepSeek API Key: Configured")
            if st.button("🔄 Change API Key"):
                del st.session_state.api_key
                st.rerun()
        else:
            st.warning("⚠️ DeepSeek API Key: Not configured")
            api_input = st.text_input(
                "Enter DeepSeek API Key", 
                type="password", 
                help="Required for script analysis"
            )
            if api_input:
                set_api_key(api_input)
                st.success("✅ API Key configured!")
                st.rerun()
        
        st.divider()
        
        # Logout button
        if st.button("🚪 Logout", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>🎬 Film Production Master App</h1>
        <p>Standards & Practices + Production Design Analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload Script", "📝 Standards & Practices", "🎬 Production Design"])
    
    with tab1:
        tab_upload_script()
    
    with tab2:
        tab_standards_results()
    
    with tab3:
        tab_production_results()

if __name__ == "__main__":
    main()
