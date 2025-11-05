# Chatbot & Agentic System Overview

## System Architecture

### **Supervisor Agent**
- **Role**: Orchestrates specialist agents using LangGraph workflow
- **Function**: Routes queries intelligently using LLM-based intent understanding
- **Work**: Coordinates multi-agent collaboration, synthesizes cross-sectoral intelligence, provides explainable AI logging

---

## Specialist Agents

### **1. Data Retrieval Agent**
- **Role**: Database query specialist
- **Function**: Translates natural language queries into optimized SQL
- **Work**: 
  - Executes database queries across all tables
  - Handles multi-district queries and comparisons
  - Extracts district information from queries
  - Validates SQL for security

### **2. Health Agent**
- **Role**: Health infrastructure and vulnerability analyst
- **Function**: Calculates Health Vulnerability Index (HVI) and predicts health capacity shortfalls
- **Work**:
  - Analyzes health infrastructure capacity (ICU beds, hospitals, PHCs)
  - Predicts disease spikes and emergency case volumes
  - Identifies critical health crises (threshold-based)
  - Generates actionable health recommendations

### **3. Infrastructure Agent**
- **Role**: Infrastructure capacity and demand forecasting specialist
- **Function**: Calculates Infrastructure Strain Score (ISS) and forecasts service request volume
- **Work**:
  - Analyzes infrastructure strain (roads, water treatment, electricity)
  - Forecasts service request volume and demand
  - Correlates infrastructure readiness with service requests
  - Generates infrastructure expansion recommendations

### **4. Resource Agent**
- **Role**: Worker resource utilization and availability analyst
- **Function**: Calculates Resource Contention Score (RCS) and audits worker utilization
- **Work**:
  - Monitors worker utilization rates and availability
  - Tracks escalated requests and response times
  - Identifies resource contention hotspots
  - Recommends worker allocation and deployment strategies

---

## Metrics System

### **1. HVI (Health Vulnerability Index)**
- **Formula**: (Predicted Emergency Cases / ICU Beds) × (Bed Occupancy Rate / Capacity)
- **Scale**: 0-10 (higher = more vulnerable)
- **Purpose**: Predicts disease spikes and identifies health capacity shortfalls
- **Use Case**: Early warning system for health crises

### **2. ISS (Infrastructure Strain Score)**
- **Formula**: (Service Request Volume / Infrastructure Capacity) × Demand Forecast
- **Scale**: 0-10 (higher = more strained)
- **Purpose**: Forecasts service request volume and correlates with infrastructure readiness
- **Use Case**: Identifies infrastructure bottlenecks and expansion needs

### **3. RCS (Resource Contention Score)**
- **Formula**: (Worker Utilization Rate / Available Workers) × (Escalated Requests / Total Requests)
- **Scale**: 0-10 (higher = more contention)
- **Purpose**: Audits worker utilization and availability against demand signals
- **Use Case**: Optimizes workforce allocation and prevents burnout

### **4. P-Score (Cross-Sectoral Prioritization Score)**
- **Formula**: Weighted average of HVI (40%), ISS (30%), and RCS (30%)
- **Scale**: 0-10 (higher = higher priority)
- **Purpose**: Unified prioritization metric combining all sectoral indicators
- **Use Case**: Cross-sectoral decision-making and resource prioritization

### **5. SEL (Service Equity Lag Index)**
- **Formula**: Average Resolution Time (Low Literacy) / Average Resolution Time (High Literacy)
- **Scale**: Ratio (>1.2 indicates equity gap)
- **Purpose**: Identifies systemic bias by comparing resolution times across demographic segments
- **Use Case**: Ensures equitable service delivery across all communities

---

## System Summary

**The intelligent chatbot system leverages a multi-agent architecture powered by LangGraph to deliver comprehensive cross-sectoral intelligence for government service delivery. The Supervisor Agent orchestrates four specialist agents—Data Retrieval, Health, Infrastructure, and Resource—each analyzing specific domains using advanced metrics (HVI, ISS, RCS, P-Score, SEL) to predict vulnerabilities, forecast demand, and optimize resource allocation. The system translates natural language queries into actionable insights, automatically routes complex multi-district comparisons, and provides explainable AI logging for transparent, data-driven decision-making that enables proactive public service management and equitable resource distribution.**

