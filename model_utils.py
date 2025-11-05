# app/model_utils.py
import os
import pandas as pd
import numpy as np
import json
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging
from typing import Tuple, Dict, Any, List

# Nixtla TimeGPT client
try:
    from nixtla import NixtlaClient
except Exception as e:
    NixtlaClient = None
    logging.warning("NixtlaClient import failed. Ensure nixtla package is installed.")

# Groq client for LLM-based insights
try:
    from groq import Groq
except Exception as e:
    Groq = None
    logging.warning("Groq import failed. Ensure groq package is installed.")

NIXTLA_API_KEY = os.getenv("NIXTLA_API_KEY", None)
if NixtlaClient is not None and NIXTLA_API_KEY:
    nixtla_client = NixtlaClient(api_key=NIXTLA_API_KEY)
else:
    nixtla_client = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
if Groq is not None and GEMINI_API_KEY:
    groq_client = Groq(api_key=GEMINI_API_KEY)
else:
    groq_client = None

CSV_PATH = os.getenv("DATA_CSV", "PHREWS2_timegpt_weekly_v2.csv")

def load_data() -> pd.DataFrame:
    """Load merged CSV into a dataframe and sanitize types."""
    # Get the full path to CSV file
    csv_path = CSV_PATH
    if not os.path.isabs(csv_path):
        # If relative path, look in the same directory as this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, CSV_PATH)
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path, parse_dates=["date"])
    
    # Map new column names to expected names
    if "taluka" in df.columns and "ward_id" not in df.columns:
        df["ward_id"] = df["taluka"]
    if "disease" in df.columns and "disease_type" not in df.columns:
        df["disease_type"] = df["disease"]
    
    # Use confirmed_cases as new_cases (prioritize confirmed_cases over true_cases)
    if "confirmed_cases" in df.columns and "new_cases" not in df.columns:
        df["new_cases"] = df["confirmed_cases"]
    elif "true_cases" in df.columns and "new_cases" not in df.columns:
        df["new_cases"] = df["true_cases"]
    
    # Check required columns
    required = {"unique_id", "date", "new_cases"}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"CSV missing required columns. Need: {required}, Found: {list(df.columns)}")
    
    # Ensure ward_id and disease_type exist (extract from unique_id if needed)
    if "ward_id" not in df.columns and "unique_id" in df.columns:
        df["ward_id"] = df["unique_id"].str.split("__").str[0]
    if "disease_type" not in df.columns and "unique_id" in df.columns:
        df["disease_type"] = df["unique_id"].str.split("__").str[1].fillna("Unknown")
    
    # Ensure correct dtypes
    df["unique_id"] = df["unique_id"].astype(str)
    df["ward_id"] = df["ward_id"].astype(str) if "ward_id" in df.columns else df["unique_id"].str.split("__").str[0].astype(str)
    df["disease_type"] = df["disease_type"].astype(str) if "disease_type" in df.columns else df["unique_id"].str.split("__").str[1].fillna("Unknown").astype(str)
    df["date"] = pd.to_datetime(df["date"])
    df["new_cases"] = pd.to_numeric(df["new_cases"], errors="coerce").fillna(0).astype(int)
    
    # Fill numeric exogenous missing values - updated list based on new dataset
    numeric_cols = [
        "rainfall_mm", "humidity", "temperature",
        "available_beds", "occupied_beds", "total_beds",
        "vacancy_rate", "lab_capacity", "public_reporting_rate", "private_reporting_rate",
        "private_ari_reports", "private_fever_reports",
        "antimalarial_sales", "rifampicin_sales", "taluka_antimalarial_sales", "taluka_rifampicin_sales",
        "mobility_index", "pharma_scale"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    
    return df

def list_series(df: pd.DataFrame) -> List[str]:
    return sorted(df["unique_id"].unique().tolist())

def prepare_series_df(df: pd.DataFrame, series_id: str) -> pd.DataFrame:
    s = df[df["unique_id"] == series_id].sort_values("date").reset_index(drop=True)
    return s

def compute_holdout_kpis(series_df: pd.DataFrame, forecast_fn, h: int = 8) -> Dict[str, Any]:
    """
    Evaluate forecast_fn on a simple holdout:
    - use last 2*h weeks as holdout, train on everything before that
    forecast_fn must accept (train_df, h) and return a forecast pd.Series or DataFrame with date & y_pred
    Returns MAE, RMSE, MAPE on holdout.
    """
    n = series_df.shape[0]
    if n < (h*3):
        # not enough points; return N/A
        return {"MAE": None, "RMSE": None, "MAPE": None, "note": "series too short for holdout evaluation"}
    train = series_df.iloc[:-h]
    test = series_df.iloc[-h:]
    # call forecast_fn
    preds = forecast_fn(train, h)
    # preds expected as pd.Series indexed by date or DataFrame with ['date','y_pred']
    if isinstance(preds, pd.Series):
        y_pred = preds.values
    else:
        # try DataFrame
        if "y_pred" in preds.columns:
            y_pred = preds["y_pred"].values
        elif "new_cases" in preds.columns:
            y_pred = preds["new_cases"].values
        else:
            y_pred = preds.iloc[:, -1].values  # take last column
    y_true = test["new_cases"].values
    # align lengths
    m = min(len(y_pred), len(y_true))
    y_pred = y_pred[:m]
    y_true = y_true[:m]
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = float(np.mean(np.abs((y_true - y_pred) / (np.where(y_true==0, 1, y_true)))) * 100.0)
    return {"MAE": mae, "RMSE": rmse, "MAPE_pct": mape, "n_test": m}

# --- TimeGPT wrapper ---
def timegpt_forecast(df: pd.DataFrame, series_id: str, h: int = 12,
                     external_regs: List[str] = None, finetune_steps: int = 0, 
                     auto_select_vars: bool = False) -> pd.DataFrame:
    """
    Call Nixtla TimeGPT to forecast a single series_id for h steps.
    If nixtla_client is not available, falls back to a naive seasonal-mean forecast.
    
    Args:
        df: Full dataframe with all series
        series_id: Unique series identifier
        h: Forecast horizon (recommended: 4-8 weeks for optimal accuracy)
        external_regs: List of external regressors (disabled for speed and reliability)
        finetune_steps: Number of finetuning steps
        auto_select_vars: If True, automatically select only relevant exogenous variables (disabled)
    
    Returns a DataFrame with columns: date, y_pred
    """
    series_df = prepare_series_df(df, series_id)
    
    # Disable exogenous variables for faster, more reliable forecasts
    external_regs = []
    
    # Improved fallback function
    def fallback_forecast(msg: str = "Nixtla client not available"):
        logging.warning(msg)
        last_date = series_df["date"].max()
        freq = series_df["date"].diff().median() or pd.Timedelta(days=7)
        future_dates = [last_date + (i+1)*freq for i in range(h)]
        
        # Use seasonal naive: average of last 4 weeks with trend adjustment
        recent_avg = series_df["new_cases"].tail(4).mean()
        historical_avg = series_df["new_cases"].mean()
        
        # Apply exponential smoothing for better forecast
        if len(series_df) >= 8:
            # Calculate trend
            recent_trend = series_df["new_cases"].tail(8)
            trend_coef = np.polyfit(range(len(recent_trend)), recent_trend.values, 1)[0]
            
            # Generate forecast with trend
            preds_vals = []
            for i in range(h):
                pred = max(0, recent_avg + trend_coef * (i + 1))
                preds_vals.append(int(pred))
        else:
            preds_vals = [max(0, int(recent_avg))] * h
        
        preds = pd.DataFrame({"date": future_dates, "y_pred": preds_vals})
        return preds
    
    if nixtla_client is None:
        return fallback_forecast("Nixtla client not available")

    # Prepare data for TimeGPT - filter to only the series we want to forecast
    try:
        # Filter df to only include the series we're forecasting
        df_for_forecast = series_df[["unique_id", "date", "new_cases"]].copy()
        
        # Forecast without exogenous variables (faster and more reliable)
        logging.info(f"Forecasting {series_id} for {h} weeks using TimeGPT")
        forecast_df = nixtla_client.forecast(
            df=df_for_forecast,
            h=h,
            time_col="date",
            target_col="new_cases",
            id_col="unique_id",
            finetune_steps=finetune_steps
        )
                        
    except Exception as e:
        # fallback to improved naive forecast
        return fallback_forecast(f"TimeGPT call failed; using fallback. Error: {e}")

    # forecast_df from nixtla contains predictions for all series. Filter for our series_id.
    # Nixtla TimeGPT typically returns columns: ['unique_id', 'ds', 'TimeGPT', 'TimeGPT-lo-90', 'TimeGPT-hi-90']
    logging.info(f"TimeGPT forecast columns: {forecast_df.columns.tolist()}")
    
    # Normalize column names to handle different TimeGPT API versions
    # TimeGPT uses 'ds' for date and 'TimeGPT' for predictions
    column_mapping = {}
    if 'ds' in forecast_df.columns:
        column_mapping['ds'] = 'date'
    if 'TimeGPT' in forecast_df.columns:
        column_mapping['TimeGPT'] = 'y_pred'
    elif 'timegpt' in forecast_df.columns:
        column_mapping['timegpt'] = 'y_pred'
    
    if column_mapping:
        forecast_df = forecast_df.rename(columns=column_mapping)
    
    # Now extract the specific series
    if "unique_id" in forecast_df.columns:
        f = forecast_df[forecast_df["unique_id"] == series_id].copy()
    else:
        f = forecast_df.copy()
    
    # Ensure we have the required columns
    if "date" not in f.columns:
        raise RuntimeError(f"'date' column not found in forecast output. Available columns: {f.columns.tolist()}")
    if "y_pred" not in f.columns:
        # Try alternative column names
        if "new_cases" in f.columns:
            f = f.rename(columns={"new_cases": "y_pred"})
        else:
            raise RuntimeError(f"'y_pred' column not found in forecast output. Available columns: {f.columns.tolist()}")
    
    # Select only required columns
    f = f[["date", "y_pred"]].copy()
    
    # Ensure date parsed
    f["date"] = pd.to_datetime(f["date"])
    return f.reset_index(drop=True)

# --- Data Analysis Functions ---
def get_overall_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Get overall statistics for the dataset."""
    stats = {
        "total_cases": int(df["new_cases"].sum()),
        "avg_weekly_cases": float(df["new_cases"].mean()),
        "total_weeks": int(df["date"].nunique()),
        "unique_wards": int(df["ward_id"].nunique()),
        "unique_diseases": int(df["disease_type"].nunique()),
        "date_range": {
            "start": str(df["date"].min()),
            "end": str(df["date"].max())
        }
    }
    return stats

def get_disease_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """Get disease type distribution."""
    disease_stats = df.groupby("disease_type").agg({
        "new_cases": ["sum", "mean", "count"]
    }).reset_index()
    disease_stats.columns = ["disease_type", "total_cases", "avg_cases", "weeks"]
    disease_stats = disease_stats.sort_values("total_cases", ascending=False)
    
    # Convert to dict format
    result = {
        "diseases": disease_stats["disease_type"].tolist(),
        "total_cases": disease_stats["total_cases"].astype(int).tolist(),
        "avg_cases": disease_stats["avg_cases"].round(2).tolist()
    }
    return result

def get_ward_analysis(df: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
    """Get top wards by total cases."""
    ward_stats = df.groupby("ward_id").agg({
        "new_cases": ["sum", "mean"],
        "disease_type": "nunique"
    }).reset_index()
    ward_stats.columns = ["ward_id", "total_cases", "avg_cases", "num_diseases"]
    ward_stats = ward_stats.sort_values("total_cases", ascending=False).head(top_n)
    
    result = {
        "wards": ward_stats["ward_id"].tolist(),
        "total_cases": ward_stats["total_cases"].astype(int).tolist(),
        "avg_cases": ward_stats["avg_cases"].round(2).tolist(),
        "num_diseases": ward_stats["num_diseases"].astype(int).tolist()
    }
    return result

def get_time_trends(df: pd.DataFrame, period: str = "weekly") -> Dict[str, Any]:
    """Get time-based trends."""
    df_copy = df.copy()
    df_copy["date"] = pd.to_datetime(df_copy["date"])
    
    if period == "monthly":
        df_copy["period"] = df_copy["date"].dt.to_period("M")
        period_label = "month"
    else:  # weekly
        df_copy["period"] = df_copy["date"].dt.to_period("W")
        period_label = "week"
    
    trend_data = df_copy.groupby("period").agg({
        "new_cases": ["sum", "mean"]
    }).reset_index()
    trend_data.columns = ["period", "total_cases", "avg_cases"]
    trend_data["period"] = trend_data["period"].astype(str)
    
    result = {
        "periods": trend_data["period"].tolist(),
        "total_cases": trend_data["total_cases"].astype(int).tolist(),
        "avg_cases": trend_data["avg_cases"].round(2).tolist()
    }
    return result

def get_correlation_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Get correlations between new_cases and external regressors."""
    # Updated list of potential exogenous variables based on new dataset
    numeric_cols = [
        "new_cases", "rainfall_mm", "humidity", "temperature",
        "available_beds", "occupied_beds", "total_beds",
        "vacancy_rate", "lab_capacity", "public_reporting_rate", "private_reporting_rate",
        "private_ari_reports", "private_fever_reports",
        "antimalarial_sales", "rifampicin_sales", "taluka_antimalarial_sales", "taluka_rifampicin_sales",
        "mobility_index", "pharma_scale"
    ]
    available_cols = [c for c in numeric_cols if c in df.columns]
    
    if len(available_cols) < 2:
        return {"correlations": {}, "available_vars": available_cols}
    
    corr_matrix = df[available_cols].corr()
    correlations = {}
    
    for var in available_cols:
        if var != "new_cases":
            corr_val = corr_matrix.loc["new_cases", var]
            if not pd.isna(corr_val):
                correlations[var] = float(corr_val)
    
    # Sort by absolute correlation
    correlations = dict(sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True))
    
    return {
        "correlations": correlations,
        "available_vars": available_cols
    }

def select_relevant_exogenous_variables(series_df: pd.DataFrame, min_correlation: float = 0.1) -> List[str]:
    """
    Select only relevant exogenous variables based on correlation with new_cases.
    Returns list of variables with absolute correlation >= min_correlation.
    """
    # Updated list of potential exogenous variables based on new dataset
    potential_vars = [
        "rainfall_mm", "humidity", "temperature",
        "available_beds", "occupied_beds", "total_beds",
        "vacancy_rate", "lab_capacity", "public_reporting_rate", "private_reporting_rate",
        "private_ari_reports", "private_fever_reports",
        "antimalarial_sales", "rifampicin_sales", "taluka_antimalarial_sales", "taluka_rifampicin_sales",
        "mobility_index", "pharma_scale"
    ]
    
    available_vars = [v for v in potential_vars if v in series_df.columns]
    
    if len(available_vars) == 0 or "new_cases" not in series_df.columns:
        return []
    
    # Calculate correlations
    correlations = {}
    for var in available_vars:
        try:
            corr_val = series_df["new_cases"].corr(series_df[var])
            if not pd.isna(corr_val) and abs(corr_val) >= min_correlation:
                correlations[var] = abs(corr_val)
        except:
            continue
    
    # Sort by absolute correlation and return top variables
    sorted_vars = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
    
    # Return variables with meaningful correlation (at least 0.1)
    selected = [var for var, corr in sorted_vars if corr >= min_correlation]
    
    # Limit to top 5-8 most correlated variables to avoid overfitting
    # Always include at least top 3-5 if available
    if len(selected) > 8:
        selected = selected[:8]
    elif len(selected) == 0 and len(sorted_vars) > 0:
        # If no variables meet threshold, take top 3-5 anyway
        selected = [var for var, _ in sorted_vars[:min(5, len(sorted_vars))]]
    
    return selected

def generate_ai_insights(series_df: pd.DataFrame, forecast_df: pd.DataFrame, 
                         kpis: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate AI-powered insights using Groq LLM (Llama model) by analyzing the actual 
    forecast chart/pattern data from TimeGPT results.
    Returns structured insights as a dictionary.
    """
    insights = {
        "trend_analysis": [],
        "forecast_insights": [],
        "risk_assessment": [],
        "recommendations": []
    }
    
    # If Groq client is not available, fall back to rule-based insights
    if groq_client is None:
        logging.warning("Groq client not available, using rule-based insights")
        return _generate_rule_based_insights(series_df, forecast_df, kpis)
    
    try:
        # Prepare detailed forecast chart/pattern analysis
        recent_data = series_df.tail(12)
        older_data = series_df.iloc[:-12] if len(series_df) > 12 else series_df.head(len(series_df)//2)
        
        recent_avg = recent_data["new_cases"].mean()
        older_avg = older_data["new_cases"].mean() if len(older_data) > 0 else recent_avg
        trend_change = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        
        # Analyze forecast pattern/chart
        forecast_avg = forecast_df["y_pred"].mean()
        forecast_max = forecast_df["y_pred"].max()
        forecast_min = forecast_df["y_pred"].min()
        forecast_std = forecast_df["y_pred"].std()
        
        # Calculate forecast trend (increasing, decreasing, stable)
        if len(forecast_df) >= 3:
            first_third = forecast_df["y_pred"].iloc[:len(forecast_df)//3].mean()
            last_third = forecast_df["y_pred"].iloc[-len(forecast_df)//3:].mean()
            forecast_trend = ((last_third - first_third) / first_third * 100) if first_third > 0 else 0
        else:
            forecast_trend = 0
        
        # Peak detection in forecast
        forecast_peaks = []
        for i in range(1, len(forecast_df) - 1):
            if forecast_df["y_pred"].iloc[i] > forecast_df["y_pred"].iloc[i-1] and \
               forecast_df["y_pred"].iloc[i] > forecast_df["y_pred"].iloc[i+1]:
                forecast_peaks.append((i, forecast_df["y_pred"].iloc[i]))
        
        last_observed = series_df["new_cases"].iloc[-1]
        historical_max = series_df["new_cases"].max()
        historical_avg = series_df["new_cases"].mean()
        historical_std = series_df["new_cases"].std()
        
        # Calculate volatility
        historical_volatility = (historical_std / historical_avg * 100) if historical_avg > 0 else 0
        forecast_volatility = (forecast_std / forecast_avg * 100) if forecast_avg > 0 else 0
        
        # Extract series information
        if "unique_id" in series_df.columns:
            series_id = series_df["unique_id"].iloc[0]
            ward_id = series_df["ward_id"].iloc[0] if "ward_id" in series_df.columns else "Unknown"
            disease_type = series_df["disease_type"].iloc[0] if "disease_type" in series_df.columns else "Unknown"
        else:
            series_id = "Unknown"
            ward_id = "Unknown"
            disease_type = "Unknown"
        
        # Prepare forecast chart data points (last 12 historical + forecast for pattern analysis)
        historical_chart = series_df.tail(12)[["date", "new_cases"]].copy()
        historical_chart["type"] = "historical"
        forecast_chart = forecast_df[["date", "y_pred"]].copy()
        forecast_chart = forecast_chart.rename(columns={"y_pred": "new_cases"})
        forecast_chart["type"] = "forecast"
        
        # Build comprehensive prompt with chart/pattern analysis
        prompt = f"""You are an expert public health data analyst. Analyze the TimeGPT forecast results and chart patterns to provide structured insights.

SERIES INFORMATION:
- Series ID: {series_id}
- Ward: {ward_id}
- Disease Type: {disease_type}
- Total historical weeks: {len(series_df)}
- Date range: {series_df['date'].min()} to {series_df['date'].max()}

HISTORICAL DATA PATTERN (Last 12 weeks):
- Historical average cases per week: {historical_avg:.1f}
- Historical maximum cases: {historical_max:.0f}
- Historical standard deviation: {historical_std:.1f}
- Historical volatility: {historical_volatility:.1f}%
- Recent 12 weeks average: {recent_avg:.1f}
- Older period average: {older_avg:.1f}
- Trend change: {trend_change:.1f}% (positive = increasing, negative = decreasing)
- Last observed week cases: {last_observed:.0f}

FORECAST CHART/PATTERN ANALYSIS ({len(forecast_df)} weeks ahead):
- Forecast average cases per week: {forecast_avg:.1f}
- Forecast maximum: {forecast_max:.0f}
- Forecast minimum: {forecast_min:.0f}
- Forecast standard deviation: {forecast_std:.1f}
- Forecast volatility: {forecast_volatility:.1f}%
- Forecast trend: {forecast_trend:.1f}% (first third vs last third of forecast period)
- Number of forecast peaks detected: {len(forecast_peaks)}
- Forecast change from last observed: {((forecast_avg - last_observed) / last_observed * 100) if last_observed > 0 else 0:.1f}%

FORECAST PATTERN DETAILS:
"""
        
        # Add forecast pattern details
        if len(forecast_peaks) > 0:
            peak_info = ", ".join([f"Week {i+1}: {val:.0f} cases" for i, val in forecast_peaks[:3]])
            prompt += f"- Peaks detected at: {peak_info}\n"
        else:
            prompt += "- No clear peaks detected in forecast (relatively stable pattern)\n"
        
        # Add forecast trend description
        if forecast_trend > 5:
            prompt += f"- Forecast shows INCREASING trend ({forecast_trend:.1f}% increase from start to end)\n"
        elif forecast_trend < -5:
            prompt += f"- Forecast shows DECREASING trend ({abs(forecast_trend):.1f}% decrease from start to end)\n"
        else:
            prompt += "- Forecast shows RELATIVELY STABLE pattern (minimal trend)\n"
        
        prompt += """
MODEL PERFORMANCE METRICS:
"""
        
        if kpis:
            mape = kpis.get("MAPE_pct", None)
            mae = kpis.get("MAE", None)
            rmse = kpis.get("RMSE", None)
            mape_str = f"{mape:.1f}%" if mape is not None else "N/A"
            mae_str = f"{mae:.2f}" if mae is not None else "N/A"
            rmse_str = f"{rmse:.2f}" if rmse is not None else "N/A"
            prompt += f"""- MAPE (Mean Absolute Percentage Error): {mape_str}
- MAE (Mean Absolute Error): {mae_str}
- RMSE (Root Mean Square Error): {rmse_str}
"""
        else:
            prompt += "- Model performance metrics: Not available\n"
        
        prompt += """
Please analyze the FORECAST CHART PATTERN and provide structured insights in the following JSON format:
{
  "trend_analysis": ["2-3 insights about the historical trend pattern and how it relates to the forecast"],
  "forecast_insights": ["2-3 insights about the forecast chart pattern - analyze the shape, trend, peaks, volatility"],
  "risk_assessment": ["1-2 risk assessments based on forecast peaks, volatility, and comparison to historical maximums"],
  "recommendations": ["2-3 actionable recommendations based on the forecast pattern analysis"]
}

Requirements:
- Focus on analyzing the FORECAST CHART PATTERN (trend, peaks, volatility, shape)
- Compare forecast pattern to historical patterns
- Be specific and data-driven - use the actual numbers from the forecast
- Identify patterns: increasing/decreasing trends, peaks, volatility changes
- Provide actionable insights based on the forecast chart analysis
- Focus on public health implications of the forecast pattern
- Keep each insight concise (1-2 sentences)
- Return ONLY valid JSON, no additional text

JSON Response:"""
        
        # Call Groq API with Llama model
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert public health data analyst. Provide structured, data-driven insights in JSON format only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",  # Using Llama 3.3 70B model (updated from deprecated 3.1)
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        # Parse LLM response
        response_text = chat_completion.choices[0].message.content
        
        # Try to parse JSON response
        try:
            llm_insights = json.loads(response_text)
            
            # Extract insights from LLM response
            if "trend_analysis" in llm_insights:
                insights["trend_analysis"] = llm_insights["trend_analysis"] if isinstance(llm_insights["trend_analysis"], list) else [llm_insights["trend_analysis"]]
            if "forecast_insights" in llm_insights:
                insights["forecast_insights"] = llm_insights["forecast_insights"] if isinstance(llm_insights["forecast_insights"], list) else [llm_insights["forecast_insights"]]
            if "risk_assessment" in llm_insights:
                insights["risk_assessment"] = llm_insights["risk_assessment"] if isinstance(llm_insights["risk_assessment"], list) else [llm_insights["risk_assessment"]]
            if "recommendations" in llm_insights:
                insights["recommendations"] = llm_insights["recommendations"] if isinstance(llm_insights["recommendations"], list) else [llm_insights["recommendations"]]
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse LLM JSON response: {e}")
            logging.error(f"Response text: {response_text}")
            # Fall back to rule-based insights
            return _generate_rule_based_insights(series_df, forecast_df, kpis)
        
    except Exception as e:
        logging.exception(f"Error generating LLM insights: {e}")
        # Fall back to rule-based insights
        return _generate_rule_based_insights(series_df, forecast_df, kpis)
    
    return insights

def _generate_rule_based_insights(series_df: pd.DataFrame, forecast_df: pd.DataFrame, 
                                  kpis: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Fallback rule-based insights generation if LLM is not available.
    """
    insights = {
        "trend_analysis": [],
        "forecast_insights": [],
        "risk_assessment": [],
        "recommendations": []
    }
    
    # Analyze historical trend
    recent_data = series_df.tail(12)
    older_data = series_df.iloc[:-12] if len(series_df) > 12 else series_df.head(len(series_df)//2)
    
    recent_avg = recent_data["new_cases"].mean()
    older_avg = older_data["new_cases"].mean() if len(older_data) > 0 else recent_avg
    
    trend_change = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
    
    if abs(trend_change) > 10:
        direction = "increasing" if trend_change > 0 else "decreasing"
        insights["trend_analysis"].append(
            f"Recent trend shows a {abs(trend_change):.1f}% {direction} in cases compared to historical average."
        )
    else:
        insights["trend_analysis"].append("Case numbers are relatively stable compared to historical average.")
    
    # Analyze forecast
    forecast_avg = forecast_df["y_pred"].mean()
    last_observed = series_df["new_cases"].iloc[-1]
    forecast_change = ((forecast_avg - last_observed) / last_observed * 100) if last_observed > 0 else 0
    
    if abs(forecast_change) > 15:
        direction = "increase" if forecast_change > 0 else "decrease"
        insights["forecast_insights"].append(
            f"Forecast predicts a {abs(forecast_change):.1f}% {direction} in average weekly cases over the forecast period."
        )
    else:
        insights["forecast_insights"].append("Forecast indicates stable case numbers in the coming weeks.")
    
    # Peak analysis
    forecast_max = forecast_df["y_pred"].max()
    historical_max = series_df["new_cases"].max()
    
    if forecast_max > historical_max * 0.8:
        insights["risk_assessment"].append(
            f"Forecasted peak ({forecast_max:.0f} cases) approaches historical maximum ({historical_max:.0f} cases). "
            "Consider preparing additional resources."
        )
    
    # Model accuracy insights
    if kpis and kpis.get("MAPE_pct"):
        mape = kpis["MAPE_pct"]
        if mape < 20:
            insights["forecast_insights"].append(
                f"Model shows good accuracy with MAPE of {mape:.1f}%, indicating reliable forecasts."
            )
        elif mape < 40:
            insights["forecast_insights"].append(
                f"Model accuracy is moderate (MAPE: {mape:.1f}%). Forecasts should be interpreted with caution."
            )
        else:
            insights["forecast_insights"].append(
                f"Model shows lower accuracy (MAPE: {mape:.1f}%). Consider additional data or model refinement."
            )
    
    # Seasonal pattern detection
    if len(series_df) > 52:
        series_df_copy = series_df.copy()
        series_df_copy["month"] = series_df_copy["date"].dt.month
        monthly_avg = series_df_copy.groupby("month")["new_cases"].mean()
        peak_month = monthly_avg.idxmax()
        
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        insights["trend_analysis"].append(
            f"Historical data shows peak activity typically occurs in {month_names[peak_month-1]}."
        )
    
    # Recommendations
    if forecast_avg > recent_avg * 1.2:
        insights["recommendations"].append(
            "Forecast indicates increasing case load. Consider proactive resource allocation and public health messaging."
        )
    elif forecast_avg < recent_avg * 0.8:
        insights["recommendations"].append(
            "Forecast shows declining trend. Good time to review and optimize resource utilization."
        )
    
    if kpis and kpis.get("last_week_cases"):
        last_week = kpis["last_week_cases"]
        if last_week > forecast_avg * 1.5:
            insights["recommendations"].append(
                "Last week's cases were significantly higher than forecasted average. Monitor closely for potential outbreak."
            )
    
    return insights