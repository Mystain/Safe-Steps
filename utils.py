import os
import json
import pandas as pd
import numpy as np
import datetime
import logging
import sqlite3
from collections import Counter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_analytics_data(area=None, is_admin=False):
    """Generate analytics data for the dashboard"""
    try:
        # Define Kurla areas
        kurla_areas = [
            "Kurla West", "Kurla East", "Kurla Station", "BKC", "Nehru Nagar", 
            "Tilak Nagar", "Chunabhatti", "Chembur", "Saki Naka", "Asalpha", 
            "Vinoba Bhave Nagar", "LBS Marg", "Kamani", "Premier Colony",
            "Kalina", "Santacruz East", "Vidyavihar", "Lokmanya Tilak Terminus",
            "Sion", "Jarimari", "Safed Pool"
        ]
        
        # Initialize data structures
        area_data = {area: 0 for area in kurla_areas}
        crime_types = {
            "Theft": 0,
            "Vehicle Theft": 0,
            "Assault": 0,
            "Robbery": 0,
            "Vandalism": 0,
            "Harassment": 0,
            "Drug-related": 0,
            "Fraud": 0,
            "Murder": 0,
            "Kidnapping": 0,
            "Other": 0
        }
        
        # Get data from map data file for area coordinates
        map_data_path = os.path.join('static', 'data', 'map', 'crime_map_data.json')
        map_data = {}
        
        if os.path.exists(map_data_path):
            try:
                with open(map_data_path, 'r') as f:
                    map_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading map data: {str(e)}")
        
        # Initialize heatmap data and trend data
        heatmap_data = []
        now = datetime.datetime.now()
        trend_labels = []
        trend_values = [0, 0, 0, 0, 0, 0]  # Initialize with zeros
        
        # Generate trend labels (last 6 months)
        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            if month <= 0:
                month += 12
                year -= 1
            trend_labels.append(datetime.datetime(year, month, 1).strftime("%b %Y"))
        
        # 1. Process database reports
        try:
            # Connect to the database
            conn = sqlite3.connect('reports.db')
            cursor = conn.cursor()
            
            # Get all reports from the database
            cursor.execute("SELECT id, date, description, lat, lng FROM reports")
            db_reports = cursor.fetchall()
            
            # Process each report
            for report in db_reports:
                report_id, date_str, description, lat, lng = report
                
                # Determine crime type
                crime_type = determine_crime_type(description)
                crime_types[crime_type] = crime_types.get(crime_type, 0) + 1
                
                # Add to area data
                if lat and lng:
                    area_name = find_area_by_coordinates(lat, lng, map_data, kurla_areas)
                    area_data[area_name] = area_data.get(area_name, 0) + 1
                    
                    # Add to heatmap
                    heatmap_data.append({
                        "lat": lat,
                        "lng": lng,
                        "weight": 1
                    })
                
                # Add to trend data
                if date_str:
                    try:
                        report_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                        for i, label in enumerate(trend_labels):
                            label_date = datetime.datetime.strptime(label, "%b %Y")
                            if report_date.year == label_date.year and report_date.month == label_date.month:
                                trend_values[i] += 1
                                break
                    except Exception as e:
                        logger.error(f"Error parsing date {date_str}: {str(e)}")
            
            conn.close()
        except Exception as e:
            logger.error(f"Error processing database reports: {str(e)}")
        
        # 2. Process news article analysis
        try:
            news_analysis_path = os.path.join('static', 'data', 'news_analysis', 'crime_analysis.json')
            
            if os.path.exists(news_analysis_path):
                with open(news_analysis_path, 'r') as f:
                    news_analysis = json.load(f)
                
                # Add crime categories from news
                if 'crime_categories' in news_analysis:
                    for crime_type, count in news_analysis['crime_categories'].items():
                        # Map news crime types to our standardized types
                        mapped_type = map_crime_type(crime_type)
                        crime_types[mapped_type] = crime_types.get(mapped_type, 0) + count
                
                # Add crime locations from news
                if 'crime_locations' in news_analysis:
                    for location, count in news_analysis['crime_locations'].items():
                        # Map news locations to our standardized areas
                        area_name = map_location_to_area(location, kurla_areas)
                        area_data[area_name] = area_data.get(area_name, 0) + count
                
                # Process recent incidents for trend data
                if 'recent_incidents' in news_analysis:
                    for incident in news_analysis['recent_incidents']:
                        if 'date' in incident:
                            try:
                                # Try different date formats
                                incident_date = None
                                date_formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"]
                                
                                for fmt in date_formats:
                                    try:
                                        incident_date = datetime.datetime.strptime(incident['date'], fmt)
                                        break
                                    except:
                                        continue
                                
                                if incident_date:
                                    for i, label in enumerate(trend_labels):
                                        label_date = datetime.datetime.strptime(label, "%b %Y")
                                        if incident_date.year == label_date.year and incident_date.month == label_date.month:
                                            trend_values[i] += 1
                                            break
                            except Exception as e:
                                logger.error(f"Error parsing incident date: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing news analysis: {str(e)}")
        
        # Filter by selected area if specified
        filtered_area_data = {}
        if area:
            for k, v in area_data.items():
                if area.lower() in k.lower() or k.lower() in area.lower():
                    filtered_area_data[k] = v
                    
            if filtered_area_data:
                area_data = filtered_area_data
        
        # Calculate percent change
        if len(trend_values) >= 2 and trend_values[-2] > 0:
            percent_change = ((trend_values[-1] - trend_values[-2]) / trend_values[-2]) * 100
        else:
            percent_change = 0
        
        # Sort crime types by count (descending)
        sorted_types = sorted(crime_types.items(), key=lambda x: x[1], reverse=True)
        type_labels = [item[0] for item in sorted_types]
        type_values = [item[1] for item in sorted_types]
        
        # Calculate total reports
        total_reports = sum(type_values)
        
        # Calculate high risk areas (areas with incident count > 7)
        high_risk_areas = sum(1 for count in area_data.values() if count > 7)
        
        # Calculate average daily reports (assuming data is for the last 30 days)
        avg_daily_reports = round(total_reports / 30, 1)
        
        # Find most common crime
        most_common_crime = type_labels[0] if type_labels else "None"
        most_common_percent = round((type_values[0] / sum(type_values) * 100) if type_values and sum(type_values) > 0 else 0)
        
        # Return all the data
        return {
            "kurla_areas": kurla_areas,
            "area_data": area_data,
            "trend_labels": trend_labels,
            "trend_values": trend_values,
            "type_labels": type_labels,
            "type_values": type_values,
            "heatmap_data": heatmap_data,
            "percent_change": percent_change,
            "total_reports": total_reports,
            "high_risk_areas": high_risk_areas,
            "avg_daily_reports": avg_daily_reports,
            "most_common_crime": most_common_crime,
            "most_common_percent": most_common_percent
        }
    except Exception as e:
        logger.error(f"Error generating analytics data: {str(e)}")
        # Return empty data in case of error
        return {
            "kurla_areas": [],
            "area_data": {},
            "trend_labels": [],
            "trend_values": [],
            "type_labels": [],
            "type_values": [],
            "heatmap_data": [],
            "percent_change": 0,
            "total_reports": 0,
            "high_risk_areas": 0,
            "avg_daily_reports": 0,
            "most_common_crime": "None",
            "most_common_percent": 0
        }

def determine_crime_type(description):
    """Determine crime type from description using keyword matching"""
    if not description:
        return "Other"
        
    description = str(description).lower()
    
    if any(word in description for word in ['theft', 'steal', 'stole', 'stolen', 'pickpocket']):
        if any(word in description for word in ['vehicle', 'car', 'bike', 'motorcycle', 'auto']):
            return "Vehicle Theft"
        return "Theft"
    elif any(word in description for word in ['assault', 'attack', 'beat', 'hit', 'fight', 'violence']):
        return "Assault"
    elif any(word in description for word in ['robbery', 'robbed', 'mugging', 'snatching']):
        return "Robbery"
    elif any(word in description for word in ['vandalism', 'damage', 'graffiti', 'break', 'destroy']):
        return "Vandalism"
    elif any(word in description for word in ['harassment', 'stalking', 'following', 'eve teasing']):
        return "Harassment"
    elif any(word in description for word in ['drug', 'substance', 'alcohol', 'drunk']):
        return "Drug-related"
    elif any(word in description for word in ['fraud', 'scam', 'cheat', 'deceive']):
        return "Fraud"
    elif any(word in description for word in ['murder', 'kill', 'homicide', 'death']):
        return "Murder"
    elif any(word in description for word in ['kidnap', 'abduct', 'missing']):
        return "Kidnapping"
    else:
        return "Other"

def find_area_by_coordinates(lat, lng, map_data, kurla_areas):
    """Find which area a report belongs to based on coordinates"""
    if not lat or not lng:
        return "Kurla"
    
    # First try to match with map data markers
    if 'markers' in map_data:
        # Find the closest marker
        closest_marker = None
        min_distance = float('inf')
        
        for marker in map_data['markers']:
            if 'position' in marker and 'lat' in marker['position'] and 'lng' in marker['position']:
                marker_lat = marker['position']['lat']
                marker_lng = marker['position']['lng']
                
                # Calculate distance (simple Euclidean distance)
                distance = ((float(lat) - float(marker_lat)) ** 2 + (float(lng) - float(marker_lng)) ** 2) ** 0.5
                
                if distance < min_distance:
                    min_distance = distance
                    closest_marker = marker
        
        # If we found a close marker and it's within a reasonable distance
        if closest_marker and min_distance < 0.01:  # Approximately 1km
            return closest_marker['title']
    
    # If no match found, return a default area
    return "Kurla"

def map_location_to_area(location, kurla_areas):
    """Map a location name to a standardized area name"""
    if not location:
        return "Kurla"
    
    location = str(location).lower()
    
    # Direct mapping for common locations
    location_mapping = {
        'kurla west': 'Kurla West',
        'kurla east': 'Kurla East',
        'kurla station': 'Kurla Station',
        'bkc': 'BKC',
        'nehru nagar': 'Nehru Nagar',
        'tilak nagar': 'Tilak Nagar',
        'chunabhatti': 'Chunabhatti',
        'chembur': 'Chembur',
        'saki naka': 'Saki Naka',
        'asalpha': 'Asalpha',
        'vinoba bhave nagar': 'Vinoba Bhave Nagar',
        'lbs marg': 'LBS Marg',
        'kamani': 'Kamani',
        'premier colony': 'Premier Colony',
        'kalina': 'Kalina',
        'santacruz east': 'Santacruz East',
        'vidyavihar': 'Vidyavihar',
        'lokmanya tilak terminus': 'Lokmanya Tilak Terminus',
        'sion': 'Sion',
        'jarimari': 'Jarimari',
        'safed pool': 'Safed Pool'
    }
    
    # Check for direct match
    if location in location_mapping:
        return location_mapping[location]
    
    # Check for partial match
    for area_key, area_name in location_mapping.items():
        if area_key in location or location in area_key:
            return area_name
    
    # Check against standard area list
    for area in kurla_areas:
        if area.lower() in location or location in area.lower():
            return area
    
    # Default to Kurla if no match found
    return "Kurla"

def map_crime_type(crime_type):
    """Map crime types from news analysis to standardized types"""
    if not crime_type:
        return "Other"
    
    crime_type = str(crime_type).lower()
    
    # Direct mapping
    type_mapping = {
        'theft': 'Theft',
        'stealing': 'Theft',
        'larceny': 'Theft',
        'pickpocket': 'Theft',
        'shoplifting': 'Theft',
        
        'vehicle theft': 'Vehicle Theft',
        'car theft': 'Vehicle Theft',
        'bike theft': 'Vehicle Theft',
        'auto theft': 'Vehicle Theft',
        'motor vehicle theft': 'Vehicle Theft',
        
        'assault': 'Assault',
        'attack': 'Assault',
        'battery': 'Assault',
        'violence': 'Assault',
        'fight': 'Assault',
        
        'robbery': 'Robbery',
        'mugging': 'Robbery',
        'snatching': 'Robbery',
        'armed robbery': 'Robbery',
        
        'vandalism': 'Vandalism',
        'property damage': 'Vandalism',
        'graffiti': 'Vandalism',
        'destruction': 'Vandalism',
        
        'harassment': 'Harassment',
        'stalking': 'Harassment',
        'eve teasing': 'Harassment',
        'bullying': 'Harassment',
        
        'drug': 'Drug-related',
        'narcotics': 'Drug-related',
        'substance abuse': 'Drug-related',
        'alcohol': 'Drug-related',
        
        'fraud': 'Fraud',
        'scam': 'Fraud',
        'cheating': 'Fraud',
        'forgery': 'Fraud',
        
        'murder': 'Murder',
        'homicide': 'Murder',
        'killing': 'Murder',
        
        'kidnapping': 'Kidnapping',
        'abduction': 'Kidnapping',
        'missing person': 'Kidnapping'
    }
    
    # Check for direct match
    for key, value in type_mapping.items():
        if key in crime_type:
            return value
    
    # Default to Other if no match found
    return "Other"


