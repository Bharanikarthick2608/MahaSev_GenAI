"""
FastAPI backend for Alerts & Feedback Dashboard.
Provides API endpoints for alerts and citizen feedback data.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from typing import List, Optional

app = FastAPI(title="Alerts & Feedback Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")


def get_current_date():
    """Get formatted current date."""
    return datetime.now().strftime("%A, %B %d, %Y")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main dashboard HTML page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_date": get_current_date()
        }
    )


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

# Sample customer sentiment data for word cloud and charts
CUSTOMER_SENTIMENT_DATA = {
    "sentiment_distribution": {
        "positive": 45,
        "neutral": 30,
        "negative": 25
    },
    "word_frequency": [
        {"word": "service", "frequency": 125},
        {"word": "response", "frequency": 98},
        {"word": "quality", "frequency": 87},
        {"word": "delay", "frequency": 76},
        {"word": "excellent", "frequency": 65},
        {"word": "improvement", "frequency": 54},
        {"word": "satisfaction", "frequency": 52},
        {"word": "waiting", "frequency": 48},
        {"word": "staff", "frequency": 45},
        {"word": "facility", "frequency": 43},
        {"word": "clean", "frequency": 41},
        {"word": "maintenance", "frequency": 39},
        {"word": "helpful", "frequency": 37},
        {"word": "time", "frequency": 35},
        {"word": "process", "frequency": 33},
        {"word": "efficient", "frequency": 31},
        {"word": "system", "frequency": 29},
        {"word": "issue", "frequency": 28},
        {"word": "quick", "frequency": 27},
        {"word": "digital", "frequency": 25},
        {"word": "online", "frequency": 24},
        {"word": "support", "frequency": 23},
        {"word": "experience", "frequency": 22},
        {"word": "problem", "frequency": 21},
        {"word": "good", "frequency": 20},
        {"word": "infrastructure", "frequency": 19},
        {"word": "road", "frequency": 18},
        {"word": "water", "frequency": 17},
        {"word": "health", "frequency": 16},
        {"word": "clinic", "frequency": 15}
    ],
    "sentiment_trends": [
        {"date": "2024-01-01", "positive": 38, "neutral": 35, "negative": 27},
        {"date": "2024-01-08", "positive": 40, "neutral": 33, "negative": 27},
        {"date": "2024-01-15", "positive": 42, "neutral": 32, "negative": 26},
        {"date": "2024-01-22", "positive": 43, "neutral": 31, "negative": 26},
        {"date": "2024-01-29", "positive": 45, "neutral": 30, "negative": 25}
    ],
    "topic_sentiment": [
        {"topic": "Healthcare", "positive": 55, "neutral": 25, "negative": 20},
        {"topic": "Infrastructure", "positive": 35, "neutral": 30, "negative": 35},
        {"topic": "Digital Services", "positive": 60, "neutral": 25, "negative": 15},
        {"topic": "Public Safety", "positive": 40, "neutral": 30, "negative": 30},
        {"topic": "Utilities", "positive": 30, "neutral": 35, "negative": 35}
    ]
}

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
        "feedback_count": len(ALL_FEEDBACK_DATA),  # Total feedback items for tab badge (5)
        "sentiment_count": len(CUSTOMER_SENTIMENT_DATA.get("word_frequency", []))  # Total words for sentiment tab
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


@app.get("/api/sentiment")
async def get_sentiment():
    """Get customer sentiment data for charts and word cloud."""
    return JSONResponse(content=CUSTOMER_SENTIMENT_DATA)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

