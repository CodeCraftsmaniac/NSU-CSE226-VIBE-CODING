#!/usr/bin/env python3
"""Check user and scan history in database."""

from backend.database import get_supabase, get_user_by_email, get_user_scans
import json

email = 'mdrakibul2004@gmail.com'

# Check if user exists
user = get_user_by_email(email)
if user:
    print('USER FOUND:')
    print(json.dumps(user, indent=2, default=str))
    print('\n' + '='*60)
    
    # Check scans for this user
    scans = get_user_scans(user['id'], limit=10)
    print(f'\nSCAN HISTORY ({len(scans)} scans):')
    if scans:
        for scan in scans:
            print(f"  - {scan['filename']} | CGPA: {scan['cgpa']} | Courses: {scan['total_courses']} | {scan['created_at']}")
    else:
        print('  No scans found')
else:
    print(f'USER NOT FOUND: {email}')
    print('User needs to sign in first to create account in database')
