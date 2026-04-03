"""
nsu_courses.py - NSU Official Course Data
==========================================
Comprehensive course catalog for North South University
Data sourced from official NSU department websites.

Schools & Departments:
- School of Engineering & Applied Science (SEAS)
  - CSE (Computer Science & Engineering) - Department Code: 42
  - EEE (Electrical & Electronic Engineering) - Department Code: 43
  - ECE (Electronic & Computer Engineering) - Department Code: 44
  - ETE (Electronics & Telecommunications Engineering) - Department Code: 45
  - ARC (Architecture) - Department Code: 46
  - ENV (Environmental Science & Management) - Department Code: 47

- School of Business (SBE)
  - BBA (Bachelor of Business Administration) - Department Code: 30

- School of Arts and Social Science (SASS)
  - ECO (Economics) - Department Code: 50
  - ENG (English) - Department Code: 51

- School of Life Science (SLS)
  - PHR (Pharmacy) - Department Code: 60
  - PBH (Public Health) - Department Code: 61
  - MIC (Microbiology) - Department Code: 62
  - BCH (Biochemistry & Biotechnology) - Department Code: 63

Last Updated: April 2026
Reference: https://www.northsouth.edu/academic/
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UNIVERSITY CORE COURSES (Common across Engineering programs)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UNIVERSITY_CORE = {
    "languages": [
        ("ENG102", "Introduction to Composition", 3),
        ("ENG103", "Intermediate Composition", 3),
        ("ENG111", "Public Speaking", 3),
        ("BEN205", "Bangla Language", 3),
    ],
    "humanities": [
        ("PHI104", "Introduction to Ethics", 3),
        ("HIS102", "Introduction to World Civilization", 3),
        ("HIS103", "Emergence of Bangladesh", 3),
    ],
    "social_sciences": [
        ("ECO101", "Introduction to Microeconomics", 3),
        ("ECO104", "Introduction to Macroeconomics", 3),
        ("POL101", "Introduction to Political Science", 3),
        ("POL104", "Introduction to Governance", 3),
        ("SOC101", "Introduction to Sociology", 3),
        ("ANT101", "Introduction to Anthropology", 3),
        ("ENV203", "Environmental Science", 3),
        ("GEO205", "Introduction to Bangladesh Geography", 3),
    ],
    "natural_sciences": [
        ("BIO103", "Biology", 4),
        ("CHE101", "Chemistry I", 4),
        ("CHE101L", "Chemistry I Lab", 0),
        ("PHY107", "Physics I", 3),
        ("PHY107L", "Physics I Lab", 1),
        ("PHY108", "Physics II", 3),
        ("PHY108L", "Physics II Lab", 1),
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCHOOL OF ENGINEERING & PHYSICAL SCIENCES (SEPS) CORE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEPS_CORE = {
    "mathematics": [
        ("MAT116", "Pre-Calculus", 0),
        ("MAT120", "Calculus I", 3),
        ("MAT125", "Linear Algebra", 3),
        ("MAT130", "Calculus II", 3),
        ("MAT250", "Calculus III", 3),
        ("MAT350", "Engineering Mathematics", 3),
        ("MAT361", "Probability and Statistics", 3),
    ],
    "physics": [
        ("PHY107", "Physics I", 3),
        ("PHY107L", "Physics I Lab", 1),
        ("PHY108", "Physics II", 3),
        ("PHY108L", "Physics II Lab", 1),
    ],
    "chemistry": [
        ("CHE101", "Chemistry I", 3),
        ("CHE101L", "Chemistry I Lab", 1),
    ],
    "engineering_fundamentals": [
        ("CEE110", "Engineering Drawing", 1),
        ("EEE154", "Engineering Drawing", 1),
        ("EEE452", "Engineering Economics", 3),
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CSE - COMPUTER SCIENCE & ENGINEERING (Department Code: 42)
#  Total Credits Required: 130
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CSE_COURSES = {
    "department_code": 42,
    "department_name": "Computer Science & Engineering",
    "degree": "Bachelor of Science in Computer Science and Engineering (BSCSE)",
    "total_credits": 130,
    
    "foundation": [
        # Programming Foundation
        ("CSE115", "Programming Language I", 3),
        ("CSE115L", "Programming Language I Lab", 1),
        ("CSE173", "Discrete Mathematics", 3),
        ("CSE215", "Programming Language II", 3),
        ("CSE215L", "Programming Language II Lab", 1),
    ],
    
    "core": [
        # Data Structures & Algorithms
        ("CSE225", "Data Structures and Algorithm", 3),
        ("CSE225L", "Data Structures and Algorithm Lab", 0),
        ("CSE373", "Design and Analysis of Algorithms", 3),
        
        # Digital Systems & Hardware
        ("CSE231", "Digital Logic Design", 3),
        ("CSE231L", "Digital Logic Design Lab", 0),
        ("CSE331", "Microprocessor Interfacing & Embedded Systems", 3),
        ("CSE331L", "Microprocessor Interfacing & Embedded Systems Lab", 0),
        ("CSE332", "Computer Organization and Architecture", 3),
        
        # Systems & Software
        ("CSE311", "Database Systems", 3),
        ("CSE311L", "Database Systems Lab", 0),
        ("CSE323", "Operating Systems Design", 3),
        ("CSE323L", "Operating Systems Design Lab", 0),
        ("CSE327", "Software Engineering", 3),
        ("CSE425", "Concepts of Programming Language", 3),
        
        # Theory & Computation
        ("CSE226", "Discrete Structures", 3),  # Additional discrete math
        ("CSE340", "Computer Networking", 3),  # Networking fundamentals
        
        # Electrical/Electronics Foundation (from EEE)
        ("EEE141", "Electrical Circuits I", 3),
        ("EEE141L", "Electrical Circuits I Lab", 1),
        ("EEE111", "Analog Electronics I", 3),
        ("EEE111L", "Analog Electronics I Lab", 1),
    ],
    
    "capstone": [
        ("CSE299", "Junior Design Project I", 1),
        ("CSE499A", "Senior Design Project I", 1.5),
        ("CSE499B", "Senior Design Project II", 1.5),
    ],
    
    "internship": [
        ("CSE498", "Intern/Co-op (8-12 weeks)", 0),  # Non-credit
    ],
    
    "electives": {
        "algorithms_computation": [
            ("CSE401", "Advanced Programming Techniques", 3),
            ("CSE417", "Numerical Methods", 3),
            ("CSE418", "Computer Graphics", 3),
            ("CSE426", "Compiler Constructions", 3),
            ("CSE473", "Theory of Computation", 3),
            ("CSE491", "Special Topics in Algorithms", 3),
        ],
        "software_engineering": [
            ("CSE411", "Advanced Database Systems", 3),
            ("CSE427", "Software Quality Assurance & Testing", 3),
            ("CSE428", "Software Process Management", 3),
            ("CSE429", "Software System Architecture", 3),
            ("CSE492", "Special Topics in Software Engineering", 3),
        ],
        "networks": [
            ("CSE422", "Modelling and Simulation", 3),
            ("CSE438", "Data Communication & Network", 3),
            ("CSE482", "Internet and Web Technology", 3),
            ("CSE485", "Digital Signal Processing", 3),
            ("CSE486", "Mobile and Wireless Application Development", 3),
            ("CSE493", "Special Topics in Networks", 3),
        ],
        "computer_architecture_vlsi": [
            ("CSE433", "Advanced Architecture", 3),
            ("CSE435", "Introduction to VLSI Design", 3),
            ("CSE413", "Verilog HDL: Modelling, Simulation, and Synthesis", 3),
            ("CSE414", "Advanced Chip Design Methodology and Optimization using HDL", 3),
            ("CSE415", "VLSI Chip Testing", 3),
            ("CSE494", "Special Topics in VLSI", 3),
        ],
        "artificial_intelligence": [
            ("CSE440", "Artificial Intelligence", 3),
            ("CSE445", "Machine Learning", 3),
            ("CSE465", "Pattern Recognition and Neural Network", 3),
            ("CSE467", "Digital Image Processing", 3),
            ("CSE468", "Computer Vision", 3),
            ("CSE470", "Theory of Fuzzy Systems", 3),
            ("CSE419", "Data Mining", 3),
            ("CSE495", "Special Topics in AI", 3),
        ],
        "bioinformatics": [
            ("CSE446", "Introduction to Bioinformatics", 3),
            ("CSE447", "Molecular Biology", 3),
            ("CSE448", "Genome Sequence & Analysis", 3),
            ("CSE449", "Structural Bioinformatics", 3),
            ("CSE442", "Micro Array Bioinformatics", 3),
            ("CSE496", "Special Topics in Bioinformatics", 3),
        ],
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EEE - ELECTRICAL & ELECTRONIC ENGINEERING (Department Code: 43)
#  Total Credits Required: 130
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EEE_COURSES = {
    "department_code": 43,
    "department_name": "Electrical & Electronic Engineering",
    "degree": "Bachelor of Science in Electrical and Electronic Engineering (BSEEE)",
    "total_credits": 130,
    
    "foundation": [
        ("CSE115", "Programming Language I", 3),
        ("CSE115L", "Programming Language I Lab", 1),
        ("CSE173", "Discrete Mathematics", 3),  # Also required for EEE
    ],
    
    "core": [
        # Circuits
        ("EEE141", "Electrical Circuits I", 3),
        ("EEE141L", "Electrical Circuits I Lab", 1),
        ("EEE241", "Electrical Circuits II", 3),
        ("EEE241L", "Electrical Circuits II Lab", 1),
        
        # Electronics
        ("EEE111", "Analog Electronics I", 3),
        ("EEE111L", "Analog Electronics I Lab", 1),
        ("EEE311", "Analog Electronics II", 3),
        ("EEE311L", "Analog Electronics II Lab", 1),
        ("EEE312", "Power Electronics", 3),
        ("EEE312L", "Power Electronics Lab", 0),
        
        # Digital Systems
        ("EEE211", "Digital Logic Design", 3),
        ("EEE211L", "Digital Logic Design Lab", 0),
        ("EEE212", "Digital Systems Design", 3),  # Advanced digital
        
        # Signals & Systems
        ("EEE221", "Signals and Systems", 3),
        ("EEE321", "Introduction to Communications Systems", 3),
        ("EEE321L", "Introduction to Communications Systems Lab", 0),
        
        # Electromagnetics & Power
        ("EEE361", "Electromagnetic Fields & Waves", 3),
        ("EEE362", "Power Systems", 3),
        ("EEE362L", "Power Systems Lab", 0),
        ("EEE363", "Electrical Machines", 3),
        ("EEE363L", "Electrical Machines Lab", 1),
        
        # Control
        ("EEE342", "Control Engineering", 3),
        ("EEE342L", "Control Engineering Lab", 1),
        
        # Additional Core
        ("EEE154", "Engineering Drawing", 1),  # Required for engineering
        ("EEE452", "Engineering Economics", 3),  # Professional course
    ],
    
    "capstone": [
        ("EEE299", "Junior Design Project I", 1),
        ("EEE499", "Senior Design Project I", 1.5),
        ("EEE499B", "Senior Design Project II", 1.5),
    ],
    
    "internship": [
        ("EEE498", "Intern/Co-op/Directed Research", 0),  # Non-credit
    ],
    
    "electives": {
        "solid_state_electronics": [
            ("EEE410", "Semiconductor Devices and Technology", 3),
            ("EEE411", "Introduction to VLSI Design", 3),
            ("EEE413", "Verilog HDL: Modelling, Simulation, and Synthesis", 3),
            ("EEE414", "Advanced VLSI Chip Design Methodology and Optimization using HDL", 3),
            ("EEE415", "CMOS Analog Circuit Design", 3),
            ("EEE491", "Special Topics in Solid State Electronics", 3),
        ],
        "power_system_engineering": [
            ("EEE461", "Power System Operations & Reliability", 3),
            ("EEE462", "Switchgear and Protection", 3),
            ("EEE464", "Power Stations", 3),
            ("EEE465", "High Voltage Engineering", 3),
            ("EEE468", "Sustainable Energy Technology Systems", 3),
            ("EEE492", "Special Topics in Power Systems", 3),
        ],
        "communications_engineering": [
            ("EEE422", "Principles of Digital Communications", 3),
            ("EEE424", "Mobile and Wireless Communication System", 3),
            ("EEE426", "Fiber Optic Communication System", 3),
            ("EEE427", "Satellite Communication System", 3),
            ("EEE428", "RF and Microwave Engineering", 3),
            ("EEE493", "Special Topics in Communications", 3),
        ],
        "robotics_intelligence": [
            ("EEE453", "Microprocessor Interface and Embedded System", 3),
            ("EEE432", "Artificial Intelligence", 3),
            ("EEE433", "Pattern Recognition and Neural Network", 3),
            ("EEE436", "Theory of Fuzzy Systems", 3),
            ("EEE469", "Computer Vision", 3),
            ("EEE494", "Special Topics in Robotics", 3),
        ],
        "telecommunication_systems": [
            ("EEE331", "Data Communications & Networks", 3),
            ("EEE421", "Stochastic Signals and Systems", 3),
            ("EEE423", "Principles of Telecommunication Network", 3),
            ("EEE451", "Telecommunications Business and Management", 3),
            ("EEE471", "Digital Signal Processing", 3),
            ("EEE495", "Special Topics in Telecommunications", 3),
        ],
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BBA - BACHELOR OF BUSINESS ADMINISTRATION (Department Code: 30)
#  Total Credits Required: 130
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BBA_COURSES = {
    "department_code": 30,
    "department_name": "School of Business & Economics",
    "degree": "Bachelor of Business Administration (BBA)",
    "total_credits": 130,
    
    "foundation": [
        # English Foundation
        ("ENG102", "Introduction to Composition", 3),
        ("ENG103", "Intermediate Composition", 3),
        ("ENG111", "Public Speaking", 3),
        ("BEN205", "Bangla Language", 3),
        
        # Math Foundation
        ("BUS130", "Business Mathematics", 3),
        ("BUS172", "Business Statistics I", 3),
        ("BUS272", "Business Statistics II", 3),
        
        # Social Sciences
        ("ECO101", "Introduction to Microeconomics", 3),
        ("ECO104", "Introduction to Macroeconomics", 3),
        ("POL101", "Introduction to Political Science", 3),
        ("SOC101", "Introduction to Sociology", 3),
        
        # Humanities
        ("PHI104", "Introduction to Ethics", 3),
        ("HIS102", "Introduction to World Civilization", 3),
        ("HIS103", "Emergence of Bangladesh", 3),
    ],
    
    "core": [
        # Accounting
        ("ACT201", "Introduction to Financial Accounting", 3),
        ("ACT202", "Introduction to Managerial Accounting", 3),
        
        # Finance
        ("FIN254", "Introduction to Financial Management", 3),
        
        # Management
        ("MGT201", "Principles of Management", 3),
        ("MGT321", "Organizational Behavior", 3),
        ("BUS240", "Business Law", 3),
        
        # Marketing
        ("MKT202", "Introduction to Marketing", 3),
        
        # Information Systems
        ("MIS101", "Introduction to Computer and Information Technology", 3),
        
        # International Business
        ("INB372", "International Business", 3),
        
        # Capstone
        ("BUS401", "Business Policy and Strategy", 3),
        ("BUS498", "Internship", 0),
    ],
    
    "majors": {
        "finance": {
            "required": [
                ("FIN433", "Financial Markets and Institutions", 3),
                ("FIN435", "Investment Theory", 3),
                ("FIN440", "Corporate Finance", 3),
                ("FIN444", "International Financial Management", 3),
            ],
            "electives": [
                ("FIN410", "Financial Statement Analysis", 3),
                ("FIN455", "Financial Modeling Using Excel", 3),
                ("FIN464", "Bank Management", 3),
                ("FIN470", "Insurance and Risk Management", 3),
                ("FIN480", "Financial Derivatives", 3),
            ],
        },
        "accounting": {
            "required": [
                ("ACT310", "Intermediate Accounting I", 3),
                ("ACT320", "Intermediate Accounting II", 3),
                ("ACT360", "Advanced Managerial Accounting", 3),
                ("ACT370", "Taxation", 3),
            ],
            "electives": [
                ("ACT380", "Audit and Assurance", 3),
                ("ACT410", "Financial Statement Analysis", 3),
                ("ACT430", "Accounting Information Systems", 3),
                ("ACT460", "Advanced Financial Accounting", 3),
            ],
        },
        "marketing": {
            "required": [
                ("MKT337", "Promotional Management", 3),
                ("MKT344", "Consumer Behavior", 3),
                ("MKT460", "Strategic Marketing", 3),
                ("MKT470", "Marketing Research", 3),
            ],
            "electives": [
                ("MKT330", "Digital Marketing", 3),
                ("MKT355", "Agricultural Marketing", 3),
                ("MKT382", "International Marketing", 3),
                ("MKT412", "Services Marketing", 3),
                ("MKT417", "Export Import Management", 3),
                ("MKT445", "Sales Management", 3),
                ("MKT450", "Marketing Channels", 3),
                ("MKT465", "Brand Management", 3),
                ("MKT475", "Marketing Analytics", 3),
            ],
        },
        "international_business": {
            "required": [
                ("MKT382", "International Marketing", 3),
                ("INB400", "International Trade & Finance", 3),
                ("INB480", "Global Business Strategy", 3),
                ("INB490", "Cross-Cultural Management", 3),
            ],
            "electives": [
                ("INB350", "International Business Negotiations", 3),
                ("INB355", "Country Risk Analysis", 3),
                ("INB410", "International Competitiveness", 3),
                ("INB415", "Global Fashion Buying & Merchandising", 3),
                ("INB495", "International Trade Law", 3),
                ("MKT417", "Export Import Management", 3),
            ],
        },
        "human_resource_management": {
            "required": [
                ("HRM340", "Training and Development", 3),
                ("HRM360", "Planning and Staffing", 3),
                ("HRM380", "Compensation", 3),
                ("HRM450", "Labor Management Relations", 3),
            ],
            "electives": [
                ("HRM370", "Leadership Theory and Practice", 3),
                ("HRM410", "Industrial Relations", 3),
                ("HRM470", "Negotiations", 3),
                ("HRM499", "Special Topics in HRM", 3),
                ("ECO441", "Labor Economics", 3),
            ],
        },
        "management": {
            "required": [
                ("MGT321", "Organizational Behavior", 3),
                ("MGT330", "Designing Effective Organizations", 3),
                ("HRM370", "Managerial Skill Development", 3),
                ("MGT410", "Organizational Development and Change Management", 3),
            ],
            "electives": [
                ("MGT350", "Managing Quality", 3),
                ("MGT490", "Project Management", 3),
                ("HRM450", "Labor Management Relations", 3),
                ("HRM470", "Negotiations", 3),
                ("MIS320", "Digital Enterprise Management", 3),
            ],
        },
        "management_information_systems": {
            "required": [
                ("MIS210", "Concepts of Computer Programming", 3),
                ("MIS310", "Database Systems for Business", 3),
                ("MIS320", "Digital Enterprise Management", 3),
                ("MIS470", "Systems Analysis and Design", 3),
            ],
            "electives": [
                ("MIS330", "Digital Marketing and Social Networks for Business", 3),
                ("MIS410", "Business Intelligence", 3),
                ("MIS450", "Data Communications and Computer Networks", 3),
                ("MIS499", "Special Topics in MIS", 3),
                ("MGT490", "Project Management", 3),
            ],
        },
        "supply_chain_management": {
            "required": [
                ("SCM310", "Logistics and Transportation", 3),
                ("SCM320", "Demand Planning and Fulfillment", 3),
                ("SCM450", "Global Procurement and Sourcing", 3),
                ("MGT460", "Six Sigma and Lean Manufacturing", 3),
            ],
            "electives": [
                ("SCM360", "Services Management", 3),
                ("SCM390", "Green Supply Chain Management", 3),
                ("MGT470", "Business Intelligence", 3),
                ("MGT490", "Project Management", 3),
            ],
        },
        "entrepreneurship": {
            "required": [
                ("ETR310", "New Venture Creation and Management", 3),
                ("ETR320", "Entrepreneurial Marketing", 3),
                ("ETR440", "Entrepreneurial Finance and VC", 3),
                ("ETR450", "International Entrepreneurship", 3),
            ],
            "electives": [
                ("ETR330", "Technology Entrepreneurship", 3),
                ("ETR380", "Corporate Entrepreneurship", 3),
                ("ETR490", "Seminar in Entrepreneurship", 3),
            ],
        },
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADDITIONAL NSU PROGRAMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ECE - ELECTRONIC & COMPUTER ENGINEERING (Department Code: 44)
ECE_COURSES = {
    "department_code": 44,
    "department_name": "Electronic & Computer Engineering",
    "degree": "Bachelor of Science in Electronic and Computer Engineering (BSECE)",
    "total_credits": 130,
    "foundation": [
        ("CSE115", "Programming Language I", 3),
        ("CSE115L", "Programming Language I Lab", 1),
    ],
    "core": [
        ("EEE141", "Electrical Circuits I", 3),
        ("EEE141L", "Electrical Circuits I Lab", 1),
        ("EEE111", "Analog Electronics I", 3),
        ("EEE111L", "Analog Electronics I Lab", 1),
        ("EEE211", "Digital Logic Design", 3),
        ("EEE211L", "Digital Logic Design Lab", 0),
        ("CSE225", "Data Structures and Algorithm", 3),
        ("CSE331", "Microprocessor Interfacing & Embedded Systems", 3),
        ("CSE332", "Computer Organization and Architecture", 3),
    ],
}

# ETE - ELECTRONICS & TELECOMMUNICATIONS ENGINEERING (Department Code: 45)
ETE_COURSES = {
    "department_code": 45,
    "department_name": "Electronics & Telecommunications Engineering",
    "degree": "Bachelor of Science in Electronics and Telecommunications Engineering (BSETE)",
    "total_credits": 130,
    "foundation": [
        ("CSE115", "Programming Language I", 3),
        ("CSE115L", "Programming Language I Lab", 1),
    ],
    "core": [
        ("EEE141", "Electrical Circuits I", 3),
        ("EEE141L", "Electrical Circuits I Lab", 1),
        ("EEE111", "Analog Electronics I", 3),
        ("EEE111L", "Analog Electronics I Lab", 1),
        ("EEE221", "Signals and Systems", 3),
        ("EEE321", "Introduction to Communications Systems", 3),
        ("EEE422", "Principles of Digital Communications", 3),
        ("EEE424", "Mobile and Wireless Communication System", 3),
    ],
}

# ARC - ARCHITECTURE (Department Code: 46)
ARC_COURSES = {
    "department_code": 46,
    "department_name": "Architecture",
    "degree": "Bachelor of Architecture (B.Arch)",
    "total_credits": 180,  # Architecture is typically 5 years
    "foundation": [
        ("ARC101", "Design Fundamentals I", 3),
        ("ARC102", "Design Fundamentals II", 3),
        ("ARC111", "Architectural Graphics I", 2),
    ],
    "core": [
        ("ARC201", "Architectural Design Studio I", 6),
        ("ARC202", "Architectural Design Studio II", 6),
        ("ARC221", "History of Architecture I", 3),
        ("ARC222", "History of Architecture II", 3),
        ("ARC231", "Building Construction I", 3),
        ("ARC232", "Building Construction II", 3),
        ("ARC241", "Environmental Control I", 3),
        ("ARC242", "Environmental Control II", 3),
    ],
}

# ENV - ENVIRONMENTAL SCIENCE & MANAGEMENT (Department Code: 47)
ENV_COURSES = {
    "department_code": 47,
    "department_name": "Environmental Science & Management",
    "degree": "Bachelor of Science in Environmental Science (BSES)",
    "total_credits": 130,
    "foundation": [
        ("ENV101", "Introduction to Environmental Science", 3),
        ("ENV102", "Environmental Chemistry", 3),
        ("BIO103", "Biology", 4),
    ],
    "core": [
        ("ENV201", "Ecology", 3),
        ("ENV202", "Environmental Biology", 3),
        ("ENV301", "Environmental Impact Assessment", 3),
        ("ENV302", "Environmental Pollution and Control", 3),
        ("ENV401", "Environmental Management Systems", 3),
    ],
}

# ECO - ECONOMICS (Department Code: 50)
ECO_COURSES = {
    "department_code": 50,
    "department_name": "Economics",
    "degree": "Bachelor of Science in Economics",
    "total_credits": 130,
    "foundation": [
        ("ECO101", "Introduction to Microeconomics", 3),
        ("ECO104", "Introduction to Macroeconomics", 3),
        ("MAT120", "Calculus I", 3),
        ("BUS172", "Business Statistics I", 3),
    ],
    "core": [
        ("ECO201", "Intermediate Microeconomics", 3),
        ("ECO202", "Intermediate Macroeconomics", 3),
        ("ECO301", "Econometrics I", 3),
        ("ECO302", "Econometrics II", 3),
        ("ECO401", "Mathematical Economics", 3),
    ],
}

# PHR - PHARMACY (Department Code: 60)
PHR_COURSES = {
    "department_code": 60,
    "department_name": "Pharmacy",
    "degree": "Bachelor of Pharmacy (B.Pharm)",
    "total_credits": 160,
    "foundation": [
        ("CHE101", "Chemistry I", 4),
        ("CHE101L", "Chemistry I Lab", 0),
        ("BIO103", "Biology", 4),
        ("PHY107", "Physics I", 3),
    ],
    "core": [
        ("PHR201", "Pharmaceutics I", 3),
        ("PHR202", "Pharmaceutical Chemistry I", 3),
        ("PHR211", "Pharmacology I", 3),
        ("PHR221", "Pharmacognosy I", 3),
        ("PHR301", "Clinical Pharmacy", 3),
        ("PHR401", "Pharmaceutical Analysis", 3),
    ],
}

# PBH - PUBLIC HEALTH (Department Code: 61)
PBH_COURSES = {
    "department_code": 61,
    "department_name": "Public Health",
    "degree": "Master of Public Health (MPH)",
    "total_credits": 60,
    "core": [
        ("PBH501", "Introduction to Public Health", 3),
        ("PBH502", "Epidemiology", 3),
        ("PBH503", "Biostatistics", 3),
        ("PBH504", "Health Policy and Management", 3),
        ("PBH505", "Environmental Health", 3),
    ],
}

# MIC - MICROBIOLOGY (Department Code: 62)
MIC_COURSES = {
    "department_code": 62,
    "department_name": "Microbiology",
    "degree": "Bachelor of Science in Microbiology",
    "total_credits": 130,
    "foundation": [
        ("BIO103", "Biology", 4),
        ("CHE101", "Chemistry I", 4),
    ],
    "core": [
        ("MIC201", "General Microbiology", 3),
        ("MIC202", "Microbiology Lab", 1),
        ("MIC301", "Bacteriology", 3),
        ("MIC302", "Virology", 3),
        ("MIC401", "Immunology", 3),
        ("MIC402", "Medical Microbiology", 3),
    ],
}

# BCH - BIOCHEMISTRY & BIOTECHNOLOGY (Department Code: 63)
BCH_COURSES = {
    "department_code": 63,
    "department_name": "Biochemistry & Biotechnology",
    "degree": "Bachelor of Science in Biochemistry and Biotechnology",
    "total_credits": 130,
    "foundation": [
        ("BIO103", "Biology", 4),
        ("CHE101", "Chemistry I", 4),
    ],
    "core": [
        ("BCH201", "Biochemistry I", 3),
        ("BCH202", "Biochemistry II", 3),
        ("BCH301", "Molecular Biology", 3),
        ("BCH302", "Genetic Engineering", 3),
        ("BCH401", "Biotechnology", 3),
        ("BCH402", "Bioinformatics", 3),
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COMBINED COURSE CATALOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NSU_PROGRAMS = {
    # School of Engineering & Applied Science
    "CSE": CSE_COURSES,
    "EEE": EEE_COURSES,
    "ECE": ECE_COURSES,
    "ETE": ETE_COURSES,
    "ARC": ARC_COURSES,
    "ENV": ENV_COURSES,
    
    # School of Business
    "BBA": BBA_COURSES,
    
    # School of Arts and Social Science
    "ECO": ECO_COURSES,
    
    # School of Life Science
    "PHR": PHR_COURSES,
    "PBH": PBH_COURSES,
    "MIC": MIC_COURSES,
    "BCH": BCH_COURSES,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FLAT COURSE LIST FOR LOOKUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_course_lookup():
    """Build a flat dictionary for course code lookup."""
    lookup = {}
    
    # University Core
    for category, courses in UNIVERSITY_CORE.items():
        for code, name, credits in courses:
            lookup[code] = {"name": name, "credits": credits, "category": f"University Core - {category}"}
    
    # SEPS Core
    for category, courses in SEPS_CORE.items():
        for code, name, credits in courses:
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"SEPS Core - {category}"}
    
    # CSE Courses
    for category in ["foundation", "core", "capstone", "internship"]:
        for code, name, credits in CSE_COURSES.get(category, []):
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"CSE - {category}"}
    
    for trail, courses in CSE_COURSES.get("electives", {}).items():
        for code, name, credits in courses:
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"CSE Elective - {trail}"}
    
    # EEE Courses
    for category in ["foundation", "core", "capstone", "internship"]:
        for code, name, credits in EEE_COURSES.get(category, []):
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"EEE - {category}"}
    
    for trail, courses in EEE_COURSES.get("electives", {}).items():
        for code, name, credits in courses:
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"EEE Elective - {trail}"}
    
    # BBA Courses
    for category in ["foundation", "core"]:
        for code, name, credits in BBA_COURSES.get(category, []):
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"BBA - {category}"}
    
    for major, data in BBA_COURSES.get("majors", {}).items():
        for code, name, credits in data.get("required", []):
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"BBA Major - {major}"}
        for code, name, credits in data.get("electives", []):
            if code not in lookup:
                lookup[code] = {"name": name, "credits": credits, "category": f"BBA Elective - {major}"}
    
    return lookup


COURSE_LOOKUP = _build_course_lookup()


def get_course_info(course_code: str) -> dict:
    """Get course information by code.
    
    Args:
        course_code: The course code (e.g., 'CSE115', 'EEE141', 'ACT201')
    
    Returns:
        Dict with name, credits, category or None if not found
    """
    code = course_code.upper().strip()
    return COURSE_LOOKUP.get(code)


def get_all_courses_for_program(program: str) -> list:
    """Get all courses for a specific program.
    
    Args:
        program: One of 'CSE', 'EEE', 'BBA'
    
    Returns:
        List of (code, name, credits) tuples
    """
    program = program.upper()
    if program not in NSU_PROGRAMS:
        return []
    
    courses = []
    prog_data = NSU_PROGRAMS[program]
    
    for category in ["foundation", "core", "capstone", "internship"]:
        courses.extend(prog_data.get(category, []))
    
    if "electives" in prog_data:
        for trail, trail_courses in prog_data["electives"].items():
            courses.extend(trail_courses)
    
    if "majors" in prog_data:
        for major, major_data in prog_data["majors"].items():
            courses.extend(major_data.get("required", []))
            courses.extend(major_data.get("electives", []))
    
    return courses


def get_mandatory_courses(program: str) -> list:
    """Get mandatory/required courses for a program.
    
    Args:
        program: One of 'CSE', 'EEE', 'BBA'
    
    Returns:
        List of course codes that are mandatory
    """
    program = program.upper()
    if program not in NSU_PROGRAMS:
        return []
    
    mandatory = []
    prog_data = NSU_PROGRAMS[program]
    
    for category in ["foundation", "core"]:
        for code, name, credits in prog_data.get(category, []):
            mandatory.append(code)
    
    return mandatory


def get_elective_courses(program: str) -> dict:
    """Get elective courses organized by trail/major.
    
    Args:
        program: One of 'CSE', 'EEE', 'BBA'
    
    Returns:
        Dict of trail/major -> list of (code, name, credits)
    """
    program = program.upper()
    if program not in NSU_PROGRAMS:
        return {}
    
    prog_data = NSU_PROGRAMS[program]
    
    if "electives" in prog_data:
        return prog_data["electives"]
    
    if "majors" in prog_data:
        return {major: data.get("electives", []) 
                for major, data in prog_data["majors"].items()}
    
    return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COURSE STATISTICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_course_stats():
    """Get statistics about the course catalog."""
    cse_courses = len(get_all_courses_for_program("CSE"))
    eee_courses = len(get_all_courses_for_program("EEE"))
    bba_courses = len(get_all_courses_for_program("BBA"))
    
    return {
        "total_unique_courses": len(COURSE_LOOKUP),
        "cse_courses": cse_courses,
        "eee_courses": eee_courses,
        "bba_courses": bba_courses,
        "university_core_courses": sum(len(c) for c in UNIVERSITY_CORE.values()),
        "seps_core_courses": sum(len(c) for c in SEPS_CORE.values()),
    }


if __name__ == "__main__":
    # Print course catalog statistics
    stats = get_course_stats()
    print("NSU Course Catalog Statistics")
    print("=" * 40)
    print(f"Total Unique Courses: {stats['total_unique_courses']}")
    print(f"CSE Courses: {stats['cse_courses']}")
    print(f"EEE Courses: {stats['eee_courses']}")
    print(f"BBA Courses: {stats['bba_courses']}")
    print(f"University Core: {stats['university_core_courses']}")
    print(f"SEPS Core: {stats['seps_core_courses']}")
    
    # Test lookup
    print("\nSample Course Lookups:")
    for code in ["CSE115", "EEE141", "ACT201", "MKT202", "MAT120"]:
        info = get_course_info(code)
        if info:
            print(f"  {code}: {info['name']} ({info['credits']} cr) - {info['category']}")
