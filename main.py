"""
FastAPI backend for Wildcard Platform.
Provides API endpoints for alerts, feedback, forecasting, and multilingual chatbot.
"""

from fastapi import FastAPI, Request, HTTPException, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import math
import json
import pandas as pd
import os
import uuid
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import chatbot service and utilities
from services.chatbot_service import ChatbotService
from agents.tools.database_tool import get_districts
from metrics.p_score import get_comprehensive_p_score

# Import forecasting model utilities
try:
    from model_utils import (
        load_data, list_series, timegpt_forecast, compute_holdout_kpis, prepare_series_df,
        get_overall_stats, get_disease_distribution, get_ward_analysis, get_time_trends,
        get_correlation_analysis, generate_ai_insights
    )
    FORECAST_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Forecasting utilities not available: {e}")
    FORECAST_AVAILABLE = False

# Import Azure OpenAI and Speech SDK for multilingual chatbot
try:
    import openai
    import azure.cognitiveservices.speech as speechsdk
    MULTILINGUAL_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Multilingual chatbot dependencies not available: {e}")
    MULTILINGUAL_AVAILABLE = False

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wildcard Platform - Smart Governance")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates - index.html is in static/templates/
templates = Jinja2Templates(directory="static/templates")

# Initialize chatbot service (singleton)
chatbot_service = ChatbotService()

# Global data storage for workforce allocation
workforce_df = None
worker_data = None
worker_data_cache = {}  # Cache for processed worker data to speed up API responses

# Global data storage for forecasting
DATA_DF = pd.DataFrame()

# LLM API Configuration for multilingual chatbot
LLM_API_ENDPOINT = os.getenv("LLM_API_ENDPOINT")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_VERSION = os.getenv("LLM_API_VERSION", "2024-05-01-preview")
LLM_DEPLOYMENT_NAME = os.getenv("LLM_DEPLOYMENT_NAME")

# Speech Service Configuration
SPEECH_SERVICE_API_KEY = os.getenv("SPEECH_SERVICE_API_KEY")
SPEECH_SERVICE_REGION = os.getenv("SPEECH_SERVICE_REGION")

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")

# Initialize OpenAI client for multilingual chatbot
openai_client = None
if MULTILINGUAL_AVAILABLE and LLM_API_KEY:
    try:
        openai_client = openai.AzureOpenAI(
            api_key=LLM_API_KEY,
            api_version=LLM_API_VERSION,
            azure_endpoint=LLM_API_ENDPOINT,
            azure_deployment=LLM_DEPLOYMENT_NAME
        )
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {e}")

# Ensure directories exist
os.makedirs('static/audio', exist_ok=True)


def get_current_date():
    """Get formatted current date."""
    return datetime.now().strftime("%A, %B %d, %Y")


def sanitize_for_json(obj):
    """
    Recursively sanitize data structure to make it JSON-compliant.
    Converts NaN, Infinity, and -Infinity to None or strings.
    """
    if isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj):
            return None
        elif math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (int, str, bool)) or obj is None:
        return obj
    else:
        # Convert other types to string
        return str(obj)


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Serve the landing page."""
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request
        }
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request
        }
    )


@app.post('/login')
async def login_post(request: Request):
    """Handle login form submission and redirect based on user type."""
    from fastapi import status
    from fastapi.responses import RedirectResponse
    
    form_data = await request.form()
    
    # Get credentials from either admin or citizen form fields
    admin_email = form_data.get('adminEmail')
    admin_password = form_data.get('adminPassword')
    citizen_id = form_data.get('citizenId')
    citizen_password = form_data.get('citizenPassword')
    
    # Also check generic fields for compatibility
    username = form_data.get('username')
    password = form_data.get('password')
    
    # Debug logging
    logging.info(f"Login attempt - adminEmail: {admin_email}, citizenId: {citizen_id}, username: {username}")
    
    # Check if admin login (prioritize admin form fields)
    if (admin_email and admin_password and admin_email == 'admin@mahaseva.gov' and admin_password == 'admin123') or \
       (username == 'admin@mahaseva.gov' and password == 'admin123'):
        # Admin login - redirect to admin dashboard
        redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        # Clear old cookies first
        redirect_response.delete_cookie(key='logged_in')
        redirect_response.delete_cookie(key='user_type')
        redirect_response.delete_cookie(key='username')
        # Set new admin cookies
        redirect_response.set_cookie(key='logged_in', value='true', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='user_type', value='admin', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='username', value='admin@mahaseva.gov', httponly=True, samesite="lax", max_age=86400)
        logging.info(f"✅ Admin login successful - redirecting to /dashboard")
        return redirect_response
    # Citizen login - accept any email and password
    elif (citizen_id and citizen_password) or (username and password):
        # Citizen login - redirect to citizen dashboard
        final_username = citizen_id or username
        redirect_response = RedirectResponse(url="/citizen_dashboard", status_code=status.HTTP_303_SEE_OTHER)
        # Clear old cookies first
        redirect_response.delete_cookie(key='logged_in')
        redirect_response.delete_cookie(key='user_type')
        redirect_response.delete_cookie(key='username')
        # Set new citizen cookies
        redirect_response.set_cookie(key='logged_in', value='true', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='user_type', value='citizen', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='username', value=final_username, httponly=True, samesite="lax", max_age=86400)
        logging.info(f"✅ Citizen login successful: {final_username} - redirecting to /citizen_dashboard")
        return redirect_response
    else:
        # Redirect back with error message
        logging.warning("❌ Login failed - no credentials provided")
        return RedirectResponse(url="/login?error=Please+enter+valid+credentials.", status_code=status.HTTP_303_SEE_OTHER)


@app.get('/new_login', response_class=HTMLResponse)
async def new_login_get(request: Request):
    """Serve the new login page."""
    # Get flash messages from query params
    error = request.query_params.get('error', '')
    success = request.query_params.get('success', '')
    return templates.TemplateResponse(
        'new_login.html',
        {
            "request": request,
            "error": error,
            "success": success
        }
    )


@app.post('/new_login')
async def new_login_post(request: Request):
    """Handle new login form submission."""
    from fastapi import status
    from fastapi.responses import RedirectResponse
    
    form_data = await request.form()
    username = form_data.get('username')
    password = form_data.get('password')
    
    # Check if admin login
    if username == 'admin@mahaseva.gov' and password == 'admin123':
        # Create redirect response and set cookies
        redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        # Clear old cookies first, then set new ones
        redirect_response.delete_cookie(key='logged_in')
        redirect_response.delete_cookie(key='user_type')
        redirect_response.delete_cookie(key='username')
        # Set new admin cookies
        redirect_response.set_cookie(key='logged_in', value='true', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='user_type', value='admin', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='username', value=username, httponly=True, samesite="lax", max_age=86400)
        logging.info(f"Admin login successful: {username}")
        return redirect_response
    # Citizen login - accept any email and password (for demo purposes)
    elif username and password:
        # Citizen login - redirect to citizen dashboard
        redirect_response = RedirectResponse(url="/citizen_dashboard", status_code=status.HTTP_303_SEE_OTHER)
        # Clear old cookies first, then set new ones
        redirect_response.delete_cookie(key='logged_in')
        redirect_response.delete_cookie(key='user_type')
        redirect_response.delete_cookie(key='username')
        # Set new citizen cookies
        redirect_response.set_cookie(key='logged_in', value='true', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='user_type', value='citizen', httponly=True, samesite="lax", max_age=86400)
        redirect_response.set_cookie(key='username', value=username, httponly=True, samesite="lax", max_age=86400)
        logging.info(f"Citizen login successful: {username}")
        return redirect_response
    else:
        # Redirect back with error message
        return RedirectResponse(url="/new_login?error=Please+enter+email+and+password.", status_code=status.HTTP_303_SEE_OTHER)


@app.get('/logout')
async def logout(request: Request):
    """Handle user logout and clear cookies."""
    from fastapi import status
    from fastapi.responses import RedirectResponse
    
    # Create redirect response and delete cookies
    redirect_response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    redirect_response.delete_cookie(key='logged_in')
    redirect_response.delete_cookie(key='user_type')
    redirect_response.delete_cookie(key='username')
    
    logging.info("User logged out successfully")
    return redirect_response


@app.get("/citizen_dashboard", response_class=HTMLResponse)
async def citizen_dashboard_page(request: Request):
    """Serve the citizen dashboard page."""
    from fastapi.responses import HTMLResponse
    
    # Get user info from cookies
    username = request.cookies.get('username', 'Citizen')
    user_type = request.cookies.get('user_type', 'citizen')
    
    # Verify it's a citizen login
    if user_type != 'citizen':
        from fastapi import status
        from fastapi.responses import RedirectResponse
        logging.warning(f"Non-citizen user tried to access citizen dashboard: {username}")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
    # Log for debugging
    logging.info(f"Citizen dashboard accessed - username: {username}")
    
    # Create response with no-cache headers
    response = templates.TemplateResponse(
        "citizen_dashboard.html",
        {
            "request": request,
            "current_date": get_current_date(),
            "username": username
        }
    )
    
    # Add cache control headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the admin dashboard HTML page with sidebar navigation."""
    from fastapi.responses import HTMLResponse
    
    # Get user type from cookies
    user_type = request.cookies.get('user_type', 'admin')
    username = request.cookies.get('username', 'User')
    
    # Log for debugging
    logging.info(f"Dashboard accessed - user_type: {user_type}, username: {username}")
    
    # Create response with no-cache headers to prevent browser caching
    response = templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_date": get_current_date(),
            "user_type": user_type,
            "username": username
        }
    )
    
    # Add cache control headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response


