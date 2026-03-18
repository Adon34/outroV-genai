# backend/app/utils/helpers.py
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import uuid

def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def hash_string(text: str) -> str:
    """Create SHA-256 hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()

def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return dt.strftime(format)

def parse_datetime(date_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """Parse datetime from string"""
    try:
        return datetime.strptime(date_str, format)
    except ValueError:
        return None

def calculate_age(birth_date: datetime) -> int:
    """Calculate age from birth date"""
    today = datetime.now()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate BMI"""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)

def get_bmi_category(bmi: float) -> str:
    """Get BMI category"""
    if bmi < 18.5:
        return "underweight"
    elif bmi < 25:
        return "normal"
    elif bmi < 30:
        return "overweight"
    else:
        return "obese"

def calculate_tdee(
    weight: float,
    height: float,
    age: int,
    gender: str,
    activity_level: str
) -> int:
    """Calculate Total Daily Energy Expenditure"""
    # BMR calculation (Mifflin-St Jeor Equation)
    if gender.lower() == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    # Activity multipliers
    multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    
    tdee = bmr * multipliers.get(activity_level, 1.2)
    return round(tdee)

def chunk_list(lst: list, chunk_size: int):
    """Split list into chunks"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def safe_json_loads(data: str) -> Optional[Dict]:
    """Safely load JSON string"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None

def generate_conversation_title(message: str) -> str:
    """Generate title for conversation from first message"""
    words = message.split()[:5]
    title = ' '.join(words)
    if len(message) > 50:
        title += '...'
    return title

def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def is_valid_uuid(val: str) -> bool:
    """Check if string is valid UUID"""
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text"""
    return [float(num) for num in re.findall(r'-?\d+\.?\d*', text)]