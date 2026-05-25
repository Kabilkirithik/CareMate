from caremate_v4.tools.patient_details_tool import PatientDetailsTool


def test():

    tool = PatientDetailsTool()

    print("\n--- BASIC INFO ---")
    print(tool._run(patient_id="P001", action="basic_info"))

    print("\n--- ACTIVE VISIT ---")
    print(tool._run(patient_id="P001", action="active_visit"))

    print("\n--- TIMELINE ---")
    print(tool._run(patient_id="P001", action="timeline"))

    print("\n--- SUMMARY DATA ---")
    print(tool._run(patient_id="P001", action="summary_data"))


if __name__ == "__main__":
    test()