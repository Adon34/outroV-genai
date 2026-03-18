# backend/app/utils/validators.py
import re
from typing import Optional, List
from datetime import datetime, date

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple:
    """
    Validate password strength
    Returns (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def validate_age(age: Optional[int]) -> bool:
    """Validate age"""
    if age is None:
        return True
    return 13 <= age <= 120

def validate_weight(weight: Optional[float]) -> bool:
    """Validate weight in kg"""
    if weight is None:
        return True
    return 20 <= weight <= 300

def validate_height(height: Optional[float]) -> bool:
    """Validate height in cm"""
    if height is None:
        return True
    return 100 <= height <= 250

def validate_activity_level(level: Optional[str]) -> bool:
    """Validate activity level"""
    valid_levels = ['sedentary', 'light', 'moderate', 'active', 'very_active']
    if level is None:
        return True
    return level in valid_levels

def validate_diet_type(diet_type: Optional[str]) -> bool:
    """Validate diet type"""
    valid_types = ['standard', 'vegetarian', 'vegan', 'keto', 'paleo', 'mediterranean']
    if diet_type is None:
        return True
    return diet_type in valid_types

def validate_meal_type(meal_type: str) -> bool:
    """Validate meal type"""
    valid_types = ['breakfast', 'lunch', 'dinner', 'snack']
    return meal_type in valid_types

def validate_date(date_str: str) -> bool:
    """Validate date string (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra spaces
    text = ' '.join(text.split())
    return text.strip()

def validate_allergies(allergies: List[str]) -> List[str]:
    """Validate and normalize allergies"""
    valid_allergies = []
    for allergy in allergies:
        allergy = allergy.strip().lower()
        if allergy and len(allergy) <= 50:
            valid_allergies.append(allergy)
    return valid_allergies

def validate_health_conditions(conditions: List[str]) -> List[str]:
    """Validate health conditions"""
    valid_conditions = []
    for condition in conditions:
        condition = condition.strip().lower()
        if condition and len(condition) <= 100:
            valid_conditions.append(condition)
    return valid_conditions