# Define alert and feedback data - shared across endpoints
ALL_ALERTS_DATA = [
    {
        "id": 1,
        "title": "Water Pipeline Rupture & Contamination - Nashik Zone 3",
        "severity": "CRITICAL",
        "description": "Major water pipeline failure detected near the Old Civil Hospital, disrupting supply to 75,000 residents. Real-time sensor data shows immediate drop in pressure and a 12% spike in coliform count downstream.",
        "timestamp": "1 hour ago",
        "status": "Active",
        "actionable_intelligence": "Predictive Model: Anomaly detection on flow/pressure sensors (IoT) combined with water quality monitoring (BigQuery). Prescribed Action: Immediate isolation of Zone 3 supply. Dispatch Health Task Force for emergency water purification and boiling advisories."
    },
    {
        "id": 2,
        "title": "Dengue Fever Cluster - Pimpri-Chinchwad Ward 8",
        "severity": "CRITICAL",
        "description": "52 confirmed Dengue cases logged in primary health centers (PHCs) in the last 48 hours. The density is 8x the critical threshold. High-risk zones identified near stagnant construction sites.",
        "timestamp": "3 hours ago",
        "status": "Active",
        "actionable_intelligence": "Predictive Model: Geospatial-temporal model correlating PHC data with climate and vector density. Prescribed Action: Mobilize District Medical Officer (DMO) and Sanitation Task Force. Launch targeted fogging and public awareness drives in a 2 km radius."
    },
    {
        "id": 3,
        "title": "High Collision Probability: Samruddhi Expressway (Km 350-360)",
        "severity": "WARNING",
        "description": "High traffic density combined with aggressive driving behavior (lane changes, over-speeding) has resulted in a 75% elevated risk score for a chain-reaction collision in the next 4 hours.",
        "timestamp": "2 hours ago",
        "status": "Active",
        "actionable_intelligence": "Predictive Model: Highway Safety Model (Vertex AI) using ANPR and telemetry data to track speed variance and hard braking events. Prescribed Action: Dispatch 3 additional Highway Patrol Units to the 10km corridor. Activate Variable Message Sign (VMS) boards immediately."
    },
    {
        "id": 4,
        "title": "Electricity Grid Instability - Pune Industrial Belt",
        "severity": "WARNING",
        "description": "Predictive model forecasts a 20% probability of cascading power grid failure within 12 hours due to sustained high load (peak industrial demand) and minor fault reports in 4 sub-stations. Risk Score: 65/100.",
        "timestamp": "5 hours ago",
        "status": "Acknowledged",
        "actionable_intelligence": "Predictive Model: Load Forecasting Model correlating historical consumption, weather, and current minor fault logs. Prescribed Action: Grid Operator has acknowledged the alert. Initiate a controlled, rotating, non-essential load shedding (Level 1) for 4 hours to stabilize the grid and reduce risk."
    },
    {
        "id": 5,
        "title": "Service Backlog Prevented - Property Tax Processing",
        "severity": "INFO",
        "description": "The backlog risk in property tax processing was mitigated by deploying a temporary AI document processor over the weekend. The risk of missing the monthly processing deadline (5000+ files) dropped from 85 to 10.",
        "timestamp": "1 day ago",
        "status": "Resolved",
        "actionable_intelligence": "System Triage: Prioritization Engine detected the resource gap and initiated a process automation agent (Gemini/Vertex AI) to clear the queue. Action: Logged as a successful AI intervention; resources returned to routine tasks."
    },
    {
        "id": 6,
        "title": "Sewage Pumping Station (SPS) Failure - Deccan Gymkhana",
        "severity": "CRITICAL",
        "description": "Pumping Station SPS-3 reported a major blockage and flow anomaly. Untreated sewage is overflowing into the storm drainage system, creating a public health emergency risk (Cholera/Typhoid) in the densely populated area.",
        "timestamp": "30 minutes ago",
        "status": "Active",
        "actionable_intelligence": "Correlation Engine immediately cross-verified the citizen complaint location (Twitter post) with the nearest SPS sensor data, detecting a 75% overcapacity alarm. Pressure Anomaly: 4x Normal. System Action: Dispatched Emergency Maintenance Team (EMT). Pre-booked one tanker of disinfectant. Generated a public health advisory drafted for local release. Status set to emergency level that bypasses standard work order queues."
    }
]

ALL_FEEDBACK_DATA = [
    {
        "id": 1,
        "title": "Negative Sentiment Cluster: Police Responsiveness: CRITICAL Needs Review",
        "severity": "CRITICAL",
        "description": "A surge of 32 social media posts and 7 registered grievances in the last 6 hours indicate significant dissatisfaction with the response time of police patrol units in Ward 14.",
        "timestamp": "6 hours ago",
        "status": "Active",
        "sentiment": "negative",
        "insight": "Gemini Output: Summarization and Topic Modeling identified a distinct, rapidly growing complaint topic. Decision: The Police Commissioner needs to review patrol logs and deploy a new community liaison officer."
    },
    {
        "id": 2,
        "title": "Emerging Infrastructure Gap (Roads): WARNING Review Needed",
        "severity": "WARNING",
        "description": "Citizen feedback shows a concentrated complaint pattern (18 complaints) about the poor condition of the NH-66 feeder road. The road is not due for maintenance until Q3.",
        "timestamp": "8 hours ago",
        "status": "Active",
        "sentiment": "negative",
        "insight": "Gemini Output: Geospatial clustering of complaint locations, cross-referenced with the Public Works Department schedule. Decision: Initiate an emergency pre-inspection to prevent the road from becoming a Critical infrastructure failure."
    },
    {
        "id": 3,
        "title": "Scheme Eligibility Confusion: INFO Acknowledged",
        "severity": "INFO",
        "description": "Automated analysis of the government portal's chat logs indicates citizens are confused about the eligibility criteria for the new Farmers' Subsidy Scheme. The confusion is across 4 regional languages.",
        "timestamp": "12 hours ago",
        "status": "Acknowledged",
        "sentiment": "neutral",
        "insight": "Gemini Output: Identified a persistent confusion topic from chat log summarization, despite a clear FAQ. Decision: Policy team has acknowledged and is revising the scheme's public-facing text using a simplified Gemini-generated draft for clarity."
    },
    {
        "id": 4,
        "title": "Positive Feedback Spike - Health Clinic: INFO Resolved",
        "severity": "INFO",
        "description": "Post-service surveys show a 20% jump in positive patient feedback at the 'Jeevan Raksha Clinic' after the implementation of a new digital queue system.",
        "timestamp": "1 day ago",
        "status": "Resolved",
        "sentiment": "positive",
        "insight": "Gemini Output: Sentiment Analysis on survey text identified the digital queue system as the primary driver of satisfaction. Decision: This best practice is to be shared and scaled to three other district clinics."
    },
    {
        "id": 5,
        "title": "Sewage Overflow Public Health Hazard - Deccan Gymkhana, Pune",
        "severity": "CRITICAL",
        "description": "Twitter (X) Post, Geo-Tagged: \"Sewage overflowing onto the main road near Deccan Gymkhana, Pune. The smell is unbearable. Water getting mixed with drain water! @PuneMahaGovt\" Location: Deccan Gymkhana, Pune (Lat/Long: 18.5204° N, 73.8567° E)",
        "timestamp": "30 minutes ago",
        "status": "Active",
        "sentiment": "critical_urgent",
        "insight": "NLP/Sentiment Engine flagged the keywords \"overflowing,\" \"unbearable,\" and \"mixed with drain water\" as a high-priority public health hazard. Sentiment Score: -0.98. Geospatial correlation linked the complaint location to a Primary Health Centre (PHC) zone and a major Sewage Pumping Station (SPS). This citizen report triggered automatic alert generation when it coincided with sensor threshold breach."
    }
]

@app.get("/api/metrics")
async def get_metrics():
    """Get dashboard metrics with dynamic counts from actual data."""
    # Calculate counts from actual data
    active_alerts = len([a for a in ALL_ALERTS_DATA if a.get("status") == "Active"])  # Should be 4
    critical_alerts = len([a for a in ALL_ALERTS_DATA if a.get("status") == "Active" and a.get("severity") == "CRITICAL"])  # Should be 3
    
    total_feedback_count = 125  # Total volume of citizen service logs/social mentions
    
    return JSONResponse(content={
        "active_alerts": active_alerts,  # Count of alerts with status "Active" (4)
        "critical_issues": critical_alerts,  # Count of active critical alerts (3)
        "total_feedback": total_feedback_count,  # Total citizen service logs/social mentions
        "positive_sentiment": "45%",  # Current public satisfaction trend
        "alerts_count": len(ALL_ALERTS_DATA),  # Total alerts for tab badge (6)
        "feedback_count": len(ALL_FEEDBACK_DATA)  # Total feedback items for tab badge (5)
    })


@app.get("/api/alerts")
async def get_alerts(
    severity: Optional[str] = "All",
    status: Optional[str] = "All"
):
    """Get alerts with optional filtering."""
    # Use shared alerts data
    all_alerts = ALL_ALERTS_DATA.copy()
    
    # Filter alerts
    filtered_alerts = all_alerts
    if severity and severity != "All":
        filtered_alerts = [a for a in filtered_alerts if a["severity"].upper() == severity.upper()]
    if status and status != "All":
        filtered_alerts = [a for a in filtered_alerts if a["status"].upper() == status.upper()]
    
    return JSONResponse(content={"alerts": filtered_alerts})


@app.get("/api/feedback")
async def get_feedback(
    severity: Optional[str] = "All",
    status: Optional[str] = "All"
):
    """Get citizen feedback with optional filtering."""
    # Use shared feedback data
    all_feedback = ALL_FEEDBACK_DATA.copy()
    
    # Filter feedback
    filtered_feedback = all_feedback
    if severity and severity != "All":
        filtered_feedback = [f for f in filtered_feedback if f["severity"].upper() == severity.upper()]
    if status and status != "All":
        filtered_feedback = [f for f in filtered_feedback if f["status"].upper() == status.upper()]
    
    return JSONResponse(content={"feedback": filtered_feedback})


# ==================== CHATBOT ENDPOINTS ====================

class ChatbotQuery(BaseModel):
    """Request model for chatbot query."""
    query: str
    district: Optional[str] = None


@app.post("/api/chatbot/query")
async def chatbot_query(request: ChatbotQuery):
    """
    Process chatbot query and return response.
    
    Args:
        request: ChatbotQuery with query and optional district
        
    Returns:
        JSON response with chatbot answer, XAI log, and metadata
    """
    try:
        result = chatbot_service.process_query(
            query=request.query,
            district=request.district if request.district and request.district != "All Districts" else None
        )
        
        # If chatbot service returned an error, return it properly
        if not result.get("success", False):
            error_data = {
                "success": False,
                "response": result.get("response", "I encountered an error processing your query."),
                "error": result.get("error", "Unknown error occurred"),
                "xai_log": sanitize_for_json(result.get("xai_log", [])),
                "agent_results": sanitize_for_json(result.get("agent_results", [])),
                "is_district_specific": False,
                "detected_district": None,
                "query": request.query,
                "district": request.district
            }
            return JSONResponse(content=sanitize_for_json(error_data))
        
        # Detect if query is district-specific (single district, not multi-district)
        is_district_specific = False
        detected_district = None
        
        if request.district and request.district != "All Districts":
            # User explicitly selected a district
            is_district_specific = True
            detected_district = request.district
        else:
            # Try to detect district from query or response
            try:
                query_lower = request.query.lower()
                response_lower = result.get("response", "").lower()
                
                # Check if response mentions a single district (not multiple)
                from agents.tools.database_tool import get_districts
                districts = get_districts()
                mentioned_districts = [d for d in districts if d.lower() in query_lower or d.lower() in response_lower]
                
                # If exactly one district mentioned, it's district-specific
                if len(mentioned_districts) == 1:
                    is_district_specific = True
                    detected_district = mentioned_districts[0]
                elif len(mentioned_districts) > 1:
                    # Multiple districts - not district-specific for metrics display
                    is_district_specific = False
            except Exception:
                # If district detection fails, just continue without it
                pass
        
        # Sanitize response data to handle NaN/Infinity values
        response_data = {
            "success": True,
            "response": result.get("response", ""),
            "xai_log": sanitize_for_json(result.get("xai_log", [])),
            "agent_results": sanitize_for_json(result.get("agent_results", [])),
            "is_district_specific": is_district_specific,
            "detected_district": detected_district,
            "query": request.query,
            "district": request.district
        }
        
        return JSONResponse(content=sanitize_for_json(response_data))
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in chatbot_query endpoint: {error_trace}")
        
        error_data = {
            "success": False,
            "response": f"I encountered an error processing your query: {str(e)}",
            "error": str(e),
            "xai_log": [],
            "agent_results": [],
            "is_district_specific": False,
            "detected_district": None,
            "query": request.query,
            "district": request.district
        }
        return JSONResponse(
            status_code=500,
            content=sanitize_for_json(error_data)
        )


@app.get("/api/chatbot/districts")
async def get_chatbot_districts():
    """Get list of all available districts."""
    try:
        districts = get_districts()
        return JSONResponse(content={
            "success": True,
            "districts": districts
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching districts: {str(e)}")


@app.get("/api/chatbot/metrics/{district}")
async def get_chatbot_metrics(district: str):
    """
    Get comprehensive metrics for a specific district.
    
    Args:
        district: District name
        
    Returns:
        JSON response with all metrics (HVI, ISS, RCS, P-Score, SEL)
    """
    try:
        metrics = get_comprehensive_p_score(district=district)
        
        if district not in metrics:
            raise HTTPException(status_code=404, detail=f"District '{district}' not found or has no metrics")
        
        district_metrics = metrics[district]
        
        metrics_data = {
            "success": True,
            "district": district,
            "metrics": {
                "p_score": district_metrics.get("p_score", 0.0),
                "hvi_score": district_metrics.get("hvi_score", 0.0),
                "iss_score": district_metrics.get("iss_score", 0.0),
                "rcs_score": district_metrics.get("rcs_score", 0.0),
                "sel_index": district_metrics.get("sel_index", 1.0),
                "health_worker_capacity_gap": district_metrics.get("health_worker_capacity_gap", 0.0),
                "priority_level": district_metrics.get("priority_level", "LOW"),
                "recommendations": district_metrics.get("recommendations", []),
                "component_details": district_metrics.get("component_details", {})
            }
        }
        
        return JSONResponse(content=sanitize_for_json(metrics_data))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")


@app.get("/api/metrics/all")
async def get_all_metrics():
    """
    Get comprehensive metrics for all districts.
    
    Returns:
        JSON response with all districts and their metrics
    """
    try:
        all_metrics = get_comprehensive_p_score(district=None)
        
        if not all_metrics:
            return JSONResponse(content=sanitize_for_json({
                "success": True,
                "districts": []
            }))
        
        # Format response
        districts_data = []
        for district, metrics in all_metrics.items():
            districts_data.append({
                "district": district,
                "p_score": metrics.get("p_score", 0.0),
                "hvi_score": metrics.get("hvi_score", 0.0),
                "iss_score": metrics.get("iss_score", 0.0),
                "rcs_score": metrics.get("rcs_score", 0.0),
                "sel_index": metrics.get("sel_index", 1.0),
                "health_worker_capacity_gap": metrics.get("health_worker_capacity_gap", 0.0),
                "priority_level": metrics.get("priority_level", "LOW"),
                "recommendations": metrics.get("recommendations", []),
                "all_issues": metrics.get("all_issues", []),
                "component_details": metrics.get("component_details", {})
            })
        
        return JSONResponse(content=sanitize_for_json({
            "success": True,
            "districts": districts_data
        }))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching all metrics: {str(e)}")


@app.get("/chatbot", response_class=HTMLResponse)
async def chatbot_page(request: Request):
    """Serve the chatbot HTML page (legacy route, redirects to unified dashboard)."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_date": get_current_date()
        }
    )


# ===================== WORKFORCE ALLOCATION FUNCTIONS =====================

def load_workforce_data():
    """Load and process the service request data for workforce allocation"""
    global workforce_df, worker_data, worker_data_cache
    
    # Try to load CSV file
    csv_path = "service_request_details_csv.csv"
    
    try:
        if os.path.exists(csv_path):
            print(f"Loading workforce CSV file: {csv_path}")
            # Load with low_memory=False and optimize dtypes to speed up loading
            workforce_df = pd.read_csv(csv_path, low_memory=False)
            print(f"CSV loaded successfully. Shape: {workforce_df.shape}")
            
            # Clean column names
            workforce_df.columns = workforce_df.columns.str.strip()
            
            # Process the data to create worker capacity dataset
            worker_data = process_worker_data(workforce_df)
            print(f"Worker data processed. Total entries: {len(worker_data)}")
            
    except Exception as e:
        print(f"Error loading workforce data: {e}")
        import traceback
        traceback.print_exc()
        workforce_df = None
        worker_data = {}
    
    return workforce_df, worker_data


def process_worker_data(df):
    """Process service request data to extract worker capacity information"""
    worker_dict = {}
    
    # Map service categories to worker roles
    role_mapping = {
        'Public Safety': ['Police Officers'],
        'Health Services': ['Nurses & Medical Staff', 'Doctors'],
        'Health': ['Nurses & Medical Staff', 'Doctors'],
        'Medical': ['Nurses & Medical Staff', 'Doctors'],
        'Infrastructure': ['Road Workers', 'Electricians'],
        'Road': ['Road Workers'],
        'Road Maintenance': ['Road Workers'],
        'Electricity': ['Electricians'],
        'Utilities': ['Garbage Collectors', 'Water Supply'],
        'Waste': ['Garbage Collectors'],
        'Waste Management': ['Garbage Collectors'],
        'Emergency': ['Fire & Emergency Services'],
        'Fire': ['Fire & Emergency Services']
    }
    
    # Extract unique districts - filter out NaN and invalid values
    if 'District' in df.columns:
        districts = df['District'].dropna().astype(str).unique()
        # Filter out empty strings, 'nan' strings, and whitespace-only strings
        districts = [d.strip() for d in districts if d and str(d).strip() and str(d).lower() != 'nan']
    else:
        districts = ['Pune', 'Nagpur', 'Jalgaon', 'Mumbai', 'Thane']
    
    # Generate worker capacity data based on service requests
    for district in districts:
        district_df = df[df['District'] == district] if 'District' in df.columns else df
        
        # Get service categories for this district
        if 'Service_Category' in df.columns:
            service_categories = district_df['Service_Category'].dropna().unique()
            service_categories = [str(s).strip() for s in service_categories if pd.notna(s)]
        else:
            service_categories = ['Public Safety', 'Health Services', 'Infrastructure']
        
        for service_category in service_categories:
            # Find matching role mapping
            roles = None
            service_lower = service_category.lower()
            for key, value in role_mapping.items():
                if key.lower() in service_lower or service_lower in key.lower():
                    roles = value
                    break
            
            if roles is None:
                roles = [service_category]
            
            for role in roles:
                category_df = district_df[district_df['Service_Category'] == service_category] if 'Service_Category' in df.columns else district_df
                
                # Calculate workforce
                min_workforce = {
                    'Police Officers': 100,
                    'Nurses & Medical Staff': 150,
                    'Doctors': 50,
                    'Road Workers': 80,
                    'Electricians': 50,
                    'Garbage Collectors': 120,
                    'Fire & Emergency Services': 60
                }.get(role, 50)
                
                base_total = min_workforce
                
                # Calculate deployed workers
                if 'Status' in df.columns and 'Worker_Assigned' in df.columns:
                    status_lower = category_df['Status'].astype(str).str.lower().str.strip()
                    active_requests = category_df[
                        (category_df['Worker_Assigned'].notna()) &
                        (status_lower.isin(['in-progress', 'in progress', 'escalated', 'new', 'pending', 'open']) |
                         ~status_lower.isin(['resolved', 'completed', 'closed']))
                    ]
                    deployed_workers = set(active_requests['Worker_Assigned'].dropna().unique())
                    deployed = len(deployed_workers)
                else:
                    deployed = max(1, len(category_df) // 5)
                
                # Ensure minimum deployment (30% of total)
                min_deployed = int(base_total * 0.30)
                if deployed < min_deployed:
                    deployed = min(int(base_total * 0.4), max(min_deployed, len(category_df)))
                
                deployed = min(deployed, base_total)
                available = max(0, base_total - deployed)
                
                # Final safety: ensure we never have 100% available
                max_available = int(base_total * 0.85)
                if available > max_available:
                    deployed = base_total - max_available
                    available = max_available
                
                key = f"{district}_{role}"
                worker_dict[key] = {
                    'district': district,
                    'role': role,
                    'total': base_total,
                    'available': available,
                    'deployed': deployed
                }
    
    return worker_dict


def get_role_statistics():
    """Calculate statistics for all roles across all districts"""
    if worker_data is None:
        return {}
    
    role_stats = {}
    
    for key, data in worker_data.items():
        role = data['role']
        if role not in role_stats:
            role_stats[role] = {
                'total': 0,
                'available': 0,
                'deployed': 0,
                'districts': []
            }
        
        role_stats[role]['total'] += data['total']
        role_stats[role]['available'] += data['available']
        role_stats[role]['deployed'] += data['deployed']
        role_stats[role]['districts'].append(data['district'])
    
    return role_stats


def get_district_stats(district_name):
    """Get detailed statistics for a specific district"""
    global worker_data, worker_data_cache
    
    if worker_data is None:
        return []
    
    # Check cache first for faster response
    cache_key = f"district_stats_{district_name.lower().strip()}"
    if cache_key in worker_data_cache:
        return worker_data_cache[cache_key]
    
    # Filter workers for this district, handling potential float/NaN values
    district_workers = []
    district_name_lower = district_name.lower().strip()
    for key, data in worker_data.items():
        try:
            # Ensure district is a string and compare
            if isinstance(data['district'], str) and data['district'].lower().strip() == district_name_lower:
                district_workers.append(data)
        except (AttributeError, KeyError):
            continue
    
    # Group by role
    role_groups = {}
    for worker in district_workers:
        role = worker['role']
        if role not in role_groups:
            role_groups[role] = {
                'role': role,
                'total': 0,
                'available': 0,
                'deployed': 0
            }
        role_groups[role]['total'] += worker['total']
        role_groups[role]['available'] += worker['available']
        role_groups[role]['deployed'] += worker['deployed']
    
    result = list(role_groups.values())
    
    # Cache the result for faster subsequent requests
    worker_data_cache[cache_key] = result
    
    return result


# ===================== WORKFORCE ALLOCATION API ENDPOINTS =====================

@app.get("/api/workforce/capacity/summary")
async def get_workforce_capacity_summary():
    """Get overall capacity summary with top categories"""
    if worker_data is None:
        load_workforce_data()
    
    role_stats = get_role_statistics()
    
    # Calculate totals
    total_workforce = sum(stat['total'] for stat in role_stats.values())
    available_capacity = sum(stat['available'] for stat in role_stats.values())
    total_deployed = sum(stat['deployed'] for stat in role_stats.values())
    
    # Get top 5 categories by total workforce
    sorted_roles = sorted(role_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:5]
    
    top_categories = [
        {
            "role": role,
            "total": stat['total'],
            "available": stat['available'],
            "deployed": stat['deployed']
        }
        for role, stat in sorted_roles
    ]
    
    # If we have less than 5 roles, add some common ones
    common_roles = {
        "Police Officers": {"total": 1500, "available": 1050, "deployed": 450},
        "Nurses & Medical Staff": {"total": 3500, "available": 2450, "deployed": 1050},
        "Road Workers": {"total": 1200, "available": 840, "deployed": 360},
        "Electricians": {"total": 800, "available": 560, "deployed": 240},
        "Garbage Collectors": {"total": 2100, "available": 1470, "deployed": 630}
    }
    
    existing_roles = {cat['role'] for cat in top_categories}
    for role, stats in common_roles.items():
        if role not in existing_roles and len(top_categories) < 5:
            if role in role_stats:
                top_categories.append({
                    "role": role,
                    "total": role_stats[role]['total'],
                    "available": role_stats[role]['available'],
                    "deployed": role_stats[role]['deployed']
                })
            else:
                top_categories.append({
                    "role": role,
                    **stats
                })
    
    top_categories = top_categories[:5]
    
    return {
        "Total_Workforce": total_workforce or 12500,
        "Available_Capacity": available_capacity or 8900,
        "Total_Deployed": total_deployed,
        "Top_Categories": top_categories
    }


@app.get("/api/workforce/capacity/district/{district_name}")
async def get_workforce_district_capacity(district_name: str):
    """Get detailed capacity breakdown for a specific district"""
    if worker_data is None:
        load_workforce_data()
    
    district_stats = get_district_stats(district_name)
    
    # Generate detailed breakdown with police grades and nurse types
    detailed_stats = []
    
    # Police Officers with grades
    police_total = sum(stat['total'] for stat in district_stats if 'Police' in stat['role'])
    police_available = sum(stat['available'] for stat in district_stats if 'Police' in stat['role'])
    police_deployed = sum(stat['deployed'] for stat in district_stats if 'Police' in stat['role'])
    
    if police_total == 0:
        police_total = 300
        police_available = 210
        police_deployed = 90
    
    detailed_stats.extend([
        {"role": "Police Officers - Grade A", "total": int(police_total * 0.3), "available": int(police_available * 0.3), "deployed": int(police_deployed * 0.3)},
        {"role": "Police Officers - Grade B", "total": int(police_total * 0.4), "available": int(police_available * 0.4), "deployed": int(police_deployed * 0.4)},
        {"role": "Police Officers - Grade C", "total": int(police_total * 0.3), "available": int(police_available * 0.3), "deployed": int(police_deployed * 0.3)}
    ])
    
    # Nurses & Doctors with types
    health_stats = [stat for stat in district_stats if 'Nurse' in stat['role'] or 'Doctor' in stat['role'] or 'Medical' in stat['role']]
    health_total = sum(stat['total'] for stat in health_stats) if health_stats else 500
    health_available = sum(stat['available'] for stat in health_stats) if health_stats else 350
    health_deployed = sum(stat['deployed'] for stat in health_stats) if health_stats else 150
    
    detailed_stats.extend([
        {"role": "Nurses - ICU", "total": int(health_total * 0.2), "available": int(health_available * 0.2), "deployed": int(health_deployed * 0.2)},
        {"role": "Nurses - General", "total": int(health_total * 0.4), "available": int(health_available * 0.4), "deployed": int(health_deployed * 0.4)},
        {"role": "Nurses - Community Health", "total": int(health_total * 0.2), "available": int(health_available * 0.2), "deployed": int(health_deployed * 0.2)},
        {"role": "Doctors - General", "total": int(health_total * 0.15), "available": int(health_available * 0.15), "deployed": int(health_deployed * 0.15)},
        {"role": "Doctors - Specialists", "total": int(health_total * 0.05), "available": int(health_available * 0.05), "deployed": int(health_deployed * 0.05)}
    ])
    
    # Other roles
    other_roles = [
        {"role": "Road Workers", "total": 200, "available": 160, "deployed": 40},
        {"role": "Electricians / Power Grid Engineers", "total": 100, "available": 80, "deployed": 20},
        {"role": "Fire & Emergency Services", "total": 150, "available": 120, "deployed": 30},
        {"role": "Garbage Collectors", "total": 300, "available": 240, "deployed": 60}
    ]
    
    for role in other_roles:
        matching_stat = next((stat for stat in district_stats if role['role'].split()[0].lower() in stat['role'].lower()), None)
        if matching_stat:
            role['total'] = matching_stat['total']
            role['available'] = matching_stat['available']
            role['deployed'] = matching_stat['deployed']
        detailed_stats.append(role)
    
    return detailed_stats


@app.get("/api/workforce/capacity/districts")
async def get_workforce_all_districts():
    """Get list of all districts"""
    if workforce_df is None:
        load_workforce_data()
    
    if workforce_df is not None and 'District' in workforce_df.columns:
        # Filter out NaN values and convert to strings, then sort - limit to 10 for performance
        districts = workforce_df['District'].dropna().astype(str).unique().tolist()
        districts = [d for d in districts if d and str(d).strip() and str(d).lower() != 'nan']
        districts = sorted(districts)[:10]
    else:
        # Fallback to existing districts from database
        districts = get_districts()[:10]
    
    return {"districts": districts}


@app.get("/api/workforce/capacity/metrics")
async def get_workforce_capacity_metrics():
    """Get additional metrics for the dashboard cards"""
    if workforce_df is None:
        load_workforce_data()
    
    # Calculate metrics
    if workforce_df is not None:
        # Total Deployed Personnel
        deployed_workers = set()
        if 'Status' in workforce_df.columns and 'Worker_Assigned' in workforce_df.columns:
            status_values = workforce_df['Status'].astype(str).str.lower().str.strip()
            active_df = workforce_df[
                (workforce_df['Worker_Assigned'].notna()) &
                (status_values.isin(['in-progress', 'in progress', 'escalated', 'new', 'pending', 'open']) |
                 ~status_values.isin(['resolved', 'completed', 'closed']))
            ]
            deployed_workers = set(active_df['Worker_Assigned'].dropna().unique())
            deployed_count = len(deployed_workers)
        else:
            deployed_count = 2150
        
        # Average Deployment Time
        if 'Created_Timestamp' in workforce_df.columns and 'Resolution_Time_Hours' in workforce_df.columns:
            avg_deployment_time = workforce_df['Resolution_Time_Hours'].mean()
            if pd.isna(avg_deployment_time):
                avg_deployment_time = 1.25
        else:
            avg_deployment_time = 1.25
    else:
        deployed_count = 2150
        avg_deployment_time = 1.25
    
    # Calculate Critical Shortfall Alerts
    role_stats = get_role_statistics()
    shortfall_count = 0
    
    # Get districts, filtering out NaN values
    if workforce_df is not None and 'District' in workforce_df.columns:
        districts = workforce_df['District'].dropna().astype(str).unique().tolist()
        districts = [d for d in districts if d and str(d).strip() and str(d).lower() != 'nan'][:5]
    else:
        districts = get_districts()[:5]
    
    for district in districts:
        district_stats = get_district_stats(district)
        for role_data in district_stats:
            availability_pct = (role_data['available'] / role_data['total'] * 100) if role_data['total'] > 0 else 0
            if role_data['role'] in ['Police Officers', 'Nurses & Medical Staff', 'Doctors']:
                if availability_pct < 85:
                    shortfall_count += 1
                    break
    
    # Highest Availability Role
    highest_availability_role = "Garbage Collectors"
    highest_availability_pct = 80.0
    
    for role, stat in role_stats.items():
        if stat['total'] > 0:
            pct = (stat['available'] / stat['total']) * 100
            if pct > highest_availability_pct:
                highest_availability_pct = pct
                highest_availability_role = role
    
    return {
        "total_deployed": deployed_count,
        "critical_shortfall_alerts": shortfall_count or 3,
        "highest_availability_role": highest_availability_role,
        "highest_availability_pct": round(highest_availability_pct, 1),
        "average_deployment_time_hours": round(avg_deployment_time, 2)
    }


@app.get("/api/workforce/capacity/district-summary")
async def get_workforce_district_summary():
    """Get summary table data for all districts"""
    if workforce_df is None:
        load_workforce_data()
    
    # Get districts, filtering out NaN values - limit to 5 for faster loading
    if workforce_df is not None and 'District' in workforce_df.columns:
        districts = workforce_df['District'].dropna().astype(str).unique().tolist()
        districts = [d for d in districts if d and str(d).strip() and str(d).lower() != 'nan'][:5]
    else:
        districts = get_districts()[:5]
    
    summary_data = []
    
    for district in districts:
        # Active Alerts - ensure district is a string for comparison
        district_df = None
        if workforce_df is not None and 'District' in workforce_df.columns:
            # Filter with type checking to avoid comparison issues
            district_df = workforce_df[workforce_df['District'].astype(str) == str(district)]
        
        if district_df is not None and len(district_df) > 0 and 'Status' in district_df.columns:
            status_values = district_df['Status'].astype(str).str.lower()
            active_alerts = len(district_df[status_values.isin(['in progress', 'in-progress', 'open', 'pending', 'new'])])
        else:
            active_alerts = 15
        
        # Total Available Workforce
        district_stats = get_district_stats(district)
        total_available = sum(stat['available'] for stat in district_stats)
        
        # Health Staff Used Percentage
        health_stats = [stat for stat in district_stats if 'Nurse' in stat['role'] or 'Doctor' in stat['role'] or 'Medical' in stat['role']]
        health_total = sum(stat['total'] for stat in health_stats) if health_stats else 0
        health_deployed = sum(stat['deployed'] for stat in health_stats) if health_stats else 0
        
        health_deployed = min(health_deployed, health_total) if health_total > 0 else 0
        health_used_pct = (health_deployed / health_total * 100) if health_total > 0 else 0
        health_used_pct = min(health_used_pct, 100.0)
        
        summary_data.append({
            "district": district,
            "active_alerts": active_alerts or 10,
            "total_available_workforce": total_available or 1500,
            "health_staff_used_pct": round(health_used_pct, 1),
            "police_safety_shortfall": False
        })
    
    # Mark only 1-2 districts with lowest police availability as having shortfall
    districts_with_police = []
    for i, district_summary in enumerate(summary_data):
        district = district_summary["district"]
        district_stats = get_district_stats(district)
        police_stats = [stat for stat in district_stats if 'Police' in stat['role']]
        
        if police_stats:
            police_availability_pcts = [
                (stat['available'] / stat['total'] * 100) if stat['total'] > 0 else 100
                for stat in police_stats
            ]
            avg_availability = sum(police_availability_pcts) / len(police_availability_pcts) if police_availability_pcts else 100
            districts_with_police.append({
                'index': i,
                'district': district,
                'availability': avg_availability
            })
    
    districts_with_police.sort(key=lambda x: x['availability'])
    
    num_shortfalls = min(2, len(districts_with_police))
    for i in range(num_shortfalls):
        if districts_with_police[i]['availability'] < 90:
            summary_data[districts_with_police[i]['index']]["police_safety_shortfall"] = True
    
    return summary_data


# ===================== TICKET MONITORING ENDPOINTS =====================

@app.get("/api/tickets")
async def get_tickets(
    service_category: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    district: Optional[str] = None,
    limit: int = 100
):
    """Get service request tickets with filtering, sorted by latest timestamp"""
    from database.connection import get_db_connection as get_db_conn
    from sqlalchemy import text
    
    conn = None
    try:
        conn = get_db_conn()
        
        # Build query with filters
        query = """
            SELECT 
                "Request_ID",
                "Created_Timestamp",
                "Service_Category",
                "Sub_Category",
                "Priority",
                "Status",
                "District",
                "Area",
                "Email_ID",
                "Channel",
                "Citizen_Age_Group",
                "Resolution_Time_Hours",
                "Escalated",
                "Satisfaction_Rating",
                "Assigned_Department",
                "Worker_Assigned"
            FROM service_request_details
            WHERE 1=1
        """
        
        params = {}
        
        if service_category and service_category != "All":
            query += ' AND "Service_Category" = :service_category'
            params['service_category'] = service_category
        
        if status and status != "All":
            query += ' AND "Status" = :status'
            params['status'] = status
        
        if priority and priority != "All":
            query += ' AND "Priority" = :priority'
            params['priority'] = priority
        
        if district and district != "All":
            query += ' AND "District" = :district'
            params['district'] = district
        
        query += ' ORDER BY "Created_Timestamp" DESC LIMIT :limit'
        params['limit'] = limit
        
        result = conn.execute(text(query), params)
        
        tickets = []
        for row in result:
            tickets.append({
                "Request_ID": row[0],
                "Created_Timestamp": row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else None,
                "Service_Category": row[2],
                "Sub_Category": row[3],
                "Priority": row[4],
                "Status": row[5],
                "District": row[6],
                "Area": row[7],
                "Email_ID": row[8],
                "Channel": row[9],
                "Citizen_Age_Group": row[10],
                "Resolution_Time_Hours": float(row[11]) if row[11] is not None else None,
                "Escalated": row[12],
                "Satisfaction_Rating": float(row[13]) if row[13] is not None else None,
                "Assigned_Department": row[14],
                "Worker_Assigned": row[15]
            })
        
        return JSONResponse(content={
            "success": True,
            "tickets": tickets,
            "count": len(tickets)
        })
        
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "tickets": [],
                "count": 0
            }
        )
    finally:
        if conn:
            conn.close()


@app.get("/api/tickets/filters")
async def get_ticket_filters():
    """Get available filter options for tickets"""
    from database.connection import get_db_connection as get_db_conn
    from sqlalchemy import text
    
    conn = None
    try:
        conn = get_db_conn()
        
        # Get distinct values for filters
        categories_result = conn.execute(text(
            'SELECT DISTINCT "Service_Category" FROM service_request_details WHERE "Service_Category" IS NOT NULL ORDER BY "Service_Category"'
        ))
        categories = [row[0] for row in categories_result]
        
        statuses_result = conn.execute(text(
            'SELECT DISTINCT "Status" FROM service_request_details WHERE "Status" IS NOT NULL ORDER BY "Status"'
        ))
        statuses = [row[0] for row in statuses_result]
        
        priorities_result = conn.execute(text(
            'SELECT DISTINCT "Priority" FROM service_request_details WHERE "Priority" IS NOT NULL ORDER BY "Priority"'
        ))
        priorities = [row[0] for row in priorities_result]
        
        districts_result = conn.execute(text(
            'SELECT DISTINCT "District" FROM service_request_details WHERE "District" IS NOT NULL ORDER BY "District"'
        ))
        districts = [row[0] for row in districts_result]
        
        return JSONResponse(content={
            "success": True,
            "filters": {
                "service_categories": categories,
                "statuses": statuses,
                "priorities": priorities,
                "districts": districts
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching ticket filters: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "filters": {
                    "service_categories": [],
                    "statuses": [],
                    "priorities": [],
                    "districts": []
                }
            }
        )
    finally:
        if conn:
            conn.close()


@app.get("/api/tickets/stats")
async def get_ticket_stats():
    """Get summary statistics for tickets"""
    from database.connection import get_db_connection as get_db_conn
    from sqlalchemy import text
    
    conn = None
    try:
        conn = get_db_conn()
        
        # Total tickets
        total_result = conn.execute(text('SELECT COUNT(*) FROM service_request_details'))
        total_tickets = total_result.fetchone()[0]
        
        # Open tickets
        open_result = conn.execute(text(
            'SELECT COUNT(*) FROM service_request_details WHERE "Status" IN (\'Open\', \'In Progress\', \'Pending\')'
        ))
        open_tickets = open_result.fetchone()[0]
        
        # High priority tickets
        high_priority_result = conn.execute(text(
            'SELECT COUNT(*) FROM service_request_details WHERE "Priority" = \'High\' AND "Status" IN (\'Open\', \'In Progress\', \'Pending\')'
        ))
        high_priority_tickets = high_priority_result.fetchone()[0]
        
        # Average resolution time
        avg_resolution_result = conn.execute(text(
            'SELECT AVG("Resolution_Time_Hours") FROM service_request_details WHERE "Resolution_Time_Hours" IS NOT NULL'
        ))
        avg_resolution_time = avg_resolution_result.fetchone()[0]
        avg_resolution_time = round(float(avg_resolution_time), 2) if avg_resolution_time else 0
        
        # Escalated tickets - Fix: Escalated is stored as TEXT, not boolean
        escalated_result = conn.execute(text(
            'SELECT COUNT(*) FROM service_request_details WHERE UPPER(CAST("Escalated" AS TEXT)) IN (\'TRUE\', \'YES\', \'1\')'
        ))
        escalated_tickets = escalated_result.fetchone()[0]
        
        return JSONResponse(content={
            "success": True,
            "stats": {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "high_priority_tickets": high_priority_tickets,
                "average_resolution_hours": avg_resolution_time,
                "escalated_tickets": escalated_tickets
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching ticket stats: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "stats": {
                    "total_tickets": 0,
                    "open_tickets": 0,
                    "high_priority_tickets": 0,
                    "average_resolution_hours": 0,
                    "escalated_tickets": 0
                }
            }
        )
    finally:
        if conn:
            conn.close()


# ===================== MULTILINGUAL CHATBOT FUNCTIONS =====================

def text_to_speech(text, language='en', voice_code=None):
    """Convert text to speech using Azure Speech Services"""
    if not MULTILINGUAL_AVAILABLE or not SPEECH_SERVICE_API_KEY:
        return None
        
    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=SPEECH_SERVICE_API_KEY, 
            region=SPEECH_SERVICE_REGION
        )
        
        # Use provided voice_code or default to English
        if voice_code is None:
            voice_code = 'en-US-JennyNeural'
        
        speech_config.speech_synthesis_voice_name = voice_code
        
        filename = f"response_{uuid.uuid4()}.wav"
        file_path = os.path.join('static', 'audio', filename)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, 
            audio_config=audio_config
        )
        
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return f"/static/audio/{filename}"
        return None
            
    except Exception as e:
        logger.error(f"Text-to-speech error: {e}")
        return None


def create_new_ticket_multilingual(data):
    """Create a new service request ticket from multilingual chatbot"""
    from database.connection import get_db_connection as get_db_conn
    from sqlalchemy import text
    
    try:
        conn = get_db_conn()
        
        # Get the maximum Request_ID number to generate next sequential ID
        result = conn.execute(text("""
            SELECT MAX(CAST(SUBSTRING("Request_ID" FROM 'REQ([0-9]+)') AS INTEGER))
            FROM service_request_details
            WHERE "Request_ID" ~ '^REQ[0-9]+$'
        """))
        max_id_row = result.fetchone()
        
        if max_id_row and max_id_row[0] is not None:
            next_number = max_id_row[0] + 1
        else:
            next_number = 1000
        
        request_id = f"REQ{next_number}"
        
        # Insert the new ticket
        conn.execute(text("""
            INSERT INTO service_request_details 
            ("Request_ID", "Created_Timestamp", "Service_Category", "Sub_Category", "Priority", "Status", 
             "District", "Area", "Email_ID", "Channel", "Citizen_Age_Group")
            VALUES 
            (:request_id, :created_timestamp, :service_category, :sub_category, :priority, :status,
             :district, :area, :email_id, :channel, :citizen_age_group)
        """), {
            "request_id": request_id,
            "created_timestamp": datetime.now(),
            "service_category": data.get('service_category', ''),
            "sub_category": data.get('sub_category', ''),
            "priority": data.get('priority', 'Normal'),
            "status": 'Open',
            "district": data.get('district', ''),
            "area": data.get('area', ''),
            "email_id": data.get('email', ''),
            "channel": "Multilingual Chatbot",
            "citizen_age_group": data.get('citizen_age_group', '')
        })
        conn.commit()
        conn.close()
        return request_id
    except Exception as e:
        logger.error(f"Database error in create_new_ticket_multilingual: {e}")
        return None


def send_confirmation_email_multilingual(to_email, ticket_id, ticket_data):
    """Send confirmation email for multilingual chatbot tickets"""
    if not SMTP_USERNAME or not FROM_EMAIL:
        return False
        
    try:
        language = ticket_data.get('language', 'en')
        
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"Ticket Confirmation: {ticket_id}"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #2c3e50;">Wildcard Platform - Ticket Confirmation</h2>
                <p>Thank you for reporting an issue. Your ticket has been created successfully.</p>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Ticket Details</h3>
                    <p><strong>Request ID:</strong> {ticket_id}</p>
                    <p><strong>Service Category:</strong> {ticket_data.get('service_category', 'N/A')}</p>
                    <p><strong>Sub-Category:</strong> {ticket_data.get('sub_category', 'N/A')}</p>
                    <p><strong>District:</strong> {ticket_data.get('district', 'N/A')}</p>
                    <p><strong>Area:</strong> {ticket_data.get('area', 'N/A')}</p>
                    <p><strong>Priority:</strong> {ticket_data.get('priority', 'Normal')}</p>
                </div>
                <p>We will address your request within 2-3 business days.</p>
                <p style="margin-top: 30px; font-size: 12px; color: #777;">
                    © 2025 Wildcard Platform | Team EvoMind
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(email_body, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Confirmation email sent to {to_email} for ticket {ticket_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        return False


# ===================== MULTILINGUAL CHATBOT ENDPOINTS =====================

@app.post('/api/new_chat')
async def new_chat(request: Request):
    """Handle multilingual chatbot conversations"""
    if not MULTILINGUAL_AVAILABLE or not openai_client:
        return JSONResponse(
            {"error": "Multilingual chatbot not available"}, 
            status_code=503
        )
    
    data = await request.json()
    user_message = data.get('message', '')
    conversation_history = data.get('history', [])
    
    # Enhanced language detection using LLM
    language_detection_response = openai_client.chat.completions.create(
        model=LLM_DEPLOYMENT_NAME or "gpt-4",
        messages=[
            {"role": "system", "content": """Detect the language and return JSON with language code and Azure Neural Voice code.
            Return ONLY JSON in this format:
            {
                "language_code": "xx",
                "voice_code": "xx-XX-NameNeural"
            }
            
            Examples:
            - English: {"language_code": "en", "voice_code": "en-US-JennyNeural"}
            - Arabic: {"language_code": "ar", "voice_code": "ar-AE-HamdanNeural"}
            - Hindi: {"language_code": "hi", "voice_code": "hi-IN-SwaraNeural"}
            - Spanish: {"language_code": "es", "voice_code": "es-ES-ElviraNeural"}
            - French: {"language_code": "fr", "voice_code": "fr-FR-DeniseNeural"}
            
            Return ONLY the JSON, no additional text."""},
            {"role": "user", "content": user_message}
        ],
        temperature=0.0
    )
    
    try:
        language_response = json.loads(language_detection_response.choices[0].message.content.strip())
        detected_language = language_response.get('language_code', 'en')
        voice_code = language_response.get('voice_code', 'en-US-JennyNeural')
    except json.JSONDecodeError:
        detected_language = 'en'
        voice_code = 'en-US-JennyNeural'
    
    logger.info(f"Detected language: {detected_language}, Voice: {voice_code}")
    
    # Process with LLM
    conversation_context = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" 
                                       for msg in conversation_history])
    
    system_prompt = f"""
You are a government service chatbot helping citizens report issues.
Important: Do not include emojis anywhere.
Understand the language: {detected_language}. Reply in {detected_language}.

Follow this conversation flow:

1. Greet and ask if the user wants to report an issue.
2. Identify Service Category from: Education, Electricity, Health Services, Infrastructure, Public Safety, Revenue Services, Road Maintenance, Transport, Waste Management, Water Supply
3. Show relevant Sub-Categories based on the category
4. Get District (broader area)
5. Get Area (specific locality)
6. Get detailed description
7. Determine Priority (High, Normal, Low)
8. Ask for Email ID
9. Ask for Citizen Age Group (18-25, 26-35, 36-45, 46-55, 56-65, 65+)
10. Provide summary and ask for confirmation
11. After confirmation, append JSON summary in English:

```json
{{
    "language": "{detected_language}",
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

The JSON must be in English only. Tell the user the issue will be resolved in 2-3 days.
"""
    
    try:
        response = openai_client.chat.completions.create(
            model=LLM_DEPLOYMENT_NAME or "gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Previous conversation:\n{conversation_context}\n\nUser message: {user_message}"}
            ],
            temperature=0.5
        )
        
        assistant_response = response.choices[0].message.content
        
        json_data = None
        final_response = assistant_response
        
        # Extract JSON
        if '```json' in assistant_response:
            parts = assistant_response.split('```json')
            visible_response = parts[0].strip()
            json_str = parts[1].split('```')[0].strip()
            
            try:
                json_data = json.loads(json_str)
                final_response = visible_response
            except json.JSONDecodeError:
                pass
        
        # Create ticket if JSON is valid
        ticket_id = None
        if json_data and json_data.get('is_complete', False):
            ticket_id = create_new_ticket_multilingual(json_data)
            if ticket_id:
                final_response += f"\n\nYour request has been submitted. Your ticket ID is: {ticket_id}"
                
                if json_data.get('email'):
                    send_confirmation_email_multilingual(
                        json_data.get('email'),
                        ticket_id,
                        json_data
                    )
        
        # Generate audio if requested
        audio_path = None
        if data.get('generate_audio', False):
            audio_path = text_to_speech(final_response.replace("*","").replace("\n",""), detected_language, voice_code)
        
        conversation_history.append({"role": "assistant", "content": assistant_response})
        
        is_arabic = detected_language == 'ar'
        
        return JSONResponse({
            "response": final_response,
            "audio_path": audio_path,
            "conversation_history": conversation_history,
            "is_arabic": is_arabic
        })
    
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post('/api/speech-to-text')
async def speech_to_text(request: Request):
    """Convert speech to text using Azure Speech Services"""
    if not MULTILINGUAL_AVAILABLE or not SPEECH_SERVICE_API_KEY:
        return JSONResponse(
            {"error": "Speech-to-text not available"}, 
            status_code=503
        )
    
    try:
        audio_data = await request.body()
        if not audio_data:
            return JSONResponse({"error": "No audio data provided"}, status_code=400)
        
        speech_config = speechsdk.SpeechConfig(
            subscription=SPEECH_SERVICE_API_KEY, 
            region=SPEECH_SERVICE_REGION
        )
        
        auto_detect_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
            languages=["en-US", "ar-AE", "hi-IN", "es-ES", "fr-FR"]
        )
        
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
            auto_detect_source_language_config=auto_detect_config
        )
        
        push_stream.write(audio_data)
        push_stream.close()
        
        result = speech_recognizer.recognize_once_async().get()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return JSONResponse({"text": result.text})
        return JSONResponse({"error": "Speech not recognized"}, status_code=400)
        
    except Exception as e:
        logger.error(f"Speech recognition error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ===================== FORECASTING ENDPOINTS =====================

@app.get("/api/series")
def api_series():
    """Get list of available forecast series"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    return JSONResponse(content={"series": list_series(DATA_DF)})


@app.get("/api/data")
def api_data(unique_id: str = None, n: int = 200):
    """Get historical data for a series"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    if unique_id:
        s = prepare_series_df(DATA_DF, unique_id).tail(n).copy()
        if "date" in s.columns:
            s["date"] = s["date"].astype(str)
        return JSONResponse(content={"data": s.to_dict(orient="records")})
    
    df_head = DATA_DF.head(n).copy()
    if "date" in df_head.columns:
        df_head["date"] = df_head["date"].astype(str)
    return JSONResponse(content={"data": df_head.to_dict(orient="records")})


@app.post("/api/forecast")
async def api_forecast(payload: dict):
    """Generate forecast for a series"""
    try:
        if not FORECAST_AVAILABLE or DATA_DF.empty:
            raise HTTPException(status_code=503, detail="Forecasting not available.")
        
        unique_id = payload.get("unique_id")
        h = int(payload.get("h", 12))
        finetune = int(payload.get("finetune_steps", 0))
        
        if not unique_id:
            raise HTTPException(status_code=400, detail="unique_id required")
        
        # Generate forecast without exogenous variables (faster and more reliable)
        try:
            preds = timegpt_forecast(DATA_DF, unique_id, h=h, finetune_steps=finetune, auto_select_vars=False)
            logging.info(f"Forecast generated successfully for {unique_id}, shape: {preds.shape}")
        except Exception as e:
            logging.error(f"Forecasting failed for {unique_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Forecasting failed: {e}")
        
        # Prepare history data
        try:
            history_df = prepare_series_df(DATA_DF, unique_id).tail(52)[["date","new_cases"]].copy()
            history_df["date"] = history_df["date"].astype(str)
            history = history_df.to_dict(orient="records")
        except Exception as e:
            logging.error(f"Failed to prepare history: {e}")
            history = []
        
        # Prepare forecast data
        try:
            preds_copy = preds.copy()
            if "date" in preds_copy.columns:
                preds_copy["date"] = preds_copy["date"].astype(str)
            forecast_data = preds_copy.to_dict(orient="records")
        except Exception as e:
            logging.error(f"Failed to prepare forecast data: {e}")
            forecast_data = []
        
        # Generate insights (optional - don't fail if this fails)
        insights = {"trend_analysis": [], "forecast_insights": [], "risk_assessment": [], "recommendations": []}
        try:
            series_df = prepare_series_df(DATA_DF, unique_id)
            # Skip insights generation for now to avoid errors - can be enabled later
            # def forecast_fn_for_insights(train_df, h_local):
            #     df_train = train_df.copy()
            #     if "unique_id" not in df_train.columns:
            #         df_train["unique_id"] = df_train["ward_id"] + "__" + df_train["disease_type"]
            #     return timegpt_forecast(df_train, df_train["unique_id"].iloc[0], h=h_local, 
            #                           finetune_steps=finetune, auto_select_vars=False)
            # kpis_for_insights = compute_holdout_kpis(series_df, forecast_fn_for_insights, h=min(h, 8))
            # insights = generate_ai_insights(series_df, preds, kpis_for_insights)
        except Exception as e:
            logging.warning(f"Failed to generate insights: {e}")
        
        return JSONResponse(content={
            "history": history, 
            "forecast": forecast_data,
            "insights": insights    
        })
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in forecast endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/kpis")
def api_kpis(unique_id: str, h: int = 8, finetune_steps: int = 10):
    """Compute forecast KPIs"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    
    s = prepare_series_df(DATA_DF, unique_id)
    
    def forecast_fn(train_df, h_local):
        df_train = train_df.copy()
        if "unique_id" not in df_train.columns:
            df_train["unique_id"] = df_train["ward_id"] + "__" + df_train["disease_type"]
        return timegpt_forecast(df_train, df_train["unique_id"].iloc[0], h=h_local, finetune_steps=finetune_steps, auto_select_vars=False)
    
    kpis = compute_holdout_kpis(s, forecast_fn, h=h)
    last_week = int(s["new_cases"].iloc[-1])
    avg_12 = float(s["new_cases"].tail(12).mean())
    
    return JSONResponse(content={"kpis": kpis, "last_week_cases": last_week, "avg_last_12_weeks": avg_12})


@app.get("/api/overall-stats")
def api_overall_stats():
    """Get overall statistics for the dataset"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    stats = get_overall_stats(DATA_DF)
    return JSONResponse(content=stats)


@app.get("/api/disease-distribution")
def api_disease_distribution():
    """Get disease type distribution"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    distribution = get_disease_distribution(DATA_DF)
    return JSONResponse(content=distribution)


@app.get("/api/ward-analysis")
def api_ward_analysis(top_n: int = 10):
    """Get top wards by total cases"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    analysis = get_ward_analysis(DATA_DF, top_n=top_n)
    return JSONResponse(content=analysis)


@app.get("/api/time-trends")
def api_time_trends(period: str = "weekly"):
    """Get time-based trends"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    trends = get_time_trends(DATA_DF, period=period)
    return JSONResponse(content=trends)


@app.get("/api/correlations")
def api_correlations():
    """Get correlations between new_cases and external regressors"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    correlations = get_correlation_analysis(DATA_DF)
    return JSONResponse(content=correlations)


@app.post("/api/insights")
async def api_insights(payload: dict):
    """Generate AI insights for a forecast"""
    if not FORECAST_AVAILABLE or DATA_DF.empty:
        raise HTTPException(status_code=503, detail="Forecasting not available.")
    
    unique_id = payload.get("unique_id")
    if not unique_id:
        raise HTTPException(status_code=400, detail="unique_id required")
    
    h = int(payload.get("h", 12))
    finetune = int(payload.get("finetune_steps", 0))
    
    try:
        preds = timegpt_forecast(DATA_DF, unique_id, h=h, finetune_steps=finetune)
        series_df = prepare_series_df(DATA_DF, unique_id)
        
        def forecast_fn(train_df, h_local):
            df_train = train_df.copy()
            if "unique_id" not in df_train.columns:
                df_train["unique_id"] = df_train["ward_id"] + "__" + df_train["disease_type"]
            return timegpt_forecast(df_train, df_train["unique_id"].iloc[0], h=h_local, 
                                  finetune_steps=finetune, auto_select_vars=False)
        kpis = compute_holdout_kpis(series_df, forecast_fn, h=min(h, 8))
        
        insights = generate_ai_insights(series_df, preds, kpis)
        
        return JSONResponse(content=insights)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {e}")


# ===================== PAGE ROUTES =====================

@app.get('/forecast', response_class=HTMLResponse)
def forecast_page(request: Request):
    """Serve the disease forecasting page"""
    return templates.TemplateResponse("disease_forecast.html", {"request": request})


@app.get('/multilingual_bot', response_class=HTMLResponse)
async def multilingual_bot(request: Request):
    """Serve the multilingual chatbot page"""
    return templates.TemplateResponse('index_new.html', {"request": request})


@app.get('/home2', response_class=HTMLResponse, name='home2')
async def home2(request: Request):
    """Serve the home2 page"""
    return templates.TemplateResponse('home2.html', {"request": request})


@app.get('/architecture', response_class=HTMLResponse)
async def architecture_page(request: Request):
    """Serve the architecture diagrams page"""
    return templates.TemplateResponse('architecture.html', {"request": request})


# ===================== STARTUP EVENT =====================

@app.on_event("startup")
async def startup_event():
    """Load data on application startup"""
    global DATA_DF
    print("="*80)
    print("🚀 Wildcard Platform - Initializing...")
    print("="*80)
    
    # Load workforce allocation data
    print("📊 Loading workforce allocation data...")
    load_workforce_data()
    print("✅ Workforce data loaded!")
    
    # Load forecasting data if available
    if FORECAST_AVAILABLE:
        try:
            print("📈 Loading disease forecasting data...")
            DATA_DF = load_data()
            print(f"✅ Forecasting data loaded! ({len(DATA_DF)} records)")
        except Exception as e:
            print(f"⚠️  Forecasting data not available: {e}")
            DATA_DF = pd.DataFrame()
    
    print("="*80)
    print("✅ Platform initialization complete!")
    print("="*80)


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 Wildcard Platform - Server Starting...")
    print("="*60)
    print(f"\n✅ Server is running at: http://localhost:8001")
    print(f"\n🌐 Main Pages:")
    print(f"   🏠 Landing Page: http://localhost:8001")
    print(f"   🔐 Login Page: http://localhost:8001/login")
    print(f"   📊 Admin Dashboard: http://localhost:8001/dashboard")
    print(f"   📈 Disease Forecasting: http://localhost:8001/forecast")
    print(f"   🗣️ Multilingual Chatbot: http://localhost:8001/multilingual_bot")
    print(f"\n✨ Features:")
    print(f"   • Predictive Alerts & Feedback")
    print(f"   • AI Admin Assistant Chatbot")
    print(f"   • Disease Outbreak Forecasting (TimeGPT)")
    print(f"   • Multilingual Citizen Service Bot")
    print(f"   • Metrics Dashboard (P-Score, HVI, ISS, RCS, SEL)")
    print(f"   • Policy Sandbox")
    print(f"   • Workforce Allocation")
    print("\n" + "="*60)
    print("Team EvoMind | Google Hackathon 2025")
    print("="*60)
    print("\nPress CTRL+C to stop the server\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, ssl_keyfile=None, ssl_certfile=None)

