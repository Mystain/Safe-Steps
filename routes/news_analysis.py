from flask import Blueprint, render_template, jsonify, request, current_app
import os
import json
import pandas as pd
import numpy as np
import logging
import datetime
import requests
from bs4 import BeautifulSoup
import re
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

news_analysis_bp = Blueprint('news_analysis', __name__)

@news_analysis_bp.route('/api/run-news-analysis', methods=['POST'])
def run_news_analysis():
    """API endpoint to trigger news analysis in the background"""
    try:
        # Start the analysis in a background thread
        thread = threading.Thread(target=perform_news_analysis)
        thread.daemon = True
        thread.start()
        
        return jsonify({"success": True, "message": "Analysis started in background"})
    except Exception as e:
        logger.error(f"Error starting news analysis: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

def perform_news_analysis():
    """Perform the news analysis in the background"""
    try:
        logger.info("Starting news analysis...")
        
        # Create directories if they don't exist
        data_dir = os.path.join('static', 'data', 'news_analysis')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # List of news sources to scrape
        news_sources = [
            {
                "name": "Mumbai Mirror",
                "url": "https://mumbaimirror.indiatimes.com/mumbai/crime",
                "article_selector": ".article-listing",
                "title_selector": "h2",
                "date_selector": ".date-format"
            },
            {
                "name": "Times of India",
                "url": "https://timesofindia.indiatimes.com/city/mumbai/crime",
                "article_selector": ".article",
                "title_selector": "h3",
                "date_selector": ".date"
            },
            # Add more news sources as needed
        ]
        
        # List of Kurla area keywords to look for
        kurla_areas = [
            "kurla west", "kurla east", "kurla station", "bkc", "nehru nagar", 
            "tilak nagar", "chunabhatti", "chembur", "saki naka", "asalpha", 
            "vinoba bhave nagar", "lbs marg", "kamani", "premier colony", 
            "kalina", "santacruz east", "vidyavihar", "lokmanya tilak terminus", 
            "sion", "jarimari", "safed pool"
        ]
        
        # List of crime keywords to look for
        crime_keywords = [
            "theft", "robbery", "assault", "murder", "rape", "kidnapping", 
            "burglary", "fraud", "violence", "attack", "crime", "criminal"
        ]
        
        # Initialize results
        crime_locations = {area: 0 for area in kurla_areas}
        crime_types = {"theft": 0, "robbery": 0, "assault": 0, "murder": 0, "other": 0}
        
        # In a real implementation, we would scrape news websites
        # For this demo, we'll simulate the results
        
        # Simulate news analysis with random data
        # In a real implementation, this would be replaced with actual web scraping
        for area in kurla_areas:
            # Generate random count between 0 and 5
            crime_locations[area] = np.random.randint(0, 6)
        
        for crime_type in crime_types:
            # Generate random count between 5 and 20
            crime_types[crime_type] = np.random.randint(5, 21)
        
        # Create a timestamp for when the analysis was performed
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create the analysis results
        analysis_results = {
            "timestamp": timestamp,
            "crime_locations": crime_locations,
            "crime_types": crime_types,
            "total_articles_analyzed": np.random.randint(50, 100),
            "crime_related_articles": np.random.randint(20, 50)
        }
        
        # Save the results to a JSON file
        json_path = os.path.join(data_dir, 'crime_analysis.json')
        with open(json_path, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        
        # Update the map data based on the new analysis
        update_map_data(crime_locations)
        
        logger.info("News analysis completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in news analysis: {str(e)}")
        return False

def update_map_data(crime_locations):
    """Update the map data based on news analysis results"""
    try:
        # Path to the map data file
        map_data_path = os.path.join('static', 'data', 'map', 'crime_map_data.json')
        
        # Check if the file exists
        if os.path.exists(map_data_path):
            # Load existing map data
            with open(map_data_path, 'r') as f:
                map_data = json.load(f)
            
            # Update the markers with new crime data
            for marker in map_data.get('markers', []):
                location_name = marker['title'].lower()
                
                # Find matching location in crime_locations
                for area in crime_locations:
                    if area in location_name or location_name in area:
                        # Update the marker with new data
                        news_count = crime_locations[area]
                        
                        # Blend with existing data (70% existing, 30% news)
                        current_count = marker.get('incidents', 0)
                        blended_count = (0.7 * current_count) + (0.3 * news_count)
                        
                        marker['incidents'] = round(blended_count, 1)
                        
                        # Recalculate intensity (1-10 scale)
                        max_count = max([m.get('incidents', 0) for m in map_data.get('markers', [])])
                        intensity = min(10, max(1, int(blended_count * 10 / max_count if max_count else 1)))
                        marker['intensity'] = intensity
                        
                        break
            
            # Update timestamp
            map_data['last_updated'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save updated map data
            with open(map_data_path, 'w') as f:
                json.dump(map_data, f, indent=2)
            
            logger.info(f"Updated map data with news analysis results")
        else:
            logger.warning(f"Map data file not found at {map_data_path}")
    except Exception as e:
        logger.error(f"Error updating map data: {str(e)}")

@news_analysis_bp.route('/api/safety-data')
def get_safety_data():
    """API endpoint to get safety data in GeoJSON format for the map"""
    try:
        # First, check if we have pre-generated map data
        map_data_path = os.path.join('static', 'data', 'map', 'crime_map_data.json')
        
        if os.path.exists(map_data_path):
            # Use the pre-generated map data
            with open(map_data_path, 'r') as f:
                map_data = json.load(f)
            
            # Convert to GeoJSON format
            features = []
            for marker in map_data.get('markers', []):
                # Determine safety level based on intensity
                intensity = marker.get('intensity', 0)
                safety_level = "green"  # Default: safe
                if intensity > 7:
                    safety_level = "red"  # High risk
                elif intensity > 4:
                    safety_level = "yellow"  # Moderate risk
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [marker['position']['lng'], marker['position']['lat']]
                    },
                    "properties": {
                        "name": marker['title'],
                        "crime_count": marker['incidents'],
                        "safety_level": safety_level
                    }
                }
                features.append(feature)
            
            # Create GeoJSON object
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            
            # Log the number of features for debugging
            logger.info(f"Returning {len(features)} features from pre-generated map data")
            
            return jsonify(geojson)
        
        # If no pre-generated data, return an empty GeoJSON
        return jsonify({
            "type": "FeatureCollection",
            "features": []
        })
    except Exception as e:
        logger.error(f"Error generating safety data: {str(e)}")
        return jsonify({"error": str(e)}), 500
