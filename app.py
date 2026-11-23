import streamlit as st
import pandas as pd
import joblib
import numpy as np
import os
from pathlib import Path
import plotly.express as px
import re
# OCR & PDF tools
import pytesseract
from PIL import Image
import pdfplumber
from pdf2image import convert_from_path

# Backend API
import requests
import json
import time

# Optional: Lottie animations
try:
    from streamlit_lottie import st_lottie
    HAS_LOTTIE = True
except Exception:
    HAS_LOTTIE = False

# ✅ Point pytesseract to your tesseract.exe
# Check if Tesseract exists at the default location, otherwise try to find it
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
]

tesseract_found = False
for path in tesseract_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        tesseract_found = True
        break

if not tesseract_found:
    # Try to use system PATH if tesseract is installed
    try:
        import shutil
        tesseract_cmd = shutil.which('tesseract')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            tesseract_found = True
    except Exception:
        pass


# =============================
# Backend API Configuration
# =============================
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5000')
PREFS_FILE = "user_prefs.json"

# =============================
# Authentication Functions
# =============================
def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'reduced_motion' not in st.session_state:
        st.session_state.reduced_motion = False
    if 'compact_density' not in st.session_state:
        st.session_state.compact_density = True
    if 'show_csv_wizard' not in st.session_state:
        st.session_state.show_csv_wizard = False

# Small utility: toast with graceful fallback
def notify(message: str, kind: str = "info") -> None:
    if hasattr(st, "toast"):
        st.toast(message, icon="✅" if kind == "success" else ("⚠️" if kind == "warning" else "ℹ️"))
    else:
        if kind == "success":
            st.success(message)
        elif kind == "warning":
            st.warning(message)
        elif kind == "error":
            st.error(message)
        else:
            st.info(message)

# Optional Lottie renderer
def render_lottie(lottie_json: dict | None, height: int = 140, key: str | None = None) -> None:
    if not HAS_LOTTIE or st.session_state.reduced_motion or not lottie_json:
        return
    try:
        st_lottie(lottie_json, height=height, key=key, loop=True, speed=0.8)
    except Exception:
        pass

# Simple skeleton placeholders
def show_skeleton_metrics(columns: int = 3):
    cols = st.columns(columns)
    for c in cols:
        with c:
            st.markdown(
                """
                <div class="skeleton-card">
                  <div class="skeleton skeleton-line" style="width: 50%; height: 14px;"></div>
                  <div class="skeleton skeleton-line" style="width: 80%; height: 26px; margin-top: 10px;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# Animated metric counter
def animated_metric(label: str, target_value: int, duration_ms: int = 600) -> None:
    container = st.empty()
    steps = max(1, int(duration_ms / 30))
    for i in range(steps + 1):
        val = int(target_value * (i / steps))
        container.metric(label, val)
        time.sleep(0.03)

# Empty-state illustration
def render_empty_state(title: str, caption: str) -> None:
    st.markdown(
        f"""
        <div style="border: 1px dashed rgba(46,125,50,0.35); padding: 1.25rem; border-radius: 12px;
                    background: linear-gradient(180deg, rgba(232,245,233,0.35), rgba(200,230,201,0.2));">
          <div style="display:flex; align-items:center; gap:16px;">
            <svg width="60" height="60" viewBox="0 0 24 24" fill="none">
              <path d="M12 21c4.97 0 9-3.58 9-8s-4.03-8-9-8S3 8.58 3 13c0 2.27 1.02 4.32 2.68 5.82l-1.04 3.06 3.2-1.74C9.03 20.63 10.47 21 12 21z"
                    fill="rgba(76,175,80,0.25)"></path>
              <path d="M11 14h2v2h-2v-2zm0-7h2v6h-2V7z" fill="rgba(46,125,50,0.8)"></path>
            </svg>
            <div>
              <div style="font-weight:700; color:#2E7D32; font-size:1.05rem;">{title}</div>
              <div style="color:#4f4f4f; margin-top:4px;">{caption}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# CSV upload wizard scaffold
def csv_upload_wizard() -> None:
    st.markdown("#### CSV Upload Wizard")
    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="wizard_csv")
    if not uploaded:
        st.info("Upload a CSV to begin mapping fields.")
        return
    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return

    st.markdown("Select ID and symptom columns to use for batch analysis.")
    cols = list(df.columns)
    id_col = st.selectbox("Patient ID column (optional)", ["<none>"] + cols, index=0, key="wizard_id_col")
    symptom_cols = st.multiselect("Symptom columns", cols, default=[c for c in cols if "symptom" in c.lower()])

    if not symptom_cols:
        st.warning("Pick at least one symptom column.")
        return

    preview_cols = ([id_col] if id_col != "<none>" else []) + symptom_cols
    st.markdown("Preview")
    st.dataframe(df[preview_cols].head(10), use_container_width=True)

    if st.button("Use this mapping", use_container_width=True):
        notify("Mapping saved for this session.", "success")
        st.session_state["csv_wizard_mapping"] = {"id_col": None if id_col == "<none>" else id_col, "symptom_cols": symptom_cols}

def login_user(username_or_email, password):
    """Login user via API (accepts username or email)"""
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/login',
            json={'username': username_or_email, 'password': password},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.token = data['token']
            st.session_state.username = data['username']
            st.session_state.user_id = data['user_id']
            return True, "Login successful!"
        else:
            error_msg = response.json().get('error', 'Login failed')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def request_password_reset(email):
    """Request password reset OTP"""
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/forgot-password',
            json={'email': email},
            timeout=5
        )
        if response.status_code == 200:
            return True, response.json().get('message', 'Reset code sent successfully')
        else:
            error_msg = response.json().get('error', 'Failed to send reset code')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def reset_password_with_otp(email, otp, new_password):
    """Reset password using OTP"""
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/reset-password',
            json={'email': email, 'otp': otp, 'new_password': new_password},
            timeout=5
        )
        if response.status_code == 200:
            return True, response.json().get('message', 'Password reset successfully')
        else:
            error_msg = response.json().get('error', 'Password reset failed')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def send_otp_to_email(email):
    """Send OTP to email via API"""
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/send-otp',
            json={'email': email},
            timeout=5
        )
        if response.status_code == 200:
            return True, response.json().get('message', 'OTP sent successfully')
        else:
            error_msg = response.json().get('error', 'Failed to send OTP')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def verify_otp_code(email, otp):
    """Verify OTP code via API"""
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/verify-otp',
            json={'email': email, 'otp': otp},
            timeout=5
        )
        if response.status_code == 200:
            return True, response.json().get('message', 'OTP verified successfully')
        else:
            error_msg = response.json().get('error', 'OTP verification failed')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def register_user(username, email, password, otp):
    """Register new user via API (with OTP)"""
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/register',
            json={'username': username, 'email': email, 'password': password, 'otp': otp},
            timeout=5
        )
        if response.status_code == 201:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.token = data['token']
            st.session_state.username = data['username']
            st.session_state.user_id = data['user_id']
            return True, "Registration successful!"
        else:
            error_msg = response.json().get('error', 'Registration failed')
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def logout_user():
    """Logout user via API"""
    if st.session_state.token:
        try:
            headers = {'Authorization': f'Bearer {st.session_state.token}'}
            requests.post(f'{API_BASE_URL}/api/logout', headers=headers, timeout=5)
        except:
            pass  # Continue logout even if API call fails
    
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.rerun()

