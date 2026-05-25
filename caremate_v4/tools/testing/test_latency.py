import asyncio
import time

# Import your tools
from emergency import emergency_precheck, EmergencyDetectionTool
from intent_routing_tool import IntentRoutingTool


# Initialize tools
emergency_tool = EmergencyDetectionTool()
intent_tool = IntentRoutingTool()


# --------------------------------------------
# Single Pipeline Test
# --------------------------------------------
async def run_pipeline(text, patient_id="P001", bed_id="B12"):

    print(f"\n--- Testing Input: '{text}' ---")

    # Total pipeline timer
    pipeline_start = time.perf_counter()

    # ----------------------------------
    # Step 1 — Emergency Precheck
    # ----------------------------------
    t1 = time.perf_counter()

    is_emergency, severity, reason = emergency_precheck(text)

    t2 = time.perf_counter()
    print(f"Emergency Precheck Latency: {(t2 - t1)*1000:.2f} ms")

    # ----------------------------------
    # Step 2 — Emergency Tool (if needed)
    # ----------------------------------
    if is_emergency:
        t3 = time.perf_counter()

        await emergency_tool._run(
            patient_id=patient_id,
            bed_id=bed_id,
            severity=severity,
            reason=reason
        )

        t4 = time.perf_counter()
        print(f"Emergency Tool Latency: {(t4 - t3)*1000:.2f} ms")

    # ----------------------------------
    # Step 3 — Intent Routing Tool
    # ----------------------------------
    t5 = time.perf_counter()

    intent_result = await intent_tool._run(text=text)

    t6 = time.perf_counter()
    print(f"Intent Tool Latency: {(t6 - t5)*1000:.2f} ms")

    print("Intent Result:", intent_result)

    # ----------------------------------
    # Total Pipeline Time
    # ----------------------------------
    pipeline_end = time.perf_counter()

    print(f"TOTAL PIPELINE LATENCY: {(pipeline_end - pipeline_start)*1000:.2f} ms")


# --------------------------------------------
# Simultaneous Multi-Input Test
# --------------------------------------------
async def test_simultaneous():

    print("\n==============================")
    print("SIMULTANEOUS LATENCY TEST")
    print("==============================")

    texts = [
        "I need water",
        "I can't breathe",
        "Bring blanket please",
        "I feel something is wrong",
        "I'm bored today",
        "Help urgently",
    ]

    tasks = [run_pipeline(t) for t in texts]

    start = time.perf_counter()

    await asyncio.gather(*tasks)

    end = time.perf_counter()

    print("\nTOTAL SIMULTANEOUS EXECUTION TIME:",
          f"{(end - start)*1000:.2f} ms")


# --------------------------------------------
# MAIN
# --------------------------------------------
if __name__ == "__main__":
    asyncio.run(test_simultaneous())