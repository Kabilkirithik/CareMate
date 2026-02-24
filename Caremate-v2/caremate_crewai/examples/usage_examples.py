"""
CareMate Example Usage
Demonstrates different patient query scenarios
"""

from caremate.crew import CareMateCrew
import json


def print_result(title: str, result: dict):
    """Pretty print results"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)
    print(json.dumps(result, indent=2))
    print("="*80 + "\n")


def main():
    """Run example scenarios"""
    
    # Initialize CareMate crew
    print("Initializing CareMate Crew...")
    caremate = CareMateCrew()
    print("✓ CareMate initialized\n")
    
    # ========================================================================
    # Scenario 1: EMERGENCY - Chest Pain
    # ========================================================================
    print("📍 Scenario 1: Emergency - Chest Pain")
    print("-" * 80)
    
    result1 = caremate.process_patient_query(
        query="I'm having severe chest pain and I can't breathe properly",
        hospital_id="PT-001",
        bed_number="ICU-301"
    )
    
    print_result("EMERGENCY SCENARIO", result1)
    print("Expected behavior:")
    print("  ✓ Classified as EMERGENCY")
    print("  ✓ Immediate escalation to emergency staff")
    print("  ✓ No approval process delay")
    print("  ✓ Reassuring response to patient\n")
    
    
    # ========================================================================
    # Scenario 2: MEDICAL - Medication Request
    # ========================================================================
    print("📍 Scenario 2: Medical - Medication Request")
    print("-" * 80)
    
    result2 = caremate.process_patient_query(
        query="Can I have my pain medication? I'm feeling uncomfortable",
        hospital_id="PT-002",
        bed_number="Room-205"
    )
    
    print_result("MEDICATION REQUEST", result2)
    print("Expected behavior:")
    print("  ✓ Classified as MEDICAL")
    print("  ✓ Requires nurse approval (hospital policy)")
    print("  ✓ Nurse notified")
    print("  ✓ Approval queue entry created")
    print("  ✓ Patient told nurse is coming\n")
    
    
    # ========================================================================
    # Scenario 3: MEDICAL - General Health Concern
    # ========================================================================
    print("📍 Scenario 3: Medical - Feeling Dizzy")
    print("-" * 80)
    
    result3 = caremate.process_patient_query(
        query="I've been feeling dizzy for the last hour",
        hospital_id="PT-003",
        bed_number="Room-412"
    )
    
    print_result("HEALTH CONCERN", result3)
    print("Expected behavior:")
    print("  ✓ Classified as MEDICAL")
    print("  ✓ Requires nurse approval")
    print("  ✓ Nurse notified")
    print("  ✓ No direct medical advice given\n")
    
    
    # ========================================================================
    # Scenario 4: NON-MEDICAL - Water Request
    # ========================================================================
    print("📍 Scenario 4: Non-Medical - Water Request")
    print("-" * 80)
    
    result4 = caremate.process_patient_query(
        query="Can I have some water please?",
        hospital_id="PT-004",
        bed_number="Room-108"
    )
    
    print_result("WATER REQUEST", result4)
    print("Expected behavior:")
    print("  ✓ Classified as NON_MEDICAL")
    print("  ✓ Auto-response allowed")
    print("  ✓ Nurse notified to bring water")
    print("  ✓ No approval delay\n")
    
    
    # ========================================================================
    # Scenario 5: NON-MEDICAL - Room Temperature
    # ========================================================================
    print("📍 Scenario 5: Non-Medical - Temperature Control")
    print("-" * 80)
    
    result5 = caremate.process_patient_query(
        query="The room is too cold, can you make it warmer?",
        hospital_id="PT-005",
        bed_number="Room-310"
    )
    
    print_result("TEMPERATURE REQUEST", result5)
    print("Expected behavior:")
    print("  ✓ Classified as NON_MEDICAL")
    print("  ✓ Auto-response with helpful suggestion")
    print("  ✓ Nurse notified")
    print("  ✓ Quick resolution\n")
    
    
    # ========================================================================
    # Scenario 6: DISTRESS - Repeated Request
    # ========================================================================
    print("📍 Scenario 6: Distress Detection - Repeated Request")
    print("-" * 80)
    
    # Simulate conversation history
    result6 = caremate.process_patient_query(
        query="I really need help please, I've been asking for assistance",
        hospital_id="PT-006",
        bed_number="Room-215"
    )
    
    print_result("DISTRESS DETECTED", result6)
    print("Expected behavior:")
    print("  ✓ Distress signals detected")
    print("  ✓ Escalated even if non-medical")
    print("  ✓ Higher priority notification")
    print("  ✓ Empathetic response\n")
    
    
    # ========================================================================
    # Scenario 7: INFORMATION - Visiting Hours
    # ========================================================================
    print("📍 Scenario 7: Information Request - Visiting Hours")
    print("-" * 80)
    
    result7 = caremate.process_patient_query(
        query="When can my family visit?",
        hospital_id="PT-007",
        bed_number="Room-503"
    )
    
    print_result("INFORMATION REQUEST", result7)
    print("Expected behavior:")
    print("  ✓ Classified as NON_MEDICAL")
    print("  ✓ Direct informational response")
    print("  ✓ No staff escalation needed")
    print("  ✓ Helpful and clear\n")
    
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*80)
    print("  EXAMPLE SCENARIOS COMPLETED")
    print("="*80)
    print("\nKey Takeaways:")
    print("  1. Emergency situations are detected and escalated immediately")
    print("  2. Medical requests always require human approval")
    print("  3. Medication requests have mandatory nurse review")
    print("  4. Non-medical requests can be auto-handled safely")
    print("  5. Distress signals trigger appropriate escalation")
    print("  6. All interactions are logged for audit trail")
    print("  7. Patient safety is always the top priority")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