def verify_token():
    """Verify if current token is valid"""
    if not st.session_state.token:
        return False
    
    try:
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.post(f'{API_BASE_URL}/api/verify', headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                return True
    except:
        pass
    
    # Token invalid, logout
    logout_user()
    return False

def save_patient_record_to_backend(patient_info, symptoms, results):
    """Save patient record to backend"""
    if not st.session_state.authenticated or not st.session_state.token:
        return
    
    try:
        top_disease = results.iloc[0]["Disease"]
        top_prob = results.iloc[0]["Probability"]
        
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        data = {
            'patient_name': patient_info.get('name', 'Unknown'),
            'age': patient_info.get('age'),
            'gender': patient_info.get('gender'),
            'medical_history': patient_info.get('medical_history', ''),
            'symptoms': ', '.join(symptoms),
            'predicted_disease': top_disease,
            'probability': float(top_prob)
        }
        requests.post(
            f'{API_BASE_URL}/api/patient-records',
            json=data,
            headers=headers,
            timeout=5
        )
    except:
        pass  # Fail silently, local CSV backup will still work

def get_api_headers():
    """Get API headers with authentication token"""
    if st.session_state.token:
        return {'Authorization': f'Bearer {st.session_state.token}'}
    return {}

def delete_all_backend_records():
    """Delete all patient records from backend database"""
    try:
        headers = get_api_headers()
        if not headers:
            return False, "Not authenticated. Please login first."
        
        # Fetch existing records
        list_resp = requests.get(f'{API_BASE_URL}/api/patient-records', headers=headers, timeout=8)
        if list_resp.status_code != 200:
            try:
                err = list_resp.json().get('error', list_resp.text)
            except Exception:
                err = list_resp.text
            return False, f"Failed to fetch records: {err}"
        
        records = list_resp.json().get('records', [])
        if not records:
            return True, "No backend records to delete"
        
        deleted = 0
        for rec in records:
            rec_id = rec.get('id')
            if rec_id is None:
                continue
            del_resp = requests.delete(f'{API_BASE_URL}/api/patient-records/{rec_id}', headers=headers, timeout=5)
            if del_resp.status_code == 200:
                deleted += 1
        
        if deleted == 0:
            return False, "Failed to delete records"
        return True, f"Successfully deleted {deleted} record(s) from backend database"
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"

def delete_local_csv():
    """Delete local patient history CSV file"""
    try:
        history_file = "patient_history.csv"
        if os.path.exists(history_file):
            os.remove(history_file)
            return True, "Successfully deleted local CSV file"
        else:
            return False, "Local CSV file does not exist"
    except Exception as e:
        return False, f"Error deleting CSV: {str(e)}"

# =============================
# OCR Helper Functions
# =============================
def test_tesseract_accessibility():
    """Test if Tesseract can be executed. Returns (success, error_message)."""
    import subprocess
    
    tesseract_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', None)
    if not tesseract_cmd or not os.path.exists(tesseract_cmd):
        return False, "Tesseract executable not found"
    
    try:
        # Try to run tesseract --version to test accessibility
        result = subprocess.run(
            [tesseract_cmd, '--version'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0:
            return True, None
        else:
            return False, f"Tesseract returned error code {result.returncode}"
    except PermissionError as e:
        return False, f"Permission denied: {str(e)}"
    except Exception as e:
        return False, f"Error testing Tesseract: {str(e)}"


def run_tesseract_with_subprocess(image_path):
    """Run Tesseract OCR using subprocess directly as a workaround for permission issues."""
    import subprocess
    import tempfile
    
    tesseract_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', None)
    if not tesseract_cmd:
        raise FileNotFoundError("Tesseract executable not configured")
    
    temp_dir = tempfile.gettempdir()
    # Tesseract creates output file with extension, so we need base name without extension
    output_base = tempfile.mktemp(dir=temp_dir, suffix='')
    output_path = output_base + '.txt'
    
    try:
        # Run tesseract directly with subprocess
        # Format: tesseract input_image output_base txt
        # Tesseract will create output_base.txt
        cmd = [tesseract_cmd, image_path, output_base, 'txt']
        
        # Set environment variables
        env = os.environ.copy()
        env['TMP'] = temp_dir
        env['TEMP'] = temp_dir
        
        # Try with different subprocess flags
        creation_flags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            creationflags=creation_flags
        )
        
        if result.returncode == 0:
            # Read the output file (Tesseract creates it with .txt extension)
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                return text
            else:
                raise Exception(f"Tesseract output file not found at {output_path}")
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise Exception(f"Tesseract failed with code {result.returncode}: {error_msg}")
    finally:
        # Clean up output file
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except:
                pass


def extract_text_from_pdf(pdf_file):
    """Extract text from PDF (works for both text-PDF and scanned)."""
    import tempfile
    
    text = ""

    try:
        # Try text-based extraction
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except:
        pass

    # If no text found → use OCR on images
    if not text.strip():
        try:
            # Set temp directory to system temp (outside OneDrive) to avoid permission issues
            temp_dir = tempfile.gettempdir()
            original_tmp = os.environ.get('TMP', None)
            original_temp = os.environ.get('TEMP', None)
            
            try:
                os.environ['TMP'] = temp_dir
                os.environ['TEMP'] = temp_dir
                
                images = convert_from_path(pdf_file)
                for img in images:
                    try:
                        text += pytesseract.image_to_string(img)
                    except PermissionError as e:
                        st.warning(f"⚠️ OCR permission error on PDF page. Error: {str(e)}")
                        # Continue with other pages
                        continue
                    except Exception as e:
                        st.warning(f"⚠️ OCR error on PDF page: {str(e)}")
                        continue
            finally:
                # Restore original environment variables
                if original_tmp is not None:
                    os.environ['TMP'] = original_tmp
                elif 'TMP' in os.environ:
                    del os.environ['TMP']
                    
                if original_temp is not None:
                    os.environ['TEMP'] = original_temp
                elif 'TEMP' in os.environ:
                    del os.environ['TEMP']
        except Exception as e:
            st.error(f"❌ Error processing PDF with OCR: {str(e)}")

    return text


def extract_text_from_image(image_file):
    """Extract text from uploaded image."""
    import tempfile
    
    try:
        img = Image.open(image_file)
        
        # Save image to a temporary file outside OneDrive to avoid sync issues
        # Use system temp directory which typically has proper permissions
        temp_dir = tempfile.gettempdir()
        temp_image_path = None
        
        # Store original TMP/TEMP to restore later
        original_tmp = os.environ.get('TMP', None)
        original_temp = os.environ.get('TEMP', None)
        
        try:
            # Set temp directory to system temp (outside OneDrive)
            os.environ['TMP'] = temp_dir
            os.environ['TEMP'] = temp_dir
            
            # Create a temporary file with proper permissions
            with tempfile.NamedTemporaryFile(dir=temp_dir, suffix='.png', delete=False) as temp_file:
                temp_image_path = temp_file.name
                img.save(temp_image_path, 'PNG')
            
            # First, test if Tesseract is accessible
            tesseract_accessible, test_error = test_tesseract_accessibility()
            if not tesseract_accessible:
                st.warning(f"⚠️ Tesseract accessibility test failed: {test_error}")
                st.info("Attempting workaround using direct subprocess call...")
            
            # Check if Tesseract is accessible before attempting OCR
            try:
                # Use the temp file path for OCR to avoid OneDrive sync issues
                text = pytesseract.image_to_string(temp_image_path)
                return text
            except PermissionError as e:
                # Try alternative 1: use image object directly (may work if file handle is the issue)
                try:
                    text = pytesseract.image_to_string(img)
                    return text
                except Exception as e2:
                    # Try alternative 2: use subprocess directly as workaround
                    try:
                        st.info("🔄 Trying alternative method: direct subprocess call...")
                        text = run_tesseract_with_subprocess(temp_image_path)
                        if text:
                            st.success("✅ OCR succeeded using alternative method!")
                            return text
                        else:
                            raise Exception("Subprocess method returned empty text")
                    except Exception as e3:
                        # All methods failed - show comprehensive error message
                        tesseract_path = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'Not configured')
                        st.error(f"❌ Permission Error: Cannot access Tesseract OCR.\n\n"
                                f"**Tesseract Path:** {tesseract_path}\n\n"
                                f"**Error Details:**\n"
                                f"- Pytesseract method: {str(e)}\n"
                                f"- Image object method: {str(e2)}\n"
                                f"- Subprocess method: {str(e3)}\n\n"
                                f"**Possible Solutions:**\n"
                                f"1. **Run as Administrator**: Right-click PowerShell/Command Prompt → 'Run as Administrator', then run your app\n"
                                f"2. **Windows Defender Exclusions**:\n"
                                f"   - Open Windows Security → Virus & threat protection\n"
                                f"   - Manage settings → Exclusions → Add or remove exclusions\n"
                                f"   - Add folder: `C:\\Program Files\\Tesseract-OCR`\n"
                                f"3. **Antivirus Settings**: Check if your antivirus is blocking subprocess execution\n"
                                f"4. **Move Project**: Try moving the project outside OneDrive folder (e.g., `C:\\Projects\\puri02`)\n"
                                f"5. **Reinstall Tesseract**: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
                                f"6. **Check Permissions**: Ensure you have read/execute permissions on Tesseract folder")
                        return ""
            except FileNotFoundError:
                st.error("❌ Tesseract OCR not found. Please install Tesseract-OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
                return ""
            except Exception as e:
                st.error(f"❌ OCR Error: {str(e)}")
                return ""
        finally:
            # Restore original environment variables
            if original_tmp is not None:
                os.environ['TMP'] = original_tmp
            elif 'TMP' in os.environ:
                del os.environ['TMP']
                
            if original_temp is not None:
                os.environ['TEMP'] = original_temp
            elif 'TEMP' in os.environ:
                del os.environ['TEMP']
            
            # Clean up temporary file
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.unlink(temp_image_path)
                except:
                    pass
                    
    except Exception as e:
        st.error(f"❌ Error opening image: {str(e)}")
        return ""

# PDF report packages
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# =============================
# Load Model & Encoder
# =============================
root = Path(__file__).parent
model_path = root / "models" / "symptom_disease_model.joblib"
encoder_path = root / "models" / "symptom_encoder.joblib"
diabetes_model_path = root / "models" / "diabetes_model.joblib"

model = joblib.load(model_path)
encoder = joblib.load(encoder_path)
diabetes_model = joblib.load(diabetes_model_path)

# Symptom list
symptom_list = encoder.classes_
# Symptom list
symptom_list = encoder.classes_

# =============================
# Symptom Synonyms Mapping
# (Place this here, so it's defined before any tab uses it)
# =============================
# -----------------------------
# Extended Symptom Synonyms Dictionary
# -----------------------------
SYMPTOM_SYNONYMS = {
    "fever": ["fever", "high temperature", "pyrexia", "raised body temp", "temperature"],
    "cough": ["cough", "dry cough", "persistent cough", "whooping cough"],
    "headache": ["headache", "migraine", "head pain", "pressure in head"],
    "fatigue": ["fatigue", "tiredness", "weakness", "exhaustion", "lethargy"],
    "nausea": ["nausea", "vomiting", "queasiness", "feeling sick"],
    "chest pain": ["chest pain", "chest discomfort", "tightness in chest", "angina"],
    "shortness of breath": [
        "shortness of breath", "breathlessness", "difficulty breathing", "dyspnea"
    ],
    "sore throat": ["sore throat", "throat pain", "throat discomfort", "pharyngitis"],
    "diarrhea": ["diarrhea", "loose stools", "frequent bowel movement", "watery stools"],
    "constipation": ["constipation", "hard stools", "difficulty passing stool"],
    "dizziness": ["dizziness", "lightheadedness", "vertigo", "giddiness"],
    "abdominal pain": ["abdominal pain", "stomach pain", "belly ache", "gastric pain"],
    "loss of appetite": ["loss of appetite", "poor appetite", "no desire to eat"],
    "joint pain": ["joint pain", "arthritis", "aching joints", "joint stiffness"],
    "back pain": ["back pain", "lower back pain", "spinal pain"],
    "rash": ["rash", "skin eruption", "skin spots", "dermatitis"],
    "weight loss": ["weight loss", "unintentional weight loss", "losing weight", "cachexia"],
    "weight gain": ["weight gain", "obesity", "overweight"],
    "anemia": ["anemia", "low hemoglobin", "pale skin", "iron deficiency"],
    "swelling": ["swelling", "edema", "inflammation", "fluid retention", "lump", "mass", "tumor"],
    "palpitations": ["palpitations", "irregular heartbeat", "rapid heartbeat"],
    "blurred vision": ["blurred vision", "loss of vision", "dim vision"],
    "chills": ["chills", "shivering", "rigors"],
    "night sweats": ["night sweats", "sweating at night"],
    "anxiety": ["anxiety", "nervousness", "restlessness"],
    "depression": ["depression", "sadness", "low mood"],
    "confusion": ["confusion", "disorientation", "mental fog"],
    "runny nose": ["runny nose", "nasal discharge", "rhinitis"],
    "sneezing": ["sneezing", "nasal irritation"],
    "itching": ["itching", "pruritus", "skin irritation"],
    "yellowing of eyes": ["yellowing of eyes", "jaundice", "yellow sclera"],
    "burning urination": ["burning urination", "painful urination", "dysuria"],
    "increased urination": ["increased urination", "frequent urination", "polyuria"],
    "thirst": ["thirst", "excessive thirst", "polydipsia"],
    "loss of consciousness": ["loss of consciousness", "fainting", "blackout"],
    "seizures": ["seizures", "fits", "convulsions"],
    "swollen lymph nodes": ["swollen lymph nodes", "enlarged glands", "lymphadenopathy"],
    "bleeding gums": ["bleeding gums", "gum bleeding", "gingival bleeding"],
    "mouth ulcers": ["mouth ulcers", "canker sores", "oral ulcers"],
    "hair loss": ["hair loss", "alopecia", "hair thinning"],
    "cold hands and feet": ["cold hands and feet", "poor circulation"],
    "excessive sweating": ["excessive sweating", "hyperhidrosis"],
    "hearing loss": ["hearing loss", "deafness", "reduced hearing"],
    "ear pain": ["ear pain", "earache", "otalgia"],
    "eye pain": ["eye pain", "ocular pain"],
    "insomnia": ["insomnia", "sleeplessness", "trouble sleeping"],
    "swollen ankles": ["swollen ankles", "ankle edema"],
    "bleeding": ["bleeding", "hemorrhage", "blood loss"],
    "weakness": ["weakness", "lack of strength", "frailty"],
    "cold": ["cold", "common cold", "flu-like symptoms"]
}

# Context-driven keyword hints sourced from common laboratory phrasing.
REPORT_KEYWORD_HINTS = [
    {
        "label": "Possible germ cell tumor involvement",
        "keywords": ["germ cell tumor", "germ cell tumours", "germ cell tumors"],
        "symptoms": ["abdominal pain", "swelling", "fatigue"],
        "diseases": ["Germ Cell Tumor"]
    },
    {
        "label": "Gestational trophoblastic disease references",
        "keywords": ["gestational trophoblastic"],
        "symptoms": ["bleeding", "nausea", "weakness"],
        "diseases": ["Gestational Trophoblastic Disease"]
    },
    {
        "label": "Testicular tumor context",
        "keywords": ["testicular tumor", "testicular tumours", "testicular tumors"],
        "symptoms": ["swelling", "weight loss", "fatigue"],
        "diseases": ["Testicular Cancer"]
    },
    {
        "label": "Ovarian involvement mentioned",
        "keywords": ["ovarian germ cell", "ovary carcinoma", "ovarian germ cell tumor"],
        "symptoms": ["abdominal pain", "swelling", "nausea"],
        "diseases": ["Ovarian Cancer"]
    },
    {
        "label": "Melanoma / carcinoma references",
        "keywords": ["melanoma", "carcinoma", "carcinomas"],
        "symptoms": ["rash", "weight loss", "fatigue"],
        "diseases": ["Melanoma", "Carcinoma"]
    },
    {
        "label": "Chronic liver disease context",
        "keywords": ["cirrhosis", "hepatocellular", "liver failure"],
        "symptoms": ["abdominal pain", "nausea", "fatigue", "swelling"],
        "diseases": ["Cirrhosis", "Hepatocellular Carcinoma"]
    },
    {
        "label": "Inflammatory bowel disease context",
        "keywords": ["inflammatory bowel", "bowel disease", "ulcerative colitis", "crohn"],
        "symptoms": ["abdominal pain", "diarrhea", "fatigue"],
        "diseases": ["Inflammatory Bowel Disease"]
    },
    {
        "label": "Breast carcinoma indicators",
        "keywords": ["breast carcinoma", "breast cancer", "mammary carcinoma"],
        "symptoms": ["swelling", "fatigue", "weight loss"],
        "diseases": ["Breast Cancer"]
    },
    {
        "label": "Lung cancer cues",
        "keywords": ["lung carcinoma", "lung cancer", "bronchogenic carcinoma", "pulmonary malignancy"],
        "symptoms": ["cough", "shortness of breath", "chest pain", "weight loss"],
        "diseases": ["Lung Cancer"]
    },
    {
        "label": "Tuberculosis references",
        "keywords": ["tuberculosis", "mycobacterium", "tb infection"],
        "symptoms": ["cough", "night sweats", "weight loss", "fatigue"],
        "diseases": ["Tuberculosis"]
    },
    {
        "label": "Diabetes mellitus indicators",
        "keywords": ["diabetes mellitus", "hyperglycemia", "diabetic"],
        "symptoms": ["thirst", "increased urination", "weight loss", "fatigue"],
        "diseases": ["Diabetes Mellitus"]
    },
    {
        "label": "Thyroid disorder language",
        "keywords": ["thyroid disorder", "hypothyroidism", "hyperthyroidism", "thyroiditis"],
        "symptoms": ["fatigue", "weight gain", "anxiety"],
        "diseases": ["Thyroid Disorder"]
    },
    {
        "label": "Chronic kidney disease cues",
        "keywords": ["chronic kidney disease", "renal failure", "nephropathy"],
        "symptoms": ["swelling", "fatigue", "nausea"],
        "diseases": ["Chronic Kidney Disease"]
    },
    {
        "label": "Cardiovascular risk markers",
        "keywords": ["myocardial infarction", "ischemic heart", "coronary artery disease", "heart failure"],
        "symptoms": ["chest pain", "shortness of breath", "fatigue"],
        "diseases": ["Coronary Artery Disease", "Heart Failure"]
    }
]


def _parse_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "").strip())
    except (TypeError, ValueError, AttributeError):
        return None


