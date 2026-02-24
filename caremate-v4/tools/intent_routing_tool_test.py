import asyncio
from intent_routing_tool import IntentRoutingTool

tool = IntentRoutingTool()

async def test():

    texts = [
        "I need water",
        "What is my disease?",
        "Bring blanket please",
        "I'm hungry",
        "Did nurse come?",
        "I feel something is wrong",
        "I'm bored today"
    ]

    for t in texts:
        result = await tool._run(text=t)
        print(f"{t} → {result}")

asyncio.run(test())