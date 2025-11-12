# 04_Python Time Calculation Functions

**Created:** 8/29/2025 13:18:42  
**Updated:** 8/29/2025 18:21:59  
**Exported:** 10/17/2025 15:24:14  
**Link:** [https://claude.ai/chat/d69691ed-0a8d-43ae-ac76-dfe9de176aa1](https://claude.ai/chat/d69691ed-0a8d-43ae-ac76-dfe9de176aa1)  

## Prompt:
8/29/2025, 1:18:43 PM

provide the python code blocks for calculating time Spent and Time Response



## Response:
8/29/2025, 1:18:56 PM

Here are the Python code blocks for calculating Time Spent and Time Response:

## Time Spent Calculation

```python
from datetime import datetime, timedelta
import pandas as pd

def calculate_time_spent(start_time, end_time):
    """
    Calculate time spent between two timestamps
    
    Args:
        start_time: datetime object or string (YYYY-MM-DD HH:MM:SS)
        end_time: datetime object or string (YYYY-MM-DD HH:MM:SS)
    
    Returns:
        timedelta object representing time spent
    """
    # Convert strings to datetime if needed
    if isinstance(start_time, str):
        start_time = pd.to_datetime(start_time)
    if isinstance(end_time, str):
        end_time = pd.to_datetime(end_time)
    
    # Calculate difference
    time_spent = end_time - start_time
    
    return time_spent

# Example usage
start = "2024-08-29 14:30:00"
end = "2024-08-29 16:45:00"
duration = calculate_time_spent(start, end)
print(f"Time spent: {duration}")
print(f"Hours: {duration.total_seconds() / 3600:.2f}")
```

## Time Response Calculation

```python
def calculate_response_time(incident_time, arrival_time):
    """
    Calculate response time from incident to arrival
    
    Args:
        incident_time: datetime object or string when incident occurred
        arrival_time: datetime object or string when unit arrived
    
    Returns:
        timedelta object representing response time
    """
    # Convert strings to datetime if needed
    if isinstance(incident_time, str):
        incident_time = pd.to_datetime(incident_time)
    if isinstance(arrival_time, str):
        arrival_time = pd.to_datetime(arrival_time)
    
    # Calculate response time
    response_time = arrival_time - incident_time
    
    return response_time

# Example usage
incident = "2024-08-29 15:22:00"
arrival = "2024-08-29 15:28:30"
response = calculate_response_time(incident, arrival)
print(f"Response time: {response}")
print(f"Minutes: {response.total_seconds() / 60:.1f}")
```

## Batch Processing for DataFrames

```python
def process_time_calculations(df, start_col, end_col, new_col_name):
    """
    Calculate time differences for entire DataFrame
    
    Args:
        df: pandas DataFrame
        start_col: column name with start times
        end_col: column name with end times
        new_col_name: name for new calculated column
    
    Returns:
        DataFrame with new time calculation column
    """
    # Ensure datetime format
    df[start_col] = pd.to_datetime(df[start_col])
    df[end_col] = pd.to_datetime(df[end_col])
    
    # Calculate time difference
    df[new_col_name] = df[end_col] - df[start_col]
    
    # Add minutes column for easier analysis
    df[f"{new_col_name}_minutes"] = df[new_col_name].dt.total_seconds() / 60
    
    return df

# Example usage for response times
df = process_time_calculations(df, 'incident_time', 'arrival_time', 'response_time')
```

## Key Points:
- Handles both string and datetime inputs
- Returns timedelta objects for precise calculations
- Includes conversion to hours/minutes for reporting
- Batch processing function for large datasets
- Error handling can be added for invalid timestamps





---
Powered by [Claude Exporter](https://www.claudexporter.com)