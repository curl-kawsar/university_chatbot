import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(BASE_DIR, 'data', 'json')

# Data files configuration
DATA_FILES = {
    "academic_deadlines": os.path.join(JSON_DIR, "academic_deadlines.json"),
    "course_information": os.path.join(JSON_DIR, "course_information.json"),
    "student_service_support": os.path.join(JSON_DIR, "student_support.json"),
    "library_books_list": os.path.join(JSON_DIR, "library_books.json"),
    "transport_service": os.path.join(JSON_DIR, "transport_service.json"),
    "paper_recheck": os.path.join(JSON_DIR, "paper_recheck.json")
} 