
import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent))

from caremate_v4.tools.emergency import emergency_precheck

test_emergencies = [
    "I can't breathe",
    "I am having a heart attack",
    "I fell down and can't get up",
    "Help me please",
    "I want some water"
]

for msg in test_emergencies:
    is_emergency, severity, reason = emergency_precheck(msg)
    print(f"Message: '{msg}' -> Emergency: {is_emergency}, Severity: {severity}, Reason: {reason}")
