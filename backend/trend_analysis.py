import numpy as np
from datetime import datetime, timedelta

def calculate_risk_trend(history_logs):
    """
    Fits a simple linear regression to the property risk history and projects the score 30 days ahead.
    history_logs: List of dicts, e.g. [{"timestamp": "2026-06-22T09:00:00Z", "score": 10.0}]
    
    Returns:
        dict: {
            "slope": float,
            "projected_score": float,
            "trend_direction": str,
            "trend_description": str,
            "projection_data": list of dicts (for plotting)
        }
    """
    if len(history_logs) < 2:
        # Fallback if there is not enough history
        current_score = history_logs[0]["score"] if history_logs else 0.0
        return {
            "slope": 0.0,
            "projected_score": current_score,
            "trend_direction": "Stable",
            "trend_description": "Insufficient history to predict trends. (Stable)",
            "projection_data": []
        }
    
    # Extract timestamps and scores
    dates = []
    scores = []
    
    for log in history_logs:
        try:
            # Handle ISO formats with or without Z
            dt_str = log["timestamp"].replace("Z", "")
            dt = datetime.fromisoformat(dt_str)
            dates.append(dt)
            scores.append(float(log["score"]))
        except Exception:
            continue
            
    if len(dates) < 2:
        current_score = scores[-1] if scores else 0.0
        return {
            "slope": 0.0,
            "projected_score": current_score,
            "trend_direction": "Stable",
            "trend_description": "Insufficient valid dates. (Stable)",
            "projection_data": []
        }
    
    # Convert dates to relative float days since the first record
    start_date = min(dates)
    x = np.array([(d - start_date).total_seconds() / 86400.0 for d in dates])
    y = np.array(scores)
    
    # Calculate slope and intercept using numpy polyfit
    try:
        slope, intercept = np.polyfit(x, y, 1)
    except Exception:
        # If calculation fails (e.g. all x are identical), fall back
        slope = 0.0
        intercept = y[-1]
    
    # Project 30 days from the last date
    last_date = dates[-1]
    days_since_start_to_last = (last_date - start_date).total_seconds() / 86400.0
    days_projected = days_since_start_to_last + 30.0
    
    projected_score = (slope * days_projected) + intercept
    
    # Clamp between 0 and 100
    projected_score = max(0.0, min(100.0, float(projected_score)))
    current_score = scores[-1]
    
    change = projected_score - current_score
    
    if slope > 0.1:
        trend_direction = "Increasing"
        trend_description = f"Risk trending upwards. Projected next month: {projected_score:.1f}% (+{change:.1f}%)"
    elif slope < -0.1:
        trend_direction = "Decreasing"
        trend_description = f"Risk trending downwards. Projected next month: {projected_score:.1f}% ({change:.1f}%)"
    else:
        trend_direction = "Stable"
        trend_description = f"Risk is stable. Projected next month: {projected_score:.1f}% (0.0% change)"
        
    # Generate points for trendline
    # We will generate a start point, end history point, and the projected point
    proj_date = last_date + timedelta(days=30)
    
    projection_data = [
        {"timestamp": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"), "score": float(intercept)},
        {"timestamp": last_date.strftime("%Y-%m-%dT%H:%M:%SZ"), "score": float((slope * days_since_start_to_last) + intercept)},
        {"timestamp": proj_date.strftime("%Y-%m-%dT%H:%M:%SZ"), "score": projected_score}
    ]
    
    return {
        "slope": float(slope),
        "projected_score": float(projected_score),
        "trend_direction": trend_direction,
        "trend_description": trend_description,
        "projection_data": projection_data
    }
