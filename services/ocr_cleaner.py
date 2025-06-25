# services/ocr_cleaner.py
# This script provides functionality to clean and process OCR (Optical Character Recognition) extracted text.
# It includes a function to load app suggestions from a JSON file for matching against OCR text.
# The primary function, clean_ocr_text, filters raw OCR text to extract relevant app names and screen time information,
# removing irrelevant or junk text. This service is essential for improving the quality of OCR data before further processing or review.

import json
import os

# Function to load app suggestions from JSON file
def load_app_suggestions(file_path='static/data/app_suggestions.json'):
    """
    Load app suggestions from a JSON file.
    
    Args:
        file_path (str): Path to the JSON file containing app suggestions.
        
    Returns:
        list: List of app names.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data = json.load(file)
                return data.get('apps', [])
        else:
            print(f"File {file_path} not found. Using default list.")
    except Exception as e:
        print(f"Error loading app suggestions: {e}")
    
    # Fallback to a default list if file loading fails
    return [
        "Facebook",
        "Instagram",
        "Twitter",
        "YouTube",
        "TikTok",
        "WhatsApp",
        "Snapchat",
        "Netflix",
        "Spotify",
        "Google Chrome"
    ]

# Load suggestions at module level
APP_SUGGESTIONS = load_app_suggestions()

def clean_ocr_text(ocr_text, app_suggestions=APP_SUGGESTIONS):
    """
    Clean the raw OCR text by removing empty lines and lines with only special characters,
    and attempt to correct app names based on provided suggestions while preserving line breaks.
    
    Args:
        ocr_text (str): The raw OCR text extracted from screenshots.
        app_suggestions (list): List of known app names for matching. Defaults to APP_SUGGESTIONS.
        
    Returns:
        str: Cleaned text with irrelevant lines removed and app names corrected where possible.
    """
    if not ocr_text:
        return ""
    
    cleaned_lines = []
    lines = ocr_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:  # Remove empty lines
            continue
        if all(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/~`'\" " for c in line):  # Remove lines with only special characters
            continue
            
        # Attempt to correct app names in the line
        corrected_line = line
        for app in app_suggestions:
            if app.lower() in line.lower():
                # Replace the matched portion with the correct app name capitalization
                start_idx = line.lower().find(app.lower())
                end_idx = start_idx + len(app)
                corrected_line = line[:start_idx] + app + line[end_idx:]
                break
                
        cleaned_lines.append(corrected_line)
    
    return '\n'.join(cleaned_lines) if cleaned_lines else ocr_text
