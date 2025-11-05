# app.py
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool, NullPool
from dotenv import load_dotenv
import os
import uuid
import json
import openai
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from typing import Optional
import pandas as pd

# Import model utilities for forecasting
from model_utils import (
    load_data, list_series, timegpt_forecast, compute_holdout_kpis, prepare_series_df,
    get_overall_stats, get_disease_distribution, get_ward_analysis, get_time_trends,
    get_correlation_analysis, generate_ai_insights
)

load_dotenv()

app = FastAPI(title="PHREWS & Citizen Service Portal")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Setup templates with url_for support
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Load data once on startup (for forecasting)
try:
    DATA_DF = load_data()
except Exception as e:
    DATA_DF = pd.DataFrame()
    print("Failed to load CSV at startup:", e)

# Add url_for function to template context
def url_for(request: Request, endpoint: str, **values):
    """Helper function to generate URLs in templates (similar to Flask's url_for)"""
    if endpoint == "static":
        filename = values.get("filename", "")
        return f"/static/{filename}"
    # Map endpoint names to URLs
    url_map = {
        "home": "/",
        "home1": "/",
        "home2": "/home2",
        "multilingual_bot": "/multilingual_bot",
        "forecast": "/forecast",
        "new_login": "/new_login",
        "logout": "/logout",
        "dashboard": "/dashboard",
        "send_resolved_emails": "/send_resolved_emails",
        "update_ticket": "/update_ticket",
        "login": "/login",
    }
    url = url_map.get(endpoint, f"/{endpoint}")
    # Add query parameters if any
    if values:
        query_string = "&".join([f"{k}={v}" for k, v in values.items()])
        url = f"{url}?{query_string}"
    return url

# Make url_for available to all templates
def get_template_context(request: Request):
    """Get base template context"""
    def url_for_template(endpoint: str, **values):
        """Template helper for url_for"""
        return url_for(request, endpoint, **values)
    return {"request": request, "url_for": url_for_template}

# Secret key for session management
SECRET_KEY = os.urandom(24).hex()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch database variables from environment
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Get DATABASE_URL from environment (preferred method)
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback: Construct from individual components if DATABASE_URL is not set
if not DATABASE_URL and USER and PASSWORD and HOST and PORT and DBNAME:
    DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")
# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL,
                       poolclass=StaticPool,
                       pool_pre_ping=True,
                       pool_reset_on_return="commit",
                       pool_recycle=300,
                       echo=False
                       )

# LLM API Configuration (Generic names - no vendor-specific mentions)
LLM_API_ENDPOINT = os.getenv("LLM_API_ENDPOINT")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_VERSION = os.getenv("LLM_API_VERSION", "2024-05-01-preview")
LLM_DEPLOYMENT_NAME = os.getenv("LLM_DEPLOYMENT_NAME")

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")

# Initialize LLM client
client = openai.AzureOpenAI(
    api_key=LLM_API_KEY,
    api_version=LLM_API_VERSION,
    azure_endpoint=LLM_API_ENDPOINT,
    azure_deployment=LLM_DEPLOYMENT_NAME
)
# Ensure directories exist
os.makedirs(os.path.join(BASE_DIR, 'static/audio'), exist_ok=True)

# Database connection function - Updated for SQLAlchemy
def get_db_connection():
    try:
        return engine.connect()
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# # Initialize database table if not exists
# def init_db():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute('''
#         IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='citizen' AND xtype='U')
#         CREATE TABLE citizen (
#             ticket_id VARCHAR(36) PRIMARY KEY,
#             category VARCHAR(100) NOT NULL,
#             location VARCHAR(255) NOT NULL,
#             description VARCHAR(MAX) NOT NULL,
#             urgency VARCHAR(20) DEFAULT 'Normal',
#             attachment_path VARCHAR(255),
#             citizen_email VARCHAR(100) NOT NULL,
#             created_at DATETIME DEFAULT GETDATE(),
#             status VARCHAR(20) DEFAULT 'Open'
#         )
#         ''')
#         conn.commit()
#     except Exception as e:
#         print(f"Database initialization error: {e}")
#     finally:
#         cursor.close()
#         conn.close()

# # Call init_db at startup
# init_db()



@app.post('/api/new_chat')
async def new_chat(request: Request):
    data = await request.json()
    user_message = data.get('message', '')
    conversation_history = data.get('history', [])
    
    # Enhanced language detection using LLM - returns JSON with language code and voice
    language_detection_response = client.chat.completions.create(
        model="AIB-LLM-GPT4o",
        messages=[
            {"role": "system", "content": """Detect the language of the following text and return a JSON response with the language code and an appropriate Azure Neural Voice code.
            Also understand the query, if the user ask to change the language also do the same process.
            Return ONLY a JSON object in this exact format:
            {
                "language_code": "xx",
                "voice_code": "xx-XX-NameNeural"
            }

            Examples of correct responses:
            - English: {"language_code": "en", "voice_code": "en-US-JennyNeural"}
            - Arabic: {"language_code": "ar", "voice_code": "ar-AE-HamdanNeural"}
            - French: {"language_code": "fr", "voice_code": "fr-FR-DeniseNeural"}
            - Spanish: {"language_code": "es", "voice_code": "es-ES-ElviraNeural"}
            - German: {"language_code": "de", "voice_code": "de-DE-KatjaNeural"}
            - Italian: {"language_code": "it", "voice_code": "it-IT-ElsaNeural"}
            - Portuguese: {"language_code": "pt", "voice_code": "pt-BR-FranciscaNeural"}
            - Dutch: {"language_code": "nl", "voice_code": "nl-NL-ColetteNeural"}
            - Russian: {"language_code": "ru", "voice_code": "ru-RU-SvetlanaNeural"}
            - Chinese: {"language_code": "zh", "voice_code": "zh-CN-XiaoxiaoNeural"}
            - Japanese: {"language_code": "ja", "voice_code": "ja-JP-NanamiNeural"}
            - Korean: {"language_code": "ko", "voice_code": "ko-KR-SunHiNeural"}
            - Hindi: {"language_code": "hi", "voice_code": "hi-IN-SwaraNeural"}
            - Urdu: {"language_code": "ur", "voice_code": "ur-PK-AsadNeural"}
            - Turkish: {"language_code": "tr", "voice_code": "tr-TR-EmelNeural"}

            For any other language, use the pattern: language_code (2 letters) and find an appropriate any one Azure Neural Voice code.
            Return ONLY the JSON, no additional text."""},
            {"role": "user", "content": user_message}
        ],
        temperature=0.0
    )
    
    try:
        # Parse the JSON response from LLM
        language_response = json.loads(language_detection_response.choices[0].message.content.strip())
        detected_language = language_response.get('language_code', 'en')
        print(detected_language)
        voice_code = language_response.get('voice_code', 'en-US-JennyNeural')
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        detected_language = 'en'
        voice_code = 'en-US-JennyNeural'
    
    concise_mode = data.get('concise_mode', False)
    logger.info(f"Preferred language: {detected_language}, Voice: {voice_code}, Concise mode: {concise_mode}")
    
    # Detect language and translate if necessary
    if detected_language == 'ar':
        # Use the LLM client to translate the user message to English
        translation_response = client.chat.completions.create(
            model="AIB-LLM-GPT4o",
            messages=[
                {"role": "system", "content": "Translate the following Arabic text to English. Only give the result."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0
        )
        user_message = translation_response.choices[0].message.content  # Translated message

    # Process with LLM
    conversation_context = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" 
                                       for msg in conversation_history])

    
    # System prompt remains the same
    system_prompt = f"""
You are a government service chatbot helping citizens report issues in their city.
Important: Strictly do not include emoji anywhere.
Understand the language of the user message {detected_language}.
You should reply in the language - {detected_language}.

Start by a warm greeting with ask whether the user wants to report an issue or not.

Follow this conversation flow to collect information:

1. Identify the Service Category from the following options only:
   - Education
   - Electricity
   - Health Services
   - Infrastructure
   - Public Safety
   - Revenue Services
   - Road Maintenance
   - Transport
   - Waste Management
   - Water Supply

2. Based on the selected Service Category, show only the relevant Sub-Categories (be descriptive and help user choose). Use the following mapping:

   **Education**
   - Book Distribution
   - Exam Related

   **Electricity**
   - Billing Issue
   - Connection Problem
   - Billing Complaint

   **Health Services**
   - Ambulance Request
   - Emergency Care

   **Infrastructure**
   - Building Maintenance
   - Bridge Repair

   **Public Safety**
   - Crime Report
   - Fire Emergency
   - Disaster Alert

   **Revenue Services**
   - Birth Certificate
   - Death Certificate
   - Caste Certificate

   **Road Maintenance**
   - Drainage Problem
   - Bridge Repair

   **Transport**
   - Bus Service

   **Waste Management**
   - Bin Placement
   - Drainage Problem

   **Water Supply**
   - Connection Problem
   - Drainage Problem

   If the user mentions something not listed, classify it under "Other".

3. Get the District (broader administrative area)
4. Get the Area (specific neighborhood or locality within the district)
5. Get a detailed description of the issue
6. Determine Priority (High, Normal, Low)
7. Ask for contact Email_ID
8. Ask for Citizen Age Group (18-25, 26-35, 36-45, 46-55, 56-65, 65+)
9. Provide a summary of all the information anywhere and ask for confirmation in the same language used by the user.
10. Only after user confirmation, append a JSON summary at the end WITHOUT ANY LABELS (like "Here is your JSON summary") using this format:

```json
{{
    "language": "[Main conversation language e.g., en, fr]",
    "service_category": "",
    "sub_category": "",
    "district": "",
    "area": "",
    "description": "",
    "priority": "",
    "email": "",
    "citizen_age_group": "",
    "is_complete": true
    }}
    ```

-Very Important: The Json Summary should be must in English only, donot use any other language for all the keys and values. If there any other present convert to English while generating Json Summary.
    11. Tell the user the issue will be resolved within 2 - 3 days.An agent will be assigned to take action in your own words
    12. After one time donot generate the json summary, Just answer the users queries.
    13. Always add one more thing like "Other Category" or "Other subcategory" while asking for these.
    14. Always ask email in the last."""
    
    try:
        response = client.chat.completions.create(
            model="Insureai-GPT-4O",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Previous conversation:\n{conversation_context}\n\nUser message: {user_message}"}
            ],
            temperature=0.5
        )
        
        assistant_response = response.choices[0].message.content

        # If the preferred language is Arabic, translate the response back to Arabic
        if detected_language == 'ar':
            translation_response = client.chat.completions.create(
                model="Insureai-GPT-4O",
                messages=[
                    {"role": "system", "content": """Translate the following English text to Modern standard Arabic. Only give the result.
                     Also give the correct answer in good formatting from Right to left."""},
                    {"role": "user", "content": assistant_response}
                ],
                temperature=0.0
            )
            assistant_response = translation_response.choices[0].message.content  # Translated response
            def wrap_rtl_lines(text: str) -> str:
                RLE = '\u202B'  # Right-to-Left Embedding
                PDF = '\u202C'  # Pop Directional Formatting
                return '\n'.join([f"{RLE}{line}{PDF}" for line in text.split('\n')])

            assistant_response = wrap_rtl_lines(assistant_response)

        json_data = None
        final_response = assistant_response

        # Extract JSON and remove it from visible response
        if '```json' in assistant_response:
            # Split the response into visible part and JSON part
            parts = assistant_response.split('```json')
            visible_response = parts[0].strip()
            json_str = parts[1].split('```')[0].strip()

            try:
                json_data = json.loads(json_str)
                # Map old field names to new ones for backward compatibility
                if 'category' in json_data and 'service_category' not in json_data:
                    json_data['service_category'] = json_data.pop('category')
                if 'urgency' in json_data and 'priority' not in json_data:
                    json_data['priority'] = json_data.pop('urgency')
                if 'location' in json_data:
                    # Try to split location into district and area, or use as district
                    location = json_data.pop('location')
                    if 'district' not in json_data:
                        json_data['district'] = location
                    if 'area' not in json_data:
                        json_data['area'] = ''
                final_response = visible_response
                
                # Remove any trailing JSON-related text that might appear before the block
                final_response = final_response.split('JSON Summary:')[0].strip()
            except json.JSONDecodeError:
                pass

        # Process ticket creation if valid JSON found
        ticket_id = None
        if json_data and json_data.get('is_complete', False):
            ticket_id = create_new_ticket(json_data)
            if ticket_id:
                # Add success message without JSON reference
                final_response = final_response.split('```json')[0].strip()
                if json_data.get('language', 'en').lower() == 'fr':
                    final_response += f"\n\nVotre demande a été envoyée. Votre identifiant de ticket est : {ticket_id}"
                else:
                    final_response += f"\n\nYour request has been submitted. Your ticket ID is: {ticket_id}"
                
                # Send confirmation email
                if json_data.get('email'):
                    send_confirmation_email(
                        json_data.get('email'),
                        ticket_id,
                        json_data
                    )

        # Append the assistant's response to the conversation history
        conversation_history.append({"role": "assistant", "content": assistant_response})

        # After detecting the language
        is_arabic = detected_language == 'ar'  # Flag to indicate if the language is Arabic

        return JSONResponse({
            "response": final_response,
            "conversation_history": conversation_history,
            "is_arabic": is_arabic
        })
    
    except Exception as e:
        print(f"Error processing chat: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


def create_new_ticket(data):
    # Generate ticket ID in the format REQ<number> (e.g., REQ1000, REQ1001, etc.)
    service_category = data.get('service_category') or data.get('category', '')
    
    conn = get_db_connection()
    try:
        # Get the maximum Request_ID number to generate next sequential ID
        # Using regex to extract number from REQ<number> format
        result = conn.execute(text("""
            SELECT MAX(CAST(SUBSTRING("Request_ID" FROM 'REQ([0-9]+)') AS INTEGER))
            FROM service_request_details
            WHERE "Request_ID" ~ '^REQ[0-9]+$'
        """))
        max_id_row = result.fetchone()
        
        if max_id_row and max_id_row[0] is not None:
            next_number = max_id_row[0] + 1
        else:
            next_number = 1000  # Start from REQ1000 if no existing REQ IDs found
        
        request_id = f"REQ{next_number}"
        
        # Insert the new ticket
        conn.execute(text("""
            INSERT INTO service_request_details 
            ("Request_ID", "Created_Timestamp", "Service_Category", "Sub_Category", "Priority", "Status", 
             "District", "Area", "Email_ID", "Channel", "Citizen_Age_Group", "Resolution_Time_Hours", 
             "Escalated", "Assigned_Department", "Worker_Assigned")
            VALUES 
            (:request_id, :created_timestamp, :service_category, :sub_category, :priority, :status,
             :district, :area, :email_id, :channel, :citizen_age_group, :resolution_time_hours,
             :escalated, :assigned_department, :worker_assigned)
        """), {
            "request_id": request_id,
            "created_timestamp": datetime.now(),
            "service_category": service_category,
            "sub_category": data.get('sub_category', ''),
            "priority": data.get('priority') or data.get('urgency', 'Normal'),
            "status": 'Open',
            "district": data.get('district', ''),
            "area": data.get('area', ''),
            "email_id": data.get('email', ''),
            "channel": "Chatbot",
            "citizen_age_group": data.get('citizen_age_group', ''),
            "resolution_time_hours": None,
            "escalated": False,
            "assigned_department": None,
            "worker_assigned": None
        })
        conn.commit()
        return request_id
    except Exception as e:
        print(f"Database error in create_new_ticket: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def send_confirmation_email(to_email, ticket_id, ticket_data):
    try:
        try:
        # Determine the language (default to English if not specified)
            language = ticket_data.get('preferred_language', 'en')
        except:
            language = 'en'
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        
        # Multilingual email subject
        subject = {
            'en': f"Ticket Confirmation: {ticket_id}",
            'fr': f"Confirmation de ticket : {ticket_id}"
        }
        msg['Subject'] = subject.get(language, subject['en'])
        
        # Multilingual email templates
        email_templates = {
            'en': f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px;">Citizen Service Portal - Ticket Confirmation</h2>
                    
                    <p>Thank you for reporting an issue through our Citizen Service Portal. We have received your report and a service agent will review it within 2 business days.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #3498db; margin-top: 0;">Ticket Details</h3>
                        <p><strong>Request ID:</strong> {ticket_id}</p>
                        <p><strong>Service Category:</strong> {ticket_data.get('service_category') or ticket_data.get('category', 'N/A')}</p>
                        <p><strong>Sub-Category:</strong> {ticket_data.get('sub_category', 'N/A')}</p>
                        <p><strong>District:</strong> {ticket_data.get('district', 'N/A')}</p>
                        <p><strong>Area:</strong> {ticket_data.get('area', 'N/A')}</p>
                        <p><strong>Description:</strong> {ticket_data.get('description', 'N/A')}</p>
                        <p><strong>Priority:</strong> {ticket_data.get('priority') or ticket_data.get('urgency', 'Normal')}</p>

                    </div>
                    
                    <p>You can reference this ticket ID in future communications about this issue. If you have any questions or need to provide additional information, please contact our support team.</p>
                    
                    <p>Thank you for helping us improve our city services.</p>
                    
                    <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #777;">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>© 2025 Municipal Government Services</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            'fr': f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px;">Portail des Services aux Citoyens - Confirmation de Ticket</h2>
                    
                    <p>Merci d'avoir signalé un problème via notre Portail des Services aux Citoyens. Nous avons bien reçu votre rapport et un agent de service l'examinera dans les 2 prochains jours ouvrables.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #3498db; margin-top: 0;">Détails du Ticket</h3>
                        <p><strong>Identifiant de la Demande :</strong> {ticket_id}</p>
                        <p><strong>Catégorie de Service :</strong> {ticket_data.get('service_category') or ticket_data.get('category', 'N/A')}</p>
                        <p><strong>Sous-Catégorie :</strong> {ticket_data.get('sub_category', 'N/A')}</p>
                        <p><strong>District :</strong> {ticket_data.get('district', 'N/A')}</p>
                        <p><strong>Zone :</strong> {ticket_data.get('area', 'N/A')}</p>
                        <p><strong>Description :</strong> {ticket_data.get('description', 'N/A')}</p>
                        <p><strong>Priorité :</strong> {ticket_data.get('priority') or ticket_data.get('urgency', 'Normal')}</p>

                    </div>
                    
                    <p>Vous pouvez faire référence à cet identifiant de ticket dans toute communication future concernant ce problème. Si vous avez des questions ou besoin de fournir des informations supplémentaires, veuillez contacter notre équipe de support.</p>
                    
                    <p>Merci de nous aider à améliorer nos services municipaux.</p>
                    
                    <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #777;">
                        <p>Ceci est un message automatique. Veuillez ne pas répondre à cet e-mail.</p>
                        <p>© 2025 Services Municipaux du Gouvernement</p>
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        # Choose the appropriate email template based on language
        email_body = email_templates.get(language, email_templates['en'])
        
        msg.attach(MIMEText(email_body, 'html'))
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            
        print(f"Confirmation email sent to {to_email} for ticket {ticket_id} in {language}")
        return True
        
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        return False

# Predefined agents for each category
AGENTS_BY_CATEGORY = {
    'Roads & Sidewalks': ['Agent1-RS', 'Agent2-RS', 'Agent3-RS'],
    'Water & Sewage': ['Agent1-WP', 'Agent2-WP', 'Agent3-WP'],
    'Trees & Vegetation': ['Agent1-TV', 'Agent2-TV', 'Agent3-TV'],
    'Traffic Light': ['Agent1-TL', 'Agent2-TL', 'Agent3-TL'],
    'Parks & Urban Forestry': ['Agent1-UF', 'Agent2-UF', 'Agent3-UF'],
    'Streets & Traffic': ['Agent1-ST', 'Agent2-ST', 'Agent3-ST']
}

# Session management helper functions
def set_session_cookie(response: Response, key: str, value: str):
    """Set a session cookie"""
    response.set_cookie(key=key, value=value, httponly=True, samesite="lax")

def get_session_cookie(request: Request, key: str) -> Optional[str]:
    """Get a session cookie"""
    return request.cookies.get(key)

def delete_session_cookie(response: Response, key: str):
    """Delete a session cookie"""
    response.delete_cookie(key=key)

# Custom exception for authentication redirects
class AuthenticationRequired(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/new_login"}
        )

# Exception handler for authentication redirects
@app.exception_handler(AuthenticationRequired)
async def authentication_exception_handler(request: Request, exc: AuthenticationRequired):
    return RedirectResponse(url="/new_login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

# Login required dependency
async def login_required(request: Request):
    """Dependency to check if user is logged in"""
    logged_in = get_session_cookie(request, 'logged_in')
    if not logged_in or logged_in != 'true':
        raise AuthenticationRequired()
    return True

# Routes
@app.get('/')
async def home1(request: Request):
    return templates.TemplateResponse('home2.html', get_template_context(request))

@app.get('/forecast', response_class=HTMLResponse)
def forecast_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get('/multilingual_bot')
async def multilingual_bot(request: Request):
    return templates.TemplateResponse('index_new.html', get_template_context(request))

# Forecast API Routes (from main.py)
@app.get("/api/series")
def api_series():
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    return JSONResponse(content={"series": list_series(DATA_DF)})

@app.get("/api/data")
def api_data(unique_id: str = None, n: int = 200):
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    if unique_id:
        s = prepare_series_df(DATA_DF, unique_id).tail(n).copy()
        # Convert date columns to strings for JSON serialization
        if "date" in s.columns:
            s["date"] = s["date"].astype(str)
        return JSONResponse(content={"data": s.to_dict(orient="records")})
    # return head of full DF
    df_head = DATA_DF.head(n).copy()
    # Convert date columns to strings for JSON serialization
    if "date" in df_head.columns:
        df_head["date"] = df_head["date"].astype(str)
    return JSONResponse(content={"data": df_head.to_dict(orient="records")})

@app.post("/api/forecast")
async def api_forecast(payload: dict):
    """
    payload:
    {
      "unique_id": "Ward_001__Dengue",
      "h": 12,
      "external_regressors": ["rainfall_mm","humidity","temperature","citizen_reports","available_beds"],
      "finetune_steps": 20
    }
    """
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    unique_id = payload.get("unique_id")
    h = int(payload.get("h", 12))
    ext = payload.get("external_regressors", [])  # Default to empty list - no exogenous variables
    finetune = int(payload.get("finetune_steps", 0))
    if not unique_id:
        raise HTTPException(status_code=400, detail="unique_id required")
    # call model with auto-selected exogenous variables for better accuracy
    try:
        # Enable auto-selection of relevant exogenous variables
        preds = timegpt_forecast(DATA_DF, unique_id, h=h, external_regs=ext, finetune_steps=finetune, auto_select_vars=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {e}")
    # return prediction and a small slice of history
    history_df = prepare_series_df(DATA_DF, unique_id).tail(52)[["date","new_cases"]].copy()
    # Convert date columns to strings for JSON serialization
    history_df["date"] = history_df["date"].astype(str)
    history = history_df.to_dict(orient="records")
    
    # Convert forecast dates to strings
    preds_copy = preds.copy()
    if "date" in preds_copy.columns:
        preds_copy["date"] = preds_copy["date"].astype(str)
    
    # Generate AI insights
    try:
        series_df = prepare_series_df(DATA_DF, unique_id)
        # Use same exogenous variables as the main forecast
        def forecast_fn_for_insights(train_df, h_local):
            df_train = train_df.copy()
            if "unique_id" not in df_train.columns:
                df_train["unique_id"] = df_train["ward_id"] + "__" + df_train["disease_type"]
            # Enable auto-selection of relevant exogenous variables
            return timegpt_forecast(df_train, df_train["unique_id"].iloc[0], h=h_local, 
                                  external_regs=ext, finetune_steps=finetune, auto_select_vars=True)
        kpis_for_insights = compute_holdout_kpis(series_df, forecast_fn_for_insights, h=min(h, 8))
        insights = generate_ai_insights(series_df, preds, kpis_for_insights)
    except Exception as e:
        logging.warning(f"Failed to generate insights: {e}")
        insights = {"trend_analysis": [], "forecast_insights": [], "risk_assessment": [], "recommendations": []}
    
    return JSONResponse(content={
        "history": history, 
        "forecast": preds_copy.to_dict(orient="records"),
        "insights": insights    
    })

@app.get("/api/kpis")
def api_kpis(unique_id: str, h: int = 8, finetune_steps: int = 10):
    """
    Compute holdout KPIs using a simple internal evaluate function based on finetune_steps.
    """
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    s = prepare_series_df(DATA_DF, unique_id)
    # wrapper forecast_fn to connect with model_utils.compute_holdout_kpis
    def forecast_fn(train_df, h_local):
        # call TimeGPT with finetune on train_df only
        # Nixtla client wrapper expects the whole dataset normally; for quick evaluation we can call the model_utils.timegpt_forecast on the global DF but restrict
        # As a pragmatic approach, we'll create a small df identical to train format but with unique_id only for this series
        df_train = train_df.copy()
        # add required columns if missing
        if "unique_id" not in df_train.columns:
            df_train["unique_id"] = df_train["ward_id"] + "__" + df_train["disease_type"]
        return timegpt_forecast(df_train, df_train["unique_id"].iloc[0], h=h_local, external_regs=[], finetune_steps=finetune_steps, auto_select_vars=False)
    kpis = compute_holdout_kpis(s, forecast_fn, h=h)
    # additional simple data KPIs
    last_week = int(s["new_cases"].iloc[-1])
    avg_12 = float(s["new_cases"].tail(12).mean())
    return JSONResponse(content={"kpis": kpis, "last_week_cases": last_week, "avg_last_12_weeks": avg_12})

@app.get("/api/overall-stats")
def api_overall_stats():
    """Get overall statistics for the dataset."""
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    stats = get_overall_stats(DATA_DF)
    return JSONResponse(content=stats)

@app.get("/api/disease-distribution")
def api_disease_distribution():
    """Get disease type distribution."""
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    distribution = get_disease_distribution(DATA_DF)
    return JSONResponse(content=distribution)

@app.get("/api/ward-analysis")
def api_ward_analysis(top_n: int = 10):
    """Get top wards by total cases."""
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    analysis = get_ward_analysis(DATA_DF, top_n=top_n)
    return JSONResponse(content=analysis)

@app.get("/api/time-trends")
def api_time_trends(period: str = "weekly"):
    """Get time-based trends (weekly or monthly)."""
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    trends = get_time_trends(DATA_DF, period=period)
    return JSONResponse(content=trends)

@app.get("/api/correlations")
def api_correlations():
    """Get correlations between new_cases and external regressors."""
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    correlations = get_correlation_analysis(DATA_DF)
    return JSONResponse(content=correlations)

@app.post("/api/insights")
async def api_insights(payload: dict):
    """Generate AI insights for a forecast."""
    if DATA_DF.empty:
        raise HTTPException(status_code=500, detail="Data not loaded.")
    unique_id = payload.get("unique_id")
    if not unique_id:
        raise HTTPException(status_code=400, detail="unique_id required")
    
    h = int(payload.get("h", 12))
    finetune = int(payload.get("finetune_steps", 0))
    
    # Get forecast
    try:
        preds = timegpt_forecast(DATA_DF, unique_id, h=h, finetune_steps=finetune)
        series_df = prepare_series_df(DATA_DF, unique_id)
        
        # Get KPIs for insights
        def forecast_fn(train_df, h_local):
            df_train = train_df.copy()
            if "unique_id" not in df_train.columns:
                df_train["unique_id"] = df_train["ward_id"] + "__" + df_train["disease_type"]
            return timegpt_forecast(df_train, df_train["unique_id"].iloc[0], h=h_local, 
                                  external_regs=[], finetune_steps=finetune, auto_select_vars=False)
        kpis = compute_holdout_kpis(series_df, forecast_fn, h=min(h, 8))
        
        # Generate insights
        insights = generate_ai_insights(series_df, preds, kpis)
        
        return JSONResponse(content=insights)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {e}")

@app.get('/admin')
async def admin_index():
    return RedirectResponse(url="/new_login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.get('/new_login')
async def new_login_get(request: Request):
    # Get flash messages from query params
    error = request.query_params.get('error', '')
    context = get_template_context(request)
    context['error'] = error
    context['success'] = request.query_params.get('success', '')
    return templates.TemplateResponse('new_login.html', context)

@app.post('/new_login')
async def new_login_post(request: Request):
    form_data = await request.form()
    username = form_data.get('username')
    password = form_data.get('password')
    
    # Simple admin authentication (in production, use a more secure method)
    if username == 'admin@maharashtra.gov.in' and password == 'admin123':
        # Create redirect response and set cookies on it
        redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        set_session_cookie(redirect_response, 'logged_in', 'true')
        set_session_cookie(redirect_response, 'username', username)
        return redirect_response
    else:
        # Flash messages are not built-in in FastAPI, using query params instead
        # Use 303 to force GET request
        return RedirectResponse(url="/new_login?error=Invalid+credentials.+Please+try+again.", status_code=status.HTTP_303_SEE_OTHER)

@app.get('/logout')
async def logout():
    # Create redirect response and delete cookies on it
    redirect_response = RedirectResponse(url="/new_login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    delete_session_cookie(redirect_response, 'logged_in')
    delete_session_cookie(redirect_response, 'username')
    return redirect_response

@app.get('/dashboard')
async def dashboard(request: Request, authenticated: bool = Depends(login_required)):
    # Get filters from request args
    category = request.query_params.get('category', '')
    status_filter = request.query_params.get('status', '')
    date_from = request.query_params.get('date_from', '')
    date_to = request.query_params.get('date_to', '')
    priority = request.query_params.get('priority', '') or request.query_params.get('urgency', '')  # Support both for backward compatibility
    agent = request.query_params.get('agent', '')
    selected_lang = request.query_params.get('lang', get_session_cookie(request, 'lang') or 'en')
    
    conn = get_db_connection()

    query = """
        SELECT "Request_ID", "Service_Category", "Sub_Category", "Priority", "Status", 
               "District", "Area", "Email_ID", "Created_Timestamp", "Worker_Assigned", "Assigned_Department"
        FROM service_request_details
        WHERE 1=1
    """
    # Add filters
    if category:
        query += f' AND "Service_Category" = \'{category}\''
    if status_filter:
        query += f' AND "Status" = \'{status_filter}\''
    if date_from:
        query += f' AND "Created_Timestamp" >= \'{date_from}\''
    if date_to:
        query += f' AND "Created_Timestamp" <= \'{date_to}\''
    if priority:
        query += f' AND "Priority" = \'{priority}\''
    if agent:
        query += f' AND "Worker_Assigned" = \'{agent}\''
    
    # Order by Created_Timestamp descending (newest first)
    query += ' ORDER BY "Created_Timestamp" DESC'
    
    cursor = conn.execute(text(query))
    # Convert Row objects to dictionaries for easier template access
    columns = ["Request_ID", "Service_Category", "Sub_Category", "Priority", "Status", 
                "District", "Area", "Email_ID", "Created_Timestamp", "Worker_Assigned", "Assigned_Department"]
    tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Get all categories for the filter dropdown
    cursor = conn.execute(text('SELECT DISTINCT "Service_Category" FROM service_request_details'))
    categories = [row[0] for row in cursor.fetchall()]
    
    # Get all agents for the filter dropdown
    cursor = conn.execute(text('SELECT DISTINCT "Worker_Assigned" FROM service_request_details WHERE "Worker_Assigned" IS NOT NULL'))
    all_agents = [row[0] for row in cursor.fetchall() if row[0]]
    all_agents = sorted(list(set(all_agents)))
    
    # Count tickets by status
    cursor = conn.execute(text('SELECT "Status", COUNT(*) as count FROM service_request_details GROUP BY "Status"'))
    status_counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get counts for the dashboard cards - check both "New" and "Open" for new tickets
    new_count = status_counts.get('New', 0) + status_counts.get('Open', 0)
    in_progress_count = status_counts.get('In-Progress', 0)
    escalated_count = status_counts.get('Escalated', 0)
    resolved_count = status_counts.get('Resolved', 0)
    
    conn.close()
    
    # Get flash messages from query params
    success_msg = request.query_params.get('success', '')
    error_msg = request.query_params.get('error', '')
    info_msg = request.query_params.get('info', '')
    
    context = get_template_context(request)
    context.update({
        "selected_lang": selected_lang,
        "tickets": tickets,
        "categories": categories,
        "all_agents": all_agents,
        "agents_by_category": AGENTS_BY_CATEGORY,
        "new_count": new_count,
        "in_progress_count": in_progress_count,
        "escalated_count": escalated_count,
        "resolved_count": resolved_count,
        "selected_category": category,
        "selected_status": status_filter,
        "selected_priority": priority,
        "selected_urgency": priority,  # Keep for backward compatibility
        "selected_agent": agent,
        "date_from": date_from,
        "date_to": date_to,
        "success_msg": success_msg,
        "error_msg": error_msg,
        "info_msg": info_msg
    })
    template_response = templates.TemplateResponse('dashboard.html', context)
    # Set cookie for lang if needed
    if selected_lang:
        template_response.set_cookie(key='lang', value=selected_lang)
    return template_response

@app.post('/update_ticket')
async def update_ticket(request: Request, authenticated: bool = Depends(login_required)):
    form_data = await request.form()
    request_id = form_data.get('ticket_id')  # This is actually Request_ID now
    new_status = form_data.get('status')
    assigned_worker = form_data.get('assigned_agent', '')
    assigned_department = form_data.get('assigned_department', '')
    
    conn = get_db_connection()
    try:
        conn.execute(text("""
            UPDATE service_request_details 
            SET "Status" = :status, 
                "Worker_Assigned" = :worker_assigned,
                "Assigned_Department" = :assigned_department
            WHERE "Request_ID" = :request_id
        """), {
            "status": new_status,
            "worker_assigned": assigned_worker or None,
            "assigned_department": assigned_department or None,
            "request_id": request_id
        })
        conn.commit()
        # Flash messages are not built-in in FastAPI, using query params instead
        # Use 303 to force GET request after POST
        return RedirectResponse(url=f"/dashboard?success=Request+%23{request_id}+updated+successfully.", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error updating ticket: {e}")
        conn.rollback()
        # Use 303 to force GET request after POST
        return RedirectResponse(url=f"/dashboard?error=Error+updating+request%3A+{str(e).replace(' ', '+')}", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        conn.close()
    
@app.get('/send_resolved_emails')
async def send_resolved_emails(request: Request, authenticated: bool = Depends(login_required)):
    conn = get_db_connection()
    try:
        cursor = conn.execute(text("""
            SELECT "Request_ID", "Service_Category", "Sub_Category", "District", "Area", "Email_ID", "Worker_Assigned", "Assigned_Department"
            FROM service_request_details
            WHERE "Status" = 'Resolved' AND ("Email_ID" IS NOT NULL AND "Email_ID" != '')
        """))
        # Convert Row objects to dictionaries
        columns = ["Request_ID", "Service_Category", "Sub_Category", "District", "Area", "Email_ID", "Worker_Assigned", "Assigned_Department"]
        resolved_tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        email_count = 0
        for ticket in resolved_tickets:
            subject = f"Your Request #{ticket['Request_ID']} Has Been Resolved"
            body = f"""
            <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #fff; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <h2 style="color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px;">Request Resolution Notification</h2>
                
                <p>Dear Citizen,</p>
                <p>We are pleased to inform you that your request <strong>#{ticket['Request_ID']}</strong> has been resolved.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; border: 1px solid #ddd;">
                    <p><strong>Service Category:</strong> {ticket.get('Service_Category') or 'N/A'}</p>
                    <p><strong>Sub-Category:</strong> {ticket.get('Sub_Category') or 'N/A'}</p>
                    <p><strong>District:</strong> {ticket.get('District') or 'N/A'}</p>
                    <p><strong>Area:</strong> {ticket.get('Area') or 'N/A'}</p>
                    <p><strong>Resolved by:</strong> {ticket.get('Worker_Assigned') or 'Support Team'}</p>
                    <p><strong>Department:</strong> {ticket.get('Assigned_Department') or 'N/A'}</p>
                </div>
                
                <p>Thank you for reporting this issue. If you have any other questions or if the problem persists, please do not hesitate to contact us.</p>
                
                <p>Best regards,<br><strong>Citizen Support Team</strong></p>
                
                <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #777;">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>© 2025 Municipal Government Services</p>
                </div>
            </div>
        </body>
    </html>
            """
            
            try:
                msg = MIMEMultipart()
                msg['From'] = FROM_EMAIL
                msg['To'] = ticket.get('Email_ID')
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'html'))
                
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                email_count += 1
            except Exception as e:
                print(f"Error sending email for request #{ticket.get('Request_ID', 'Unknown')}: {str(e)}")
        
        if email_count > 0:
            # Use 303 to force GET request (even though this is already GET, it's good practice)
            return RedirectResponse(url=f"/dashboard?success=Successfully+sent+{email_count}+resolution+notification+emails.", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/dashboard?info=No+resolved+requests+with+valid+email+addresses+to+send+notifications+for.", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error in send_resolved_emails: {e}")
        return RedirectResponse(url=f"/dashboard?error=Error%3A+{str(e).replace(' ', '+')}", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        conn.close()

if __name__ == '__main__':
    # Make sure the ticket_assignments table exists
    # conn = get_db_connection()
    # cursor = conn.execute(text("""
    #     IF NOT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = 'ticket_assignments')
    #     CREATE TABLE ticket_assignments (
    #         assignment_id SERIAL PRIMARY KEY,
    #         ticket_id VARCHAR(MAX) NOT NULL,
    #         agent_name VARCHAR(100) NOT NULL,
    #         assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     )
    # """))
    # conn.commit()

    # # Add email_sent column to citizen table if it doesn't exist
    # cursor = conn.execute(text("""
    #     ALTER TABLE citizen ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE
    # """))
    # conn.commit()

    # conn = get_db_connection()
    # cursor = conn.cursor()
    # cursor.execute("UPDATE [dbo].[citizen] SET email_sent = 0 WHERE email_sent IS NULL")
    # conn.commit()
    # conn.close()
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)