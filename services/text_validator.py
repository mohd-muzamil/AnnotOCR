# services/text_validator.py
# This script provides functionality to validate corrected text extracted from OCR processes.
# It includes a function, validate_corrected_text, which checks if the text adheres to expected formats,
# such as plain text or CSV format without trailing commas, ensuring data consistency.
# This service is crucial for maintaining the integrity of reviewed data by enforcing format rules before storage or further processing.

import re

def validate_corrected_text(text):
    """
    Validate the corrected text to ensure it matches a basic format.
    - Lines can be plain text or CSV format (e.g., "facebook,1h").
    - Lines with commas must not end with a trailing comma (e.g., "facebook,1h," is invalid).
    
    Args:
        text (str): The corrected text to validate.
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
        - is_valid: True if the text matches the expected format, False otherwise.
        - error_message: Empty string if valid, otherwise a description of the format error.
    """
    if not text:
        return False, "Corrected text cannot be empty."

    # Allow the default rejection message to pass validation
    if text.strip() == "Rejected: Text is illegible or not relevant.":
        return True, ""
    
    lines = text.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]  # Remove empty lines
    
    if not lines:
        return False, "Corrected text cannot be empty after removing empty lines."
    
    for i, line in enumerate(lines, start=1):
        if ',' in line:
            # if line.endswith(','):
            #     return False, f"Line {i} has a trailing comma which is not allowed. Found: '{line}'"
            # Basic check for CSV format (at least two parts after splitting by comma)
            parts = line.split(',')
            if len(parts) < 2:
                return False, f"Line {i} does not have a valid CSV format (expected at least two parts). Found: '{line}'"
    
    return True, ""
