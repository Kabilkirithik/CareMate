import boto3

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1"
)

MODEL_ID = "arn:aws:bedrock:us-east-1:308116825446:application-inference-profile/wdzgxjy7lo97"


def ask_llm(prompt):

    response = client.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
    )

    return response["output"]["message"]["content"][0]["text"]


print(ask_llm("Explain AI in one sentence"))