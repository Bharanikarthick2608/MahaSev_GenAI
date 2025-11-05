"""
Pydantic models for database tables.
These models represent the schema for the 4 main tables.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ServiceRequestDetails(BaseModel):
    """Model for service_request_details table."""
    Request_ID: str
    Created_Timestamp: Optional[datetime] = None
    Service_Category: Optional[str] = None
    Sub_Category: Optional[str] = None
    Priority: Optional[str] = None
    Status: Optional[str] = None
    District: Optional[str] = None
    Area: Optional[str] = None
    Email_ID: Optional[str] = None
    Channel: Optional[str] = None
    Citizen_Age_Group: Optional[str] = None
    Resolution_Time_Hours: Optional[float] = None
    Escalated: Optional[bool] = None
    Satisfaction_Rating: Optional[float] = None
    Assigned_Department: Optional[str] = None
    Worker_Assigned: Optional[str] = None

    class Config:
        from_attributes = True


class PublicWorkersData(BaseModel):
    """Model for public_workers_data table."""
    District: str
    Worker_Type: Optional[str] = None
    Worker_Type_District: Optional[str] = None
    Total_Workers: Optional[int] = None
    Available_Workers: Optional[int] = None
    On_Duty: Optional[int] = None
    Avg_Experience_Years: Optional[float] = None
    Avg_Monthly_Salary_INR: Optional[float] = None
    Training_Status: Optional[str] = None
    Utilization_Rate_Percentage: Optional[float] = None
    Avg_Response_Time_Minutes: Optional[float] = None

    class Config:
        from_attributes = True


class AreaWiseDemographicsInfrastructure(BaseModel):
    """Model for area_wise_demographics_infrastructure table."""
    District: str
    Population: Optional[int] = None
    Urban_Population_Percentage: Optional[float] = None
    Area_Sq_Km: Optional[float] = None
    Hospitals: Optional[int] = None
    Primary_Health_Centers: Optional[int] = None
    Schools: Optional[int] = None
    Police_Stations: Optional[int] = None
    Fire_Stations: Optional[int] = None
    Roads_Km: Optional[float] = None
    Water_Treatment_Plants: Optional[int] = None
    Electricity_Substations: Optional[int] = None
    Literacy_Rate: Optional[float] = None
    Internet_Penetration_Percentage: Optional[float] = None
    Avg_Income_INR: Optional[float] = None

    class Config:
        from_attributes = True


class HealthInfrastructureData(BaseModel):
    """Model for health_infrastructure_data table."""
    District: str
    Total_Beds: Optional[int] = None
    ICU_Beds: Optional[int] = None
    Ventilators: Optional[int] = None
    Doctors: Optional[int] = None
    Nurses: Optional[int] = None
    Ambulances: Optional[int] = None
    Blood_Bank_Units: Optional[int] = None
    Diagnostic_Centers: Optional[int] = None
    Pharmacy_Count: Optional[int] = None
    Avg_Bed_Occupancy_Rate: Optional[float] = None
    Emergency_Cases_Per_Month: Optional[int] = None
    Maternal_Health_Centers: Optional[int] = None

    class Config:
        from_attributes = True


# Schema information for SQL generation
TABLE_SCHEMAS = {
    "service_request_details": {
        "table_name": "service_request_details",
        "columns": [
            "Request_ID", "Created_Timestamp", "Service_Category", "Sub_Category",
            "Priority", "Status", "District", "Area", "Email_ID", "Channel",
            "Citizen_Age_Group", "Resolution_Time_Hours", "Escalated",
            "Satisfaction_Rating", "Assigned_Department", "Worker_Assigned"
        ],
        "description": "Citizen service requests with resolution details and assignments"
    },
    "public_workers_data": {
        "table_name": "public_workers_data",
        "columns": [
            "District", "Worker_Type", "Worker_Type_District", "Total_Workers",
            "Available_Workers", "On_Duty", "Avg_Experience_Years",
            "Avg_Monthly_Salary_INR", "Training_Status", "Utilization_Rate_Percentage",
            "Avg_Response_Time_Minutes"
        ],
        "description": "Public worker capacity, availability, and utilization metrics by district"
    },
    "area_wise_demographics_infrastructure": {
        "table_name": "area_wise_demographics_infrastructure",
        "columns": [
            "District", "Population", "Urban_Population_Percentage", "Area_Sq_Km",
            "Hospitals", "Primary_Health_Centers", "Schools", "Police_Stations",
            "Fire_Stations", "Roads_Km", "Water_Treatment_Plants",
            "Electricity_Substations", "Literacy_Rate", "Internet_Penetration_Percentage",
            "Avg_Income_INR"
        ],
        "description": "Demographic and static infrastructure data by district"
    },
    "health_infrastructure_data": {
        "table_name": "health_infrastructure_data",
        "columns": [
            "District", "Total_Beds", "ICU_Beds", "Ventilators", "Doctors", "Nurses",
            "Ambulances", "Blood_Bank_Units", "Diagnostic_Centers", "Pharmacy_Count",
            "Avg_Bed_Occupancy_Rate", "Emergency_Cases_Per_Month", "Maternal_Health_Centers"
        ],
        "description": "Health infrastructure capacity and utilization by district"
    }
}

