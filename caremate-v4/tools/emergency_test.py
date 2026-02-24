import asyncio

from emergency import (
    emergency_precheck,
    EmergencyDetectionTool
)

tool = EmergencyDetectionTool()


async def test_emergency():

    print("\n=== TEST 1: Multiple Inputs ===")

    texts = [
        "I need water",
        "Help urgently",
        "I can't breathe",
        "I'm bored",
        "Chest pain"
    ]

    # Step 1 — Test FAST detection for multiple inputs
    for t in texts:
        is_emergency, severity, reason = emergency_precheck(t)
        print(f"Input: {t} → {is_emergency}, {severity}, {reason}")

        # Step 2 — Trigger tool ONLY if emergency detected
        if is_emergency:
            result = await tool._run(
                patient_id="P001",
                bed_id="B12",
                severity=severity,
                reason=reason
            )
            print("Tool Result:", result)

    print("\n=== TEST 2: Normal Message ===")

    text2 = "I am feeling bored today"
    result2 = emergency_precheck(text2)
    print("Precheck Output:", result2)


if __name__ == "__main__":
    asyncio.run(test_emergency())





# import asyncio

# from emergency_tool import (
#     emergency_precheck,
#     EmergencyDetectionTool
# )

# tool = EmergencyDetectionTool()


# async def test_emergency():

#     print("\n=== TEST 1: Critical Emergency ===")
#     text = "I can't breathe properly"

#     # Step 1 — Test fast detection
#     is_emergency, severity, reason = emergency_precheck(text)
#     print("Precheck Output:", is_emergency, severity, reason)

#     # Step 2 — Only call tool if emergency
#     if is_emergency:
#         result = await tool._run(
#             patient_id="P001",
#             bed_id="B12",
#             severity=severity,
#             reason=reason
#         )
#         print("Tool Result:", result)

#     print("\n=== TEST 2: Normal Message ===")
#     text2 = "I am feeling bored today"

#     result2 = emergency_precheck(text2)
#     print("Precheck Output:", result2)


# if __name__ == "__main__":
#     asyncio.run(test_emergency())