def analyze_lab_markers(text: str):
    """Extract lab-marker insights (e.g., Beta HCG ranges) from report text."""
    extra_symptoms: set[str] = set()
    informative_notes: list[str] = []
    alerts: list[str] = []
    extra_diseases: set[str] = set()

    beta_hcg_match = re.search(
        r"BETA\s+HCG[\s\S]*?([0-9.,]+)\s*mIU/mL[\s\S]*?<\s*([0-9.,]+)",
        text,
        flags=re.IGNORECASE,
    )
    if beta_hcg_match:
        value = _parse_float(beta_hcg_match.group(1))
        reference = _parse_float(beta_hcg_match.group(2))
        if value is not None and reference is not None:
            if value >= reference:
                alerts.append(
                    f"Beta-hCG level {value:.2f} mIU/mL exceeds the stated reference threshold < {reference:.2f} mIU/mL."
                )
                extra_symptoms.update(["nausea", "fatigue", "weight loss"])
                extra_diseases.add("Gestational Trophoblastic Disease")
            else:
                informative_notes.append(
                    f"Beta-hCG level {value:.2f} mIU/mL is within the stated reference range (< {reference:.2f} mIU/mL)."
                )
    return extra_symptoms, informative_notes, alerts, extra_diseases


def extract_report_symptoms(text: str):
    """Return symptoms plus contextual notes derived from a medical report."""
    found_symptoms: set[str] = set()
    context_hits: list[dict[str, list[str] | str]] = []
    suggested_diseases: set[str] = set()

    lower_text = text.lower()

    for main_symptom, synonyms in SYMPTOM_SYNONYMS.items():
        for synonym in synonyms:
            if synonym in lower_text:
                found_symptoms.add(main_symptom)
                break

    for hint in REPORT_KEYWORD_HINTS:
        for keyword in hint["keywords"]:
            if keyword in lower_text:
                added = [sym for sym in hint["symptoms"] if sym in symptom_list]
                if added:
                    found_symptoms.update(added)
                    context_entry = {
                        "label": hint["label"],
                        "symptoms": sorted(set(added))
                    }
                    diseases = hint.get("diseases")
                    if diseases:
                        suggested_diseases.update(diseases)
                        context_entry["diseases"] = sorted(set(diseases))
                    context_hits.append(context_entry)
                break

    lab_symptoms, lab_notes, lab_alerts, lab_diseases = analyze_lab_markers(text)
    found_symptoms.update(sym for sym in lab_symptoms if sym in symptom_list)
    suggested_diseases.update(lab_diseases)

    return (
        sorted(found_symptoms),
        context_hits,
        lab_notes,
        lab_alerts,
        sorted(suggested_diseases),
    )

# =============================
# PDF Report Generator
# =============================
def generate_report(patient, symptoms, results, filename="report.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Healthcare Disease Risk Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # Patient Details
    story.append(Paragraph("<b>Patient Details</b>", styles["Heading2"]))
    details = f"""
    <b>Name:</b> {patient.get("name", "N/A")} <br/>
    <b>Age:</b> {patient.get("age", "N/A")} <br/>
    <b>Gender:</b> {patient.get("gender", "N/A")} <br/>
    <b>Medical History:</b> {patient.get("medical_history", "N/A")}
    """
    story.append(Paragraph(details, styles["Normal"]))
    story.append(Spacer(1, 12))

    # Symptoms
    story.append(Paragraph("<b>Reported Symptoms</b>", styles["Heading2"]))
    story.append(Paragraph(", ".join(symptoms) if symptoms else "None", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Prediction Results (top 5)
    story.append(Paragraph("<b>Prediction Results</b>", styles["Heading2"]))
    table_data = [["Disease", "Probability"]]
    for _, row in results.head(5).iterrows():
        table_data.append([row["Disease"], f"{row['Probability']:.2f}"])

    table = Table(table_data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4B8BBE")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

    # Note
    story.append(Paragraph("<b>Doctor's Note</b>", styles["Heading2"]))
    story.append(Paragraph(
        "This report is AI-generated based on selected symptoms. "
        "It is not a medical diagnosis. Please consult a certified doctor for confirmation.",
        styles["Italic"]
    ))

    doc.build(story)
    return filename

# =============================
# Prediction Helper
# =============================
def predict_disease(symptoms):
    X_input = np.zeros(len(symptom_list))
    for s in symptoms:
        if s in symptom_list:
            idx = np.where(symptom_list == s)[0][0]
            X_input[idx] = 1
    preds = model.predict_proba([X_input])[0]
    results = pd.DataFrame({"Disease": model.classes_, "Probability": preds})
    results = results.sort_values(by="Probability", ascending=False).reset_index(drop=True)
    return results

def plot_probabilities(results, top_n=10):
    # Create gradient colors based on probability (vibrant medical theme)
    top_results = results.head(top_n).copy()
    
    # Add visual indicators for probability levels
    top_results['RiskLevel'] = top_results['Probability'].apply(
        lambda x: '🔴 High' if x > 0.7 else ('🟡 Medium' if x > 0.4 else '🟢 Low')
    )
    
    # Enhanced color scale with more vibrant medical greens
    fig = px.bar(
        top_results,
        x="Probability",
        y="Disease",
        orientation="h",
        title="",
        text="Probability",
        color="Probability",
        color_continuous_scale=[
            "#C8E6C9",  # Very light green
            "#A5D6A7",  # Light green
            "#81C784",  # Medium-light green
            "#66BB6A",  # Medium green
            "#4CAF50",  # Standard green
            "#43A047",  # Medium-dark green
            "#388E3C",  # Dark green
            "#2E7D32",  # Very dark green
            "#1B5E20"   # Deepest green
        ],
        range_color=[0, 1]
    )
    
    # Premium styling with enhanced visual effects
    fig.update_traces(
        texttemplate="<b>%{x:.1%}</b>",
        textposition="outside",
        marker=dict(
            line=dict(width=2, color='rgba(255,255,255,0.95)'),
            cornerradius=12,
            opacity=0.95
        ),
        hovertemplate="<b>%{y}</b><br>" +
                      "Probability: <b>%{x:.2%}</b><br>" +
                      "<extra></extra>",
        textfont=dict(
            size=13,
            color='#1B5E20',
            family='Segoe UI, Arial, sans-serif',
            weight='bold'
        ),
        cliponaxis=False
    )
    
    # Premium layout with medical theme
    fig.update_layout(
        yaxis=dict(
            autorange="reversed",
            title="",
            tickfont=dict(
                size=13,
                family='Segoe UI, Arial, sans-serif',
                color='#2E7D32'
            ),
            gridcolor='rgba(46, 125, 50, 0.12)',
            gridwidth=1.5,
            showgrid=True,
            linecolor='rgba(46, 125, 50, 0.2)',
            linewidth=1,
            ticklen=8,
            tickcolor='rgba(46, 125, 50, 0.3)'
        ),
        xaxis=dict(
            title=dict(
                text="<b>Prediction Probability</b>",
                font=dict(
                    size=15,
                    family='Segoe UI, Arial, sans-serif',
                    color='#1B5E20',
                    weight='bold'
                ),
                standoff=15
            ),
            tickfont=dict(
                size=12,
                family='Segoe UI, Arial, sans-serif',
                color='#555'
            ),
            tickformat='.0%',
            gridcolor='rgba(46, 125, 50, 0.15)',
            gridwidth=1.5,
            showgrid=True,
            linecolor='rgba(46, 125, 50, 0.3)',
            linewidth=2,
            range=[0, min(1.15, top_results['Probability'].max() * 1.2)],
            zeroline=True,
            zerolinecolor='rgba(46, 125, 50, 0.2)',
            zerolinewidth=1.5
        ),
        plot_bgcolor='rgba(232, 245, 233, 0.15)',
        paper_bgcolor='white',
        font=dict(family='Segoe UI, Arial, sans-serif', size=12),
        margin=dict(l=25, r=30, t=80, b=60),
        height=max(450, len(top_results) * 50),
        showlegend=False,
        coloraxis_showscale=False,  # Hide the colorbar
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#2E7D32',
            font=dict(size=13, family='Segoe UI, Arial, sans-serif')
        ),
        # Properly aligned title
        title=dict(
            text=f'📊 Top Predicted Diseases<br><sub style="font-size: 13px; color: #666;">Showing top {len(top_results)} predictions</sub>',
            x=0.5,
            xanchor='center',
            font=dict(size=22, family='Segoe UI, Arial, sans-serif', color='#1B5E20'),
            pad=dict(t=20, b=10)
        ),
        # Add subtle shadow effect
        shapes=[
            dict(
                type='rect',
                xref='paper',
                yref='paper',
                x0=0,
                y0=0,
                x1=1,
                y1=1,
                fillcolor='rgba(0,0,0,0)',
                layer='below',
                line=dict(
                    color='rgba(46, 125, 50, 0.1)',
                    width=1
                )
            )
        ]
    )
    
    return fig

# =============================
# Streamlit UI
# =============================

st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================
# Custom CSS for Modern UI
# =============================
def load_custom_css():
    st.markdown("""
    <style>
    /* Animated medical hero */
    .medical-hero {
        position: relative;
        background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 45%, #66BB6A 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 2rem;
        box-shadow: 0 12px 36px rgba(46, 125, 50, 0.35);
        overflow: hidden;
        border: 2px solid rgba(255,255,255,0.18);
    }

    .medical-hero::before,
    .medical-hero::after {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 70%);
        filter: blur(0.3px);
    }

    .medical-hero::before {
        top: -70px;
        right: -40px;
    }

    .medical-hero::after {
        bottom: -90px;
        left: -70px;
    }

    .medical-hero-content {
        position: relative;
        z-index: 2;
        text-align: center;
    }

    .medical-hero h1 {
        margin: 0;
        font-size: 2.4rem;
        font-weight: 700;
        letter-spacing: -0.3px;
        text-shadow: 0 6px 18px rgba(0,0,0,0.22);
    }

    .medical-hero p {
        margin-top: 1rem;
        font-size: 1.1rem;
        font-weight: 500;
        color: rgba(255,255,255,0.95);
    }

    .medical-hero-badges {
        margin-top: 1.5rem;
        display: inline-flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        justify-content: center;
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.55rem 1.1rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.18);
        color: #ffffff;
        font-weight: 600;
        font-size: 0.9rem;
        border: 1px solid rgba(255,255,255,0.25);
        backdrop-filter: blur(6px);
        animation: badgeFade 6s ease-in-out infinite;
    }

    .hero-badge::before {
        content: "•";
        font-size: 1.2rem;
        line-height: 1;
    }

    .medical-floaters {
        position: absolute;
        inset: 0;
        pointer-events: none;
        z-index: 1;
    }

    .medical-icon {
        position: absolute;
        font-size: 2.8rem;
        opacity: 0.85;
        filter: drop-shadow(0 10px 18px rgba(0,0,0,0.2));
    }

    .medical-icon.icon-pill {
        top: 12%;
        left: 8%;
        animation: floatUp 7s ease-in-out infinite;
    }

    .medical-icon.icon-heart {
        top: 18%;
        right: 12%;
        animation: heartbeat 2.2s ease-in-out infinite;
    }

    .medical-icon.icon-stethoscope {
        bottom: 18%;
        left: 18%;
        animation: floatUp 6.5s ease-in-out infinite reverse;
    }

    .medical-icon.icon-dna {
        bottom: 12%;
        right: 10%;
        animation: slowSpin 12s linear infinite;
        font-size: 3.1rem;
    }

    @keyframes floatUp {
        0%, 100% { transform: translateY(0px); opacity: 0.8; }
        50% { transform: translateY(-16px); opacity: 1; }
    }

    @keyframes heartbeat {
        0%, 100% { transform: scale(1); opacity: 0.85; }
        25% { transform: scale(1.12); opacity: 1; }
        45% { transform: scale(0.98); opacity: 0.9; }
        60% { transform: scale(1.08); opacity: 1; }
    }

    @keyframes slowSpin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @keyframes badgeFade {
        0%, 100% { opacity: 0.85; transform: translateY(0px); }
        50% { opacity: 1; transform: translateY(-4px); }
    }

    @media (prefers-reduced-motion: reduce) {
        .medical-icon,
        .hero-badge {
            animation: none !important;
        }
    }

    /* Sticky toolbar */
    .sticky-toolbar {
        position: sticky;
        top: 0;
        z-index: 100;
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-bottom: 1px solid rgba(0,0,0,0.06);
        padding: 0.5rem 0.75rem;
        margin-bottom: 0.75rem;
    }

    /* Main styling */
    .main {
        padding: 2rem 1rem;
    }
    
    /* Header styling - Medical theme */
    .main-header {
        background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(46, 125, 50, 0.3);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    /* Card styling - Medical theme */
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        border-left: 4px solid #4CAF50;
    }
    
    /* Login/Register card */
    .auth-card {
        background: white;
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        max-width: 500px;
        margin: 0 auto;
    }
    
    /* Button styling - Medical theme */
    .stButton>button {
        background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(46, 125, 50, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(46, 125, 50, 0.6);
        background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
    }
    
    /* Input styling */
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>select {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 0.5rem;
    }
    
    .stTextInput>div>div>input:focus,
    .stNumberInput>div>div>input:focus {
        border-color: #4CAF50;
        box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.2);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Success/Error messages */
    .stSuccess {
        border-radius: 10px;
        padding: 1rem;
    }
    
    .stError {
        border-radius: 10px;
        padding: 1rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 1rem 2rem;
        font-weight: 600;
    }
    
    /* Info boxes - Medical theme */
    .info-box {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    
    /* Feature cards */
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        text-align: center;
        transition: transform 0.3s;
        border-top: 3px solid #4CAF50;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
    }
    
    /* Skeletons */
    .skeleton-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    .skeleton {
        position: relative;
        overflow: hidden;
        background: #e9ecef;
        border-radius: 6px;
    }
    .skeleton::after {
        content: "";
        position: absolute;
        top: 0;
        left: -150px;
        height: 100%;
        width: 150px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
        animation: shimmer 1.2s infinite;
    }
    @keyframes shimmer {
        100% { transform: translateX(300%); }
    }

    /* Compact table density */
    .compact-table table {
        font-size: 0.9rem;
    }
    .compact-table table th, .compact-table table td {
        padding: 6px 8px !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #4CAF50;
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #2E7D32;
    }
    </style>
    """, unsafe_allow_html=True)

# Load custom CSS
load_custom_css()

# -----------------------------
# Theme persistence helpers
# -----------------------------
def _read_prefs() -> dict:
    try:
        if os.path.exists(PREFS_FILE):
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _write_prefs(data: dict) -> None:
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_user_theme_prefs(user_key: str) -> dict | None:
    prefs = _read_prefs()
    return prefs.get(user_key)

def save_user_theme_prefs(user_key: str, preset: str, primary: str, secondary: str, accent: str) -> None:
    prefs = _read_prefs()
    prefs[user_key] = {
        "preset": preset,
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
    }
    _write_prefs(prefs)

# Simple theme selector (primary/accent colors)
def apply_theme(primary: str, secondary: str, accent: str):
    st.markdown(f"""
    <style>
      :root {{
        --theme-primary: {primary};
        --theme-secondary: {secondary};
        --theme-accent: {accent};
      }}
      /* Override key UI elements with selected theme */
      .medical-hero {{
        background: linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-secondary) 45%, var(--theme-accent) 100%) !important;
        box-shadow: 0 12px 36px rgba(0,0,0,0.25) !important;
      }}
      .hero-badge {{
        border-color: rgba(255,255,255,0.25) !important;
        background: rgba(255,255,255,0.18) !important;
        color: #fff !important;
      }}
      .stButton>button {{
        background: linear-gradient(135deg, var(--theme-secondary), var(--theme-accent)) !important;
        border: 1px solid var(--theme-secondary) !important;
        color: #fff !important;
      }}
      .stButton>button:hover {{
        filter: brightness(0.95);
      }}
      [data-baseweb="tab-list"] [role="tab"][aria-selected="true"] {{
        color: var(--theme-primary) !important;
        border-bottom: 2px solid var(--theme-secondary) !important;
      }}
      ::-webkit-scrollbar-thumb {{
        background: var(--theme-secondary) !important;
      }}
      ::-webkit-scrollbar-thumb:hover {{
        background: var(--theme-primary) !important;
      }}
      /* Stat card accent (if present) */
      .stat-card, .stMetric {{
        --metric-accent: var(--theme-secondary);
      }}
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
init_session_state()

# Determine current user key for prefs
current_user_key = str(st.session_state.user_id) if st.session_state.user_id else "guest"
stored = load_user_theme_prefs(current_user_key)

# Hide the default Streamlit sidebar controls
st.markdown(
    """
    <style>
      section[data-testid="stSidebar"] {display: none !important;}
      [data-testid="collapsedControl"] {display: none !important;}
      .block-container {padding-left: 8px !important; padding-right: 8px !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Custom inline control panel
control_col, content_col = st.columns([0.7, 3.3], gap="small")

with control_col:
    with st.container(border=True):
        st.markdown("### 🎨 Theme")
        presets = {
            "Medical Green (default)": ("#2E7D32", "#4CAF50", "#66BB6A"),
            "Calm Blue": ("#1565C0", "#1E88E5", "#42A5F5"),
            "Royal Purple": ("#6A1B9A", "#8E24AA", "#BA68C8"),
            "Teal": ("#00695C", "#00897B", "#26A69A"),
            "Sunset": ("#D32F2F", "#F57C00", "#FBC02D"),
            "Custom…": None,
        }
        preset_names = list(presets.keys())
        default_index = 0
        if stored and stored.get("preset") in preset_names:
            default_index = preset_names.index(stored["preset"])
        elif stored and stored.get("preset") == "Custom…":
            default_index = preset_names.index("Custom…")
        choice_panel = st.selectbox(
            "Color preset",
            preset_names,
            index=default_index,
            key="theme_preset_panel",
        )
        if choice_panel == "Custom…":
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                primary = st.color_picker(
                    "Primary",
                    value=(stored.get("primary") if stored else "#2E7D32"),
                    key="theme_primary_panel",
                )
            with col_b:
                secondary = st.color_picker(
                    "Secondary",
                    value=(stored.get("secondary") if stored else "#4CAF50"),
                    key="theme_secondary_panel",
                )
            with col_c:
                accent = st.color_picker(
                    "Accent",
                    value=(stored.get("accent") if stored else "#66BB6A"),
                    key="theme_accent_panel",
                )
        else:
            if stored and stored.get("preset") == choice_panel:
                primary = stored.get("primary", presets[choice_panel][0])
                secondary = stored.get("secondary", presets[choice_panel][1])
                accent = stored.get("accent", presets[choice_panel][2])
            else:
                primary, secondary, accent = presets[choice_panel]

        apply_theme(primary, secondary, accent)
        save_user_theme_prefs(current_user_key, choice_panel, primary, secondary, accent)

        # Only show user/logout/stats when authenticated
        if st.session_state.authenticated:
            display_name = st.session_state.username if st.session_state.username else "Guest"
            st.markdown(
                f"""
                <div style='text-align: center; padding: 0.75rem 0;'>
                    <h3 style='color: #2E7D32; margin-bottom: 0.3rem;'>👤 {display_name}</h3>
                    <p style='color: #666; font-size: 0.9rem;'>Welcome back!</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🚪 Logout", use_container_width=True, key="inline_logout_btn"):
                logout_user()
            st.markdown("---")
            st.markdown("### 📊 Dashboard Stats")
            total_records = 0
            try:
                if st.session_state.token:
                    headers = get_api_headers()
                    resp = requests.get(f"{API_BASE_URL}/api/patient-records", headers=headers, timeout=5)
                    if resp.status_code == 200:
                        records = resp.json().get("records", [])
                        total_records = len(records)
            except requests.exceptions.RequestException:
                pass
            except Exception:
                pass
            if total_records == 0:
                try:
                    if os.path.exists("patient_history.csv"):
                        df_hist = pd.read_csv("patient_history.csv")
                        total_records = len(df_hist)
                except Exception:
                    total_records = 0
            st.metric("📋 Total Records", int(total_records))


# =============================
# Login Page
# =============================
if not st.session_state.authenticated:
    # Verify token if exists (for page refresh)
    if st.session_state.token:
        if not verify_token():
            st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        # Login/Register Page with modern design (rendered in right content column)
        content_col.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 2.8rem; background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%); 
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                       margin-bottom: 0.5rem; white-space: nowrap; font-weight: 700;'>
                       🏥 Healthcare Disease Prediction System</h1>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = content_col.columns([0.15, 1.7, 0.15])
        
        with col2:
            # Tabs for Login and Register with better styling
            auth_tabs = col2.tabs(["🔐 Login", "📝 Register"])
            
            # Login Tab
            with auth_tabs[0]:
                st.markdown("### Welcome Back! 👋")
                st.markdown("<p style='color: #666; margin-bottom: 2rem;'>Sign in to access the disease prediction system</p>", unsafe_allow_html=True)
                
                # Initialize forgot password state
                if 'show_forgot_password' not in st.session_state:
                    st.session_state.show_forgot_password = False
                if 'show_reset_password' not in st.session_state:
                    st.session_state.show_reset_password = False
                if 'reset_email' not in st.session_state:
                    st.session_state.reset_email = None
                
                # Show forgot password form if requested
                if st.session_state.show_forgot_password and not st.session_state.show_reset_password:
                    st.markdown("---")
                    st.markdown("### 🔐 Forgot Password")
                    with st.form("forgot_password_form"):
                        reset_email = st.text_input("📧 Email", key="forgot_email", placeholder="Enter your registered email")
                        submit_forgot = st.form_submit_button("📧 Send Reset Code", use_container_width=True)
                        
                        if submit_forgot:
                            if reset_email:
                                success, message = request_password_reset(reset_email)
                                if success:
                                    st.success(f"✅ {message}")
                                    st.session_state.reset_email = reset_email
                                    st.session_state.show_reset_password = True
                                else:
                                    st.error(f"❌ {message}")
                            else:
                                st.warning("⚠️ Please enter your email")
                    
                    if st.button("← Back to Login", use_container_width=True):
                        st.session_state.show_forgot_password = False
                        st.rerun()
                
                # Show reset password form
                elif st.session_state.show_reset_password and st.session_state.reset_email:
                    st.markdown("---")
                    st.markdown("### 🔑 Reset Password")
                    with st.form("reset_password_form"):
                        st.info(f"📧 Reset code sent to: {st.session_state.reset_email}")
                        reset_otp = st.text_input("🔐 Enter Reset Code", key="reset_otp", placeholder="6-digit code")
                        new_password = st.text_input("🔒 New Password", type="password", key="new_password", placeholder="Minimum 6 characters")
                        confirm_password = st.text_input("🔒 Confirm Password", type="password", key="confirm_password", placeholder="Re-enter password")
                        submit_reset = st.form_submit_button("✨ Reset Password", use_container_width=True)
                        
                        if submit_reset:
                            if reset_otp and new_password and confirm_password:
                                if new_password != confirm_password:
                                    st.error("❌ Passwords do not match")
                                elif len(new_password) < 6:
                                    st.error("❌ Password must be at least 6 characters")
                                else:
                                    success, message = reset_password_with_otp(st.session_state.reset_email, reset_otp, new_password)
                                    if success:
                                        st.success(f"✅ {message}")
                                        st.session_state.show_forgot_password = False
                                        st.session_state.show_reset_password = False
                                        st.session_state.reset_email = None
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {message}")
                            else:
                                st.warning("⚠️ Please fill all fields")
                    
                    if st.button("← Back", use_container_width=True):
                        st.session_state.show_reset_password = False
                        st.rerun()
                
                # Normal login form
                else:
                    with st.form("login_form"):
                        username_or_email = st.text_input("👤 Email/Username", key="login_username", placeholder="Enter your email or username")
                        password = st.text_input("🔒 Password", type="password", key="login_password", placeholder="Enter your password")
                        
                        # Forgot password link
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            submit_login = st.form_submit_button("🚀 Login", use_container_width=True)
                        with col2:
                            if st.form_submit_button("🔐 Forgot?", use_container_width=True):
                                st.session_state.show_forgot_password = True
                                st.rerun()
                        
                        if submit_login:
                            if username_or_email and password:
                                success, message = login_user(username_or_email, password)
                                if success:
                                    st.success(f"✅ {message}")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
                            else:
                                st.warning("⚠️ Please enter both email/username and password")
                    
                # Default credentials info with better styling
                if not st.session_state.show_forgot_password:
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); 
                                padding: 1rem; border-radius: 10px; border-left: 4px solid #4CAF50; 
                                margin-top: 1.5rem;'>
                        <p style='margin: 0; color: #333;'><strong>💡 Default Credentials:</strong><br>
                        Username/Email: <code>admin</code> or <code>admin@example.com</code><br>
                        Password: <code>admin123</code></p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Register Tab
            with auth_tabs[1]:
                st.markdown("### Create Your Account 🎉")
                st.markdown("<p style='color: #666; margin-bottom: 2rem;'>Join us to start predicting diseases</p>", unsafe_allow_html=True)
                
                # Initialize OTP sent state
                if 'otp_sent' not in st.session_state:
                    st.session_state.otp_sent = False
                if 'otp_email' not in st.session_state:
                    st.session_state.otp_email = None
                
                reg_username = st.text_input("👤 Username", key="reg_username", placeholder="Choose a username")
                reg_email = st.text_input("📧 Email", key="reg_email", placeholder="your.email@example.com")
                
                # Send OTP button with better styling
                col_otp1, col_otp2 = st.columns([2, 1])
                with col_otp1:
                    if st.button("📧 Send OTP Code", use_container_width=True, key="send_otp_btn"):
                        if reg_email:
                            if '@' in reg_email and '.' in reg_email.split('@')[1]:
                                success, message = send_otp_to_email(reg_email)
                                if success:
                                    st.session_state.otp_sent = True
                                    st.session_state.otp_email = reg_email
                                    st.success(f"✅ {message}")
                                    st.info("💡 Check your email for the OTP code. If email is not configured, check the backend console for the OTP.")
                                else:
                                    st.error(f"❌ {message}")
                            else:
                                st.warning("⚠️ Please enter a valid email address")
                        else:
                            st.warning("⚠️ Please enter your email first")
                
                # Show OTP input if OTP has been sent
                if st.session_state.otp_sent and st.session_state.otp_email == reg_email:
                    st.markdown("---")
                    reg_otp = st.text_input("🔐 Enter OTP Code", key="reg_otp", placeholder="Enter 6-digit code")
                    st.markdown("<p style='color: #666; font-size: 0.9rem;'>⏰ OTP expires in 10 minutes</p>", unsafe_allow_html=True)
                else:
                    reg_otp = ""
                
                with st.form("register_form"):
                    reg_password = st.text_input("🔒 Password", type="password", key="reg_password", placeholder="Minimum 6 characters")
                    reg_confirm = st.text_input("🔒 Confirm Password", type="password", key="reg_confirm", placeholder="Re-enter your password")
                    submit_register = st.form_submit_button("✨ Create Account", use_container_width=True)
                    
                    if submit_register:
                        if not reg_username or not reg_email or not reg_password:
                            st.warning("Please fill all fields")
                        elif not st.session_state.otp_sent or st.session_state.otp_email != reg_email:
                            st.error("Please send OTP first")
                        elif not reg_otp:
                            st.error("Please enter the OTP code")
                        elif reg_password != reg_confirm:
                            st.error("Passwords do not match")
                        elif len(reg_password) < 6:
                            st.error("Password must be at least 6 characters")
                        else:
                            # Verify OTP first
                            verify_success, verify_msg = verify_otp_code(reg_email, reg_otp)
                            if verify_success:
                                # Proceed with registration
                                success, message = register_user(reg_username, reg_email, reg_password, reg_otp)
                                if success:
                                    st.success(message)
                                    # Reset OTP state
                                    st.session_state.otp_sent = False
                                    st.session_state.otp_email = None
                                    st.rerun()
                                else:
                                    st.error(message)
                            else:
                                st.error(verify_msg)
        
        st.stop()

# =============================
# Main Application (Authenticated Users)
# =============================
# Sidebar is rendered globally above for both authenticated and guest users.

# Main header with animated medical floaters
content_col.markdown("""
<div class="medical-hero">
    <div class="medical-floaters">
        <span class="medical-icon icon-pill">💊</span>
        <span class="medical-icon icon-heart">❤️</span>
        <span class="medical-icon icon-stethoscope">🩺</span>
        <span class="medical-icon icon-dna">🧬</span>
    </div>
    <div class="medical-hero-content">
        <h1>🏥 Healthcare Disease Prediction System</h1>
        <p>Multi-Disease Prediction & Analysis</p>
        <div class="medical-hero-badges">
            <span class="hero-badge">Smart Triage</span>
            <span class="hero-badge">Instant Insights</span>
            <span class="hero-badge">Patient Safety</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tabs = content_col.tabs([

    "🔍 Single Prediction",
    "📊 Batch Analysis",
    "🩺 Symptom Check",
    "💉 Diabetes Prediction",
    "📄 Medical Report"
])

# -----------------------------
# Tab 1: Single Prediction
# -----------------------------
with tabs[0]:

    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); 
                padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; 
                margin-bottom: 2rem;'>
        <h2 style='color: #2E7D32; margin: 0;'>👤 Patient Details & Disease Prediction</h2>
        <p style='color: #666; margin: 0.5rem 0 0 0;'>Enter patient information and symptoms to get disease predictions</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("single_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            age = st.number_input("Age", min_value=1, max_value=120, value=30)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        with col2:
            medical_history = st.text_area("Medical History", placeholder="e.g., Hypertension, past surgeries")

        st.subheader("Current Symptoms")
        symptoms = st.multiselect("Select symptoms", options=symptom_list)

        submitted = st.form_submit_button("🔍 Predict Disease")

    if submitted:
        if symptoms:

            # Prediction progress animation
            prog = st.progress(0, text="Analyzing symptoms...")
            for i in range(0, 100, 8):
                time.sleep(0.05)
                prog.progress(min(100, i), text="Analyzing symptoms...")
            results = predict_disease(symptoms)

            prog.empty()
            
            # Enhanced Results Display
            st.markdown("---")
            st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); 
                        padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; 
                        margin: 2rem 0;'>
                <h2 style='color: #2E7D32; margin: 0;'>📊 Prediction Results</h2>
                <p style='color: #666; margin: 0.5rem 0 0 0;'>Disease predictions based on selected symptoms</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Top Prediction Card
            top_disease = results.iloc[0]["Disease"]
            top_prob = results.iloc[0]["Probability"]
            
            col_prob1, col_prob2 = st.columns(2)
            with col_prob1:
                st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 10px; 
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 4px solid #4CAF50;'>
                    <h3 style='color: #2E7D32; margin: 0 0 0.5rem 0;'>🎯 Top Prediction</h3>
                    <h2 style='color: #333; margin: 0;'>{top_disease}</h2>
                    <p style='color: #666; margin: 0.5rem 0 0 0; font-size: 0.9rem;'>
                        Confidence: <strong style='color: #4CAF50;'>{top_prob*100:.1f}%</strong>
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_prob2:
                st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 10px; 
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 4px solid #66BB6A;'>
                    <h3 style='color: #2E7D32; margin: 0 0 0.5rem 0;'>📈 All Predictions</h3>
                    <p style='color: #666; margin: 0;'>View detailed results below</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Results Table with better styling
            st.markdown("### 📋 Detailed Results")
            st.dataframe(results.head(10), use_container_width=True)

            fig = plot_probabilities(results)
            st.plotly_chart(fig, use_container_width=True)

            patient_info = {
                "name": name,
                "age": age,
                "gender": gender,
                "medical_history": medical_history
            }
            report_path = root / "reports"
            os.makedirs(report_path, exist_ok=True)
            pdf_file = report_path / f"{name or 'patient'}_report.pdf"

            generate_report(patient_info, symptoms, results, filename=str(pdf_file))

            with open(pdf_file, "rb") as f:
                st.download_button("📄 Download Report", f, file_name=pdf_file.name, mime="application/pdf")

            # -----------------------------

            # ✅ Save prediction to backend and CSV
            # -----------------------------

            
            # Save to backend
            save_patient_record_to_backend(patient_info, symptoms, results)
            
            # Also save to local CSV (backup)
            history_file = "patient_history.csv"
            top_disease = results.iloc[0]["Disease"]
            top_prob = results.iloc[0]["Probability"]

            new_record = pd.DataFrame([{
                "Patient Name": name or "Unknown",
                "Age": age,
                "Gender": gender,
                "Medical History": medical_history,
                "Symptoms": ", ".join(symptoms),
                "Top Predicted Disease": top_disease,
                "Probability": round(top_prob, 2)
            }])

            if os.path.exists(history_file):
                old = pd.read_csv(history_file)
                updated = pd.concat([old, new_record], ignore_index=True)
                updated.to_csv(history_file, index=False)
            else:
                new_record.to_csv(history_file, index=False)

        else:
            st.warning("Please select at least one symptom.")

    # -----------------------------
    # 📜 Patient History Button
    # -----------------------------
    st.markdown("---")
    if st.button("📜 View Patient History"):

        # Try to fetch from backend first
        backend_records = []
        try:
            headers = get_api_headers()
            response = requests.get(f'{API_BASE_URL}/api/patient-records', headers=headers, timeout=5)
            if response.status_code == 200:
                backend_records = response.json().get('records', [])
        except:
            pass
        
        # Also load from local CSV
        history_file = "patient_history.csv"
        local_records = []
        try:
            if os.path.exists(history_file):
                df_history = pd.read_csv(history_file)
                if not df_history.empty:
                    local_records = df_history.to_dict('records')
        except:
            pass
        
        # Combine and display records
        if backend_records or local_records:
            st.subheader("Saved Patient Records")
            # Removed delete buttons per user request
            
            # Create DataFrame from backend records
            if backend_records:
                backend_df = pd.DataFrame(backend_records)
                backend_df = backend_df.rename(columns={
                    'patient_name': 'Patient Name',
                    'age': 'Age',
                    'gender': 'Gender',
                    'medical_history': 'Medical History',
                    'symptoms': 'Symptoms',
                    'predicted_disease': 'Top Predicted Disease',
                    'probability': 'Probability'
                })
                st.write("**From Backend Database:**")
                st.dataframe(backend_df[['Patient Name', 'Age', 'Gender', 'Symptoms', 'Top Predicted Disease', 'Probability']])
            
            # Display local CSV records
            if local_records:
                local_df = pd.DataFrame(local_records)
                if backend_records:
                    st.write("**From Local CSV:**")
                st.dataframe(local_df)
            
            # Search functionality
            patient_filter = st.text_input("🔎 Search by Patient Name")
            if patient_filter:
                if backend_records:
                    filtered_backend = backend_df[backend_df["Patient Name"].str.contains(patient_filter, case=False, na=False)]
                    if not filtered_backend.empty:
                        st.dataframe(filtered_backend)
                if local_records:
                    filtered_local = local_df[local_df["Patient Name"].str.contains(patient_filter, case=False, na=False)]
                    if not filtered_local.empty:
                        st.dataframe(filtered_local)
        else:
            st.info("No patient history records available yet.")


# -----------------------------
# Tab 2: Batch CSV Prediction
# -----------------------------
with tabs[1]:
    st.header("Batch CSV Prediction")
    st.write("Upload a CSV with columns **Name** and **Symptoms** (comma-separated).")


    if st.session_state.show_csv_wizard:
        with st.expander("🧙 CSV Upload Wizard (map your columns)", expanded=True):
            csv_upload_wizard()
            st.markdown("---")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df.columns = [col.strip() for col in df.columns]

        if "Symptoms" not in df.columns:
            st.error("CSV must contain a 'Symptoms' column.")
        else:
            all_results = []
            for idx, row in enumerate(df.itertuples(index=False), start=1):
                patient_name = getattr(row, "Name") if "Name" in df.columns else f"Patient {idx}"
                symptoms_raw = str(getattr(row, "Symptoms"))
                symptoms = [s.strip() for s in symptoms_raw.split(",") if s.strip()]
                results = predict_disease(symptoms)
                top_disease = results.iloc[0]["Disease"]
                prob = results.iloc[0]["Probability"]

                all_results.append({
                    "Name": patient_name,
                    "Symptoms": ", ".join(symptoms),
                    "Top Disease": top_disease,
                    "Probability": round(prob, 2)
                })

            batch_df = pd.DataFrame(all_results)
            st.subheader("Batch Prediction Results")

            if st.session_state.compact_density:
                st.markdown("<div class='compact-table'>", unsafe_allow_html=True)
            st.dataframe(batch_df, use_container_width=True)
            if st.session_state.compact_density:
                st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Tab 3: Symptom-based Prediction
# -----------------------------
with tabs[2]:

    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); 
                padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; 
                margin-bottom: 2rem;'>
        <h2 style='color: #2E7D32; margin: 0;'>🩺 Quick Symptom Check</h2>
        <p style='color: #666; margin: 0.5rem 0 0 0;'>Select symptoms to get instant disease predictions</p>
    </div>
    """, unsafe_allow_html=True)
    symptoms = st.multiselect("Select Symptoms", options=symptom_list)

    if st.button("🔍 Predict"):
        if symptoms:
            results = predict_disease(symptoms)
            st.subheader("Prediction Results")
            st.dataframe(results.head(10))

            fig = plot_probabilities(results)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Please select at least one symptom.")

# -----------------------------
# Tab 4: Diabetes Prediction
# -----------------------------
with tabs[3]:

    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); 
                padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; 
                margin-bottom: 2rem;'>
        <h2 style='color: #2E7D32; margin: 0;'>💉 Diabetes Risk Assessment</h2>
        <p style='color: #666; margin: 0.5rem 0 0 0;'>Enter health metrics to assess diabetes risk</p>
    </div>
    """, unsafe_allow_html=True)

    pregnancies = st.number_input("Pregnancies", min_value=0, step=1, key="pregnancies")
    glucose = st.number_input("Glucose Level", min_value=0, key="glucose")
    blood_pressure = st.number_input("Blood Pressure", min_value=0, key="blood_pressure")
    skin_thickness = st.number_input("Skin Thickness", min_value=0, key="skin_thickness")
    insulin = st.number_input("Insulin Level", min_value=0, key="insulin")
    bmi = st.number_input("BMI", min_value=0.0, key="bmi")
    dpf = st.number_input("Diabetes Pedigree Function", min_value=0.0, key="dpf")
    age_diabetes = st.number_input("Age", min_value=1, key="age_diabetes")

    if st.button("🔍 Predict Diabetes", key="predict_diabetes"):
        features = np.array([[pregnancies, glucose, blood_pressure,
                              skin_thickness, insulin, bmi, dpf, age_diabetes]])
        prediction = diabetes_model.predict(features)[0]
        st.success("✅ Positive for Diabetes" if prediction == 1 else "❌ Negative for Diabetes")

# -----------------------------
# Tab 5: Upload Medical Report
# -----------------------------
with tabs[4]:

    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); 
                padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; 
                margin-bottom: 2rem;'>
        <h2 style='color: #2E7D32; margin: 0;'>📄 Medical Report Analyzer</h2>
        <p style='color: #666; margin: 0.5rem 0 0 0;'>Upload PDF or image reports for automated analysis</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_report = st.file_uploader("Upload Report", type=["pdf", "png", "jpg", "jpeg"])
    
    # Manual text input fallback option
    use_manual_input = st.checkbox("📝 Enter report text manually (if OCR fails)", value=False)
    manual_text = ""
    if use_manual_input:
        manual_text = st.text_area("Enter or paste report text here:", height=200, key="manual_report_text")

    if uploaded_report is not None:
        file_type = uploaded_report.type

        if "pdf" in file_type:
            text = extract_text_from_pdf(uploaded_report)
        else:
            text = extract_text_from_image(uploaded_report)
        
        # If OCR failed and no text extracted, show manual input option
        if not text.strip() and not use_manual_input:
            st.warning("⚠️ OCR extraction failed or returned no text. Please check the 'Enter report text manually' option above to input text directly.")
            text = ""  # Clear text so user knows to use manual input
        elif not text.strip() and use_manual_input:
            text = manual_text  # Use manual input if OCR failed
        elif text.strip() and use_manual_input:
            # If both OCR and manual input have text, let user choose or combine
            st.info("💡 Both OCR and manual text are available. Using OCR result. You can edit below if needed.")
            # Allow editing of OCR result
            text = st.text_area("Edit extracted text (or use manual input above):", text, height=300, key="edited_ocr_text")
        else:
            # OCR succeeded, show the text
            st.subheader("📄 Extracted Report Text")
            st.text_area("Report Content", text, height=300, key="ocr_extracted_text")

    elif use_manual_input and manual_text:
        # No file uploaded but manual text provided
        text = manual_text
        st.subheader("📄 Report Text")
        st.text_area("Report Content", text, height=300, key="manual_report_display")
    else:
        text = ""

    # Analyze button - available when text is present (from OCR or manual input)
    if text.strip():
        if st.button("🔍 Analyze Report for Diseases"):
            (
                found_symptoms,
                context_hits,
                lab_notes,
                lab_alerts,
                suggested_diseases,
            ) = extract_report_symptoms(text)

            if context_hits:
                st.markdown("### Context-based insights detected")
                for hit in context_hits:
                    details = f"{hit['label']}: added symptom cues {', '.join(hit['symptoms'])}"
                    diseases = hit.get("diseases")
                    if diseases:
                        details += f" | suggested diseases: {', '.join(diseases)}"
                    st.info(details)

            if lab_notes:
                st.success("\n".join(lab_notes))

            if lab_alerts:
                st.error("\n".join(lab_alerts))

            if suggested_diseases:
                st.markdown("### Suggested diseases from report cues")
                st.warning("; ".join(suggested_diseases))

            if found_symptoms:
                st.write("✅ Symptoms found in report:", ", ".join(found_symptoms))
                results = predict_disease(found_symptoms)
                st.subheader("Prediction Results")
                st.dataframe(results.head(10))

                fig = plot_probabilities(results)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No recognizable symptoms found in the uploaded report. Try adding manual symptoms or adjust the report extraction.")