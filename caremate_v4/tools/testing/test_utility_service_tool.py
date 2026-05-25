from caremate_v4.tools.utility_service_tool import UtilityServiceTool


def test_utility_service():

    tool = UtilityServiceTool()

    print("🧰 Testing Utility Service Tool...\n")

    # Example patient request
    result = tool.run(
        patient_id="P001",
        bed_number="B12",
        request_text="I need a blanket."
    )

    print("📌 Request Created:")
    print(result)

    print("\n⏱ Checking SLA Reminder...")

    reminder = tool.check_sla_and_trigger_reminder(result)

    print("Reminder Status:")
    print(reminder)

    print("\n✅ Simulating Service Completion...")

    completion = tool.confirm_completion(result)

    print("Completion Result:")
    print(completion)


if __name__ == "__main__":
    test_utility_service()