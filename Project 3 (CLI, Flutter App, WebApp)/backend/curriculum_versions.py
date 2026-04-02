"""
NSU Curriculum Versions
=======================
Different graduation years have different course requirements.
NSU changed their curriculum around 2018-2020, so students enrolled
in different years have different requirements.

This module provides:
- CURRICULUM_VERSIONS: Department-specific curriculum versions
- get_curriculum_version(): Get appropriate curriculum for a student
- detect_enrollment_year(): Extract enrollment year from student ID
"""

from typing import Optional, Dict, Any


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CURRICULUM VERSIONS BY DEPARTMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRICULUM_VERSIONS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "CSE": {
        # Version 1: Before 2018 (older curriculum)
        "v1": {
            "name": "CSE Curriculum 2013-2017",
            "valid_years": range(2000, 2018),
            "total_credits": 136,
            "requirements": {
                "foundation": 15,          # Programming fundamentals
                "core": 60,                # CSE core courses
                "electives": 15,           # 5 electives × 3 credits
                "university_core": 46,     # GED + Math + Science
            },
            "min_electives": 5,
            "notes": [
                "Requires CEE110 (Engineering Drawing)",
                "EEE452 (Engineering Economics) is mandatory",
                "MAT116 (Pre-Calculus) is required",
            ]
        },
        # Version 2: 2018-2021 (transitional curriculum)
        "v2": {
            "name": "CSE Curriculum 2018-2021",
            "valid_years": range(2018, 2022),
            "total_credits": 133,
            "requirements": {
                "foundation": 12,
                "core": 54,
                "electives": 15,
                "university_core": 40,
                "capstone": 4,
                "open_electives": 8,
            },
            "min_electives": 5,
            "notes": [
                "MAT116 (Pre-Calculus) made optional",
                "Some lab courses have 0 credits",
                "Reduced GED requirements",
            ]
        },
        # Version 3: 2022+ (current curriculum)
        "v3": {
            "name": "CSE Curriculum 2022+",
            "valid_years": range(2022, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 11,
                "core": 42,
                "electives": 9,            # 3 electives × 3 credits
                "university_core": 34,
                "seps_core": 30,           # Science, Engineering, Problem Solving
                "capstone": 4,
            },
            "min_electives": 3,
            "notes": [
                "Current curriculum structure",
                "Streamlined credit requirements",
                "Only 3 electives required (down from 5)",
            ]
        }
    },
    
    "EEE": {
        # Version 1: Before 2018
        "v1": {
            "name": "EEE Curriculum 2013-2017",
            "valid_years": range(2000, 2018),
            "total_credits": 136,
            "requirements": {
                "foundation": 15,
                "core": 60,
                "electives": 15,
                "university_core": 46,
            },
            "min_electives": 5,
            "notes": [
                "Similar structure to CSE v1",
                "Heavy emphasis on lab courses",
            ]
        },
        # Version 2: 2018-2021
        "v2": {
            "name": "EEE Curriculum 2018-2021",
            "valid_years": range(2018, 2022),
            "total_credits": 133,
            "requirements": {
                "foundation": 12,
                "core": 54,
                "electives": 15,
                "university_core": 40,
                "capstone": 4,
            },
            "min_electives": 5,
            "notes": [
                "Transitional curriculum",
                "Reduced total credits",
            ]
        },
        # Version 3: 2022+
        "v3": {
            "name": "EEE Curriculum 2022+",
            "valid_years": range(2022, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 11,
                "core": 42,
                "electives": 9,
                "university_core": 34,
                "seps_core": 30,
                "capstone": 4,
            },
            "min_electives": 3,
            "notes": [
                "Current curriculum",
                "Aligned with CSE v3 structure",
            ]
        }
    },
    
    "BBA": {
        # Version 1: Before 2019
        "v1": {
            "name": "BBA Curriculum 2013-2018",
            "valid_years": range(2000, 2019),
            "total_credits": 132,
            "requirements": {
                "foundation": 42,          # General + business foundation
                "core": 30,                # BBA core courses
                "major": 24,               # Major courses
                "minor": 12,               # Minor concentration
                "electives": 9,            # Free electives
                "university_core": 15,     # GED courses
            },
            "min_electives": 3,
            "notes": [
                "Double major option available",
                "Minor required",
            ]
        },
        # Version 2: 2019+
        "v2": {
            "name": "BBA Curriculum 2019+",
            "valid_years": range(2019, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 39,
                "core": 30,
                "major": 24,
                "minor": 12,
                "electives": 6,
                "university_core": 19,
            },
            "min_electives": 2,
            "notes": [
                "Current BBA curriculum",
                "Streamlined elective requirements",
            ]
        }
    },
    
    # Additional departments with simplified curriculum versions
    "ECE": {
        "v1": {
            "name": "ECE Curriculum 2022+",
            "valid_years": range(2000, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 11,
                "core": 45,
                "electives": 9,
                "university_core": 34,
                "seps_core": 27,
                "capstone": 4,
            },
            "min_electives": 3,
            "notes": ["Electronic & Computer Engineering curriculum"]
        }
    },
    
    "ETE": {
        "v1": {
            "name": "ETE Curriculum 2022+",
            "valid_years": range(2000, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 11,
                "core": 45,
                "electives": 9,
                "university_core": 34,
                "seps_core": 27,
                "capstone": 4,
            },
            "min_electives": 3,
            "notes": ["Electronics & Telecommunications Engineering curriculum"]
        }
    },
    
    "ARC": {
        "v1": {
            "name": "Architecture Curriculum",
            "valid_years": range(2000, 2035),
            "total_credits": 180,  # 5-year program
            "requirements": {
                "foundation": 24,
                "design_studios": 60,
                "theory_history": 24,
                "technology": 30,
                "electives": 18,
                "university_core": 24,
            },
            "min_electives": 6,
            "notes": ["5-year Bachelor of Architecture program"]
        }
    },
    
    "ENV": {
        "v1": {
            "name": "Environmental Science Curriculum",
            "valid_years": range(2000, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 15,
                "core": 45,
                "electives": 12,
                "university_core": 34,
                "field_work": 6,
                "capstone": 4,
            },
            "min_electives": 4,
            "notes": ["Environmental Science & Management curriculum"]
        }
    },
    
    "ECO": {
        "v1": {
            "name": "Economics Curriculum",
            "valid_years": range(2000, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 18,
                "core": 45,
                "electives": 15,
                "university_core": 34,
                "quantitative": 18,
            },
            "min_electives": 5,
            "notes": ["Bachelor of Science in Economics curriculum"]
        }
    },
    
    "PHR": {
        "v1": {
            "name": "Pharmacy Curriculum",
            "valid_years": range(2000, 2035),
            "total_credits": 160,  # 4-year + internship
            "requirements": {
                "foundation": 24,
                "core": 72,
                "electives": 12,
                "university_core": 24,
                "clinical_practice": 28,
            },
            "min_electives": 4,
            "notes": ["Bachelor of Pharmacy curriculum"]
        }
    },
    
    "MIC": {
        "v1": {
            "name": "Microbiology Curriculum",
            "valid_years": range(2000, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 18,
                "core": 48,
                "electives": 12,
                "university_core": 34,
                "lab_work": 18,
            },
            "min_electives": 4,
            "notes": ["Bachelor of Science in Microbiology curriculum"]
        }
    },
    
    "BCH": {
        "v1": {
            "name": "Biochemistry & Biotechnology Curriculum",
            "valid_years": range(2000, 2035),
            "total_credits": 130,
            "requirements": {
                "foundation": 18,
                "core": 48,
                "electives": 12,
                "university_core": 34,
                "lab_work": 18,
            },
            "min_electives": 4,
            "notes": ["Bachelor of Science in Biochemistry and Biotechnology curriculum"]
        }
    }
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENROLLMENT YEAR DETECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_enrollment_year(student_id: str) -> Optional[int]:
    """
    Extract enrollment year from NSU student ID.
    
    NSU Student ID Format: YYXXXXX S DD
    - YY: Enrollment year (last 2 digits)
    - XXXXX: Serial number
    - S: Space
    - DD: Department code
    
    Examples:
        "0920402 S 43" → 2009 (enrolled 2009, CSE)
        "1820102 S 42" → 2018 (enrolled 2018, CSE)
        "2310534 S 30" → 2023 (enrolled 2023, BBA)
    
    Args:
        student_id: Student ID string (may contain spaces/special chars)
    
    Returns:
        Enrollment year (e.g., 2009, 2018, 2023) or None if detection fails
    """
    if not student_id:
        return None
    
    # Clean the ID - extract only digits from the first part
    clean_id = ''.join(c for c in str(student_id) if c.isdigit())
    
    if len(clean_id) >= 2:
        year_digits = int(clean_id[:2])
        
        # Handle year rollover (00-35 → 2000-2035, 36-99 → 1936-1999)
        # NSU was founded in 1992, so students before 2000 would have 9x IDs
        if year_digits <= 35:
            return 2000 + year_digits
        else:
            return 1900 + year_digits  # Historical students (rare)
    
    return None


def get_enrollment_year_display(year: Optional[int]) -> str:
    """Format enrollment year for display."""
    if year is None:
        return "Unknown"
    return f"{year} (Batch of {year + 4})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CURRICULUM VERSION LOOKUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_curriculum_version(
    department: str, 
    enrollment_year: Optional[int] = None,
    student_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get the appropriate curriculum version for a student.
    
    Args:
        department: Department code (CSE, EEE, BBA)
        enrollment_year: Student's enrollment year (optional)
        student_id: Student ID to extract year from (used if enrollment_year not given)
    
    Returns:
        Dict with curriculum version info:
        {
            "version": "v2",
            "name": "CSE Curriculum 2018-2021",
            "total_credits": 133,
            "requirements": {...},
            "enrollment_year": 2018,
            "year_range": "2018-2021",
            ...
        }
        
        Returns None if department not found or year doesn't match any version.
    """
    # Normalize department
    dept = department.upper() if department else ""
    
    # Get versions for this department
    dept_versions = CURRICULUM_VERSIONS.get(dept, {})
    if not dept_versions:
        return None
    
    # Detect enrollment year from student ID if not provided
    if enrollment_year is None and student_id:
        enrollment_year = detect_enrollment_year(student_id)
    
    # If still no year, use the latest curriculum
    if enrollment_year is None:
        # Get the latest version (highest valid_years)
        latest_version = None
        latest_year = 0
        for version_id, version in dept_versions.items():
            if version["valid_years"].stop > latest_year:
                latest_year = version["valid_years"].stop
                latest_version = (version_id, version)
        
        if latest_version:
            version_id, version = latest_version
            return _build_version_response(version_id, version, enrollment_year)
        return None
    
    # Find matching curriculum version for the enrollment year
    for version_id, version in dept_versions.items():
        if enrollment_year in version["valid_years"]:
            return _build_version_response(version_id, version, enrollment_year)
    
    # Year doesn't match any version - use closest one
    # Check if year is before the earliest version
    earliest_version = min(dept_versions.items(), key=lambda x: x[1]["valid_years"].start)
    if enrollment_year < earliest_version[1]["valid_years"].start:
        return _build_version_response(earliest_version[0], earliest_version[1], enrollment_year)
    
    # Year is after the latest version - use latest
    latest_version = max(dept_versions.items(), key=lambda x: x[1]["valid_years"].stop)
    return _build_version_response(latest_version[0], latest_version[1], enrollment_year)


def _build_version_response(
    version_id: str, 
    version: Dict[str, Any], 
    enrollment_year: Optional[int]
) -> Dict[str, Any]:
    """Build the curriculum version response dict."""
    year_range = version["valid_years"]
    
    return {
        "version": version_id,
        "name": version["name"],
        "total_credits": version["total_credits"],
        "requirements": version["requirements"],
        "min_electives": version.get("min_electives", 3),
        "notes": version.get("notes", []),
        "enrollment_year": enrollment_year,
        "year_range": f"{year_range.start}-{year_range.stop - 1}",
        "is_current": version_id == "v3" or version_id == "v2" and "2019" in version["name"]
    }


def get_curriculum_version_display(curriculum: Optional[Dict[str, Any]]) -> str:
    """Format curriculum version info for display."""
    if not curriculum:
        return "Unknown Curriculum"
    
    return f"{curriculum['name']} ({curriculum['year_range']})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CREDIT REQUIREMENTS COMPARISON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compare_credits_to_curriculum(
    earned_credits: int,
    curriculum: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare student's earned credits against curriculum requirements.
    
    Returns:
        Dict with comparison info:
        {
            "required": 130,
            "earned": 115,
            "remaining": 15,
            "progress_pct": 88.5,
            "on_track": True,
            "note": "15 credits remaining"
        }
    """
    required = curriculum.get("total_credits", 130)
    remaining = max(0, required - earned_credits)
    progress = round(min(earned_credits / required * 100, 100), 1) if required > 0 else 0
    
    return {
        "required": required,
        "earned": earned_credits,
        "remaining": remaining,
        "progress_pct": progress,
        "on_track": earned_credits >= required,
        "note": f"{remaining} credits remaining" if remaining > 0 else "Credit requirement met!"
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UTILITY: LIST ALL VERSIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def list_all_curriculum_versions() -> Dict[str, list]:
    """
    Get a summary of all curriculum versions for reference.
    
    Returns:
        Dict mapping department to list of version summaries
    """
    result = {}
    for dept, versions in CURRICULUM_VERSIONS.items():
        result[dept] = []
        for version_id, version in versions.items():
            result[dept].append({
                "version": version_id,
                "name": version["name"],
                "years": f"{version['valid_years'].start}-{version['valid_years'].stop - 1}",
                "total_credits": version["total_credits"]
            })
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MANUAL OVERRIDE SUPPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_curriculum_by_version_id(department: str, version_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific curriculum version (for manual override).
    
    Args:
        department: Department code (CSE, EEE, BBA)
        version_id: Version identifier (v1, v2, v3)
    
    Returns:
        Curriculum version dict or None
    """
    dept = department.upper() if department else ""
    dept_versions = CURRICULUM_VERSIONS.get(dept, {})
    
    if version_id in dept_versions:
        return _build_version_response(version_id, dept_versions[version_id], None)
    
    return None
