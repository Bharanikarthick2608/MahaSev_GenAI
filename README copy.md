# Alerts & Feedback Dashboard

A FastAPI-based dashboard for displaying real-time alerts and citizen feedback, matching the exact structure and components from the design.

## Features

- **Dashboard Metrics**: Displays Active Alerts, Critical Issues, Total Feedback, and Positive Sentiment
- **Navigation Tabs**: Switch between "Real-time Alerts" and "Citizen Feedback"
- **Filtering**: Filter by Severity (All, Critical, Warning, Info) and Status (All, Active, Acknowledged, Resolved)
- **Real-time Data**: Dynamic loading of alerts and feedback based on selected filters

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --port 8001
```

3. Open your browser and navigate to:
```
http://localhost:8001
```

## Project Structure

```
Alertpage/`
├── main.py                 # FastAPI application with endpoints
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Main HTML template
└── static/
    ├── style.css          # CSS styles
    └── script.js          # JavaScript for interactivity
```

## API Endpoints

- `GET /` - Main dashboard page
- `GET /api/metrics` - Get dashboard metrics (active alerts, critical issues, etc.)
- `GET /api/alerts?severity=All&status=Resolved` - Get filtered alerts
- `GET /api/feedback?severity=All&status=All` - Get filtered feedback

## Notes

The dashboard matches the exact design structure with:
- Four metric cards at the top
- Navigation tabs for switching between alerts and feedback
- Filter buttons for Severity and Status
- Scrollable content area showing alert/feedback cards
- Responsive layout matching the original design

