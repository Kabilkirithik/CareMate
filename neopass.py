from fastapi import FastAPI
from pydantic import BaseModel
import boto3
import json
import re
import base64
from typing import Optional

app = FastAPI()

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="ap-south-1"
)

# ══════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════

class ContentPart(BaseModel):
    type: str                  # "text" or "image_url"
    text: Optional[str] = None
    image_url: Optional[dict] = None   # {"url": "data:image/png;base64,...."}

class Message(BaseModel):
    role: str
    content: str | list[ContentPart]   # string OR list of parts

class ChatRequest(BaseModel):
    messages: list[Message]


# ══════════════════════════════════════════════════════════════
# SECTION 1 — EXTRACT TEXT + IMAGES FROM REQUEST
# ══════════════════════════════════════════════════════════════

def parse_message(message: Message) -> tuple[str, list[str]]:
    """
    Returns (text, [base64_image, ...]) from a message.
    Handles both plain string content and multipart content.
    """
    if isinstance(message.content, str):
        return message.content, []

    text_parts = []
    images = []
    for part in message.content:
        if part.type == "text" and part.text:
            text_parts.append(part.text)
        elif part.type == "image_url" and part.image_url:
            url = part.image_url.get("url", "")
            # Extract base64 data from data URI: data:image/png;base64,<data>
            match = re.match(r"data:([^;]+);base64,(.+)", url)
            if match:
                images.append((match.group(1), match.group(2)))  # (media_type, b64data)

    return "\n".join(text_parts), images


# ══════════════════════════════════════════════════════════════
# SECTION 2 — VISION: EXTRACT SCHEMA FROM IMAGES
# Uses Claude claude-haiku-4-5-20251001 (via Bedrock) to read table images
# and return exact column names + sample data
# ══════════════════════════════════════════════════════════════

def extract_schema_from_images(images: list, question_text: str) -> str:
    """
    Sends images to Claude claude-haiku-4-5-20251001 on Bedrock and asks it to extract
    the exact table schema (column names, data types, sample values).
    Returns a schema description string.
    """
    if not images:
        return ""

    # Build image content blocks for Claude
    image_blocks = []
    for media_type, b64data in images:
        image_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64data
            }
        })

    image_blocks.append({
        "type": "text",
        "text": (
            "Look at the table image(s) above carefully.\n"
            "Extract and return ONLY:\n"
            "1. The exact table name (if visible)\n"
            "2. The exact column names as they appear\n"
            "3. The data type of each column (INT, VARCHAR, DECIMAL, BOOLEAN, etc.) based on sample values\n"
            "4. 1-2 sample values per column\n\n"
            "Format your response exactly like this:\n"
            "TABLE: <table_name>\n"
            "COLUMNS:\n"
            "- <column_name> (<data_type>) example: <sample_value>\n"
            "- <column_name> (<data_type>) example: <sample_value>\n"
            "...\n\n"
            "Be precise — the column names must match EXACTLY what is shown in the image."
        )
    })

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [
            {"role": "user", "content": image_blocks}
        ]
    })

    response = bedrock.invoke_model(
        modelId="anthropic.claude-haiku-4-5-20251001",
        body=body,
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


# ══════════════════════════════════════════════════════════════
# SECTION 3 — SQL TYPE DETECTOR
# ══════════════════════════════════════════════════════════════

def detect_sql_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["trigger", "after insert", "before insert", "after update",
                              "before update", "after delete", "before delete"]):
        return "trigger"
    if any(k in t for k in ["procedure", "call "]):
        return "procedure"
    if any(k in t for k in [" function", "create function", "returns ", "return "]):
        return "function"
    if any(k in t for k in ["cursor", "fetch", "open cursor"]):
        return "cursor"
    if any(k in t for k in ["transaction", "commit", "rollback", "savepoint"]):
        return "transaction"
    if any(k in t for k in ["create table", "alter table", "primary key", "foreign key"]):
        return "ddl"
    if any(k in t for k in ["insert into", "insert "]):
        return "insert"
    if any(k in t for k in ["update ", "set "]):
        return "update"
    if any(k in t for k in ["delete from", "delete "]):
        return "delete"
    return "select"


# ══════════════════════════════════════════════════════════════
# SECTION 4 — PROMPT BUILDER
# Injects real schema extracted from images into the prompt
# ══════════════════════════════════════════════════════════════

TYPE_RULES = {
    "function": """
FUNCTION RULES:
- Wrap with DELIMITER $$ ... DELIMITER ;
- DECLARE all local variables before any SELECT.
- Use: SELECT col INTO var FROM table WHERE id_col = param
- Use IF/ELSEIF for conditional logic. Always RETURN final value.
- Use DETERMINISTIC if result depends only on input.
""",
    "procedure": """
PROCEDURE RULES:
- Wrap with DELIMITER $$ ... DELIMITER ;
- Use IF/ELSEIF (NOT CASE inside SET) for conditional updates with fixed values.
- NEVER compare a column to itself: WRONG → WHERE col = col | CORRECT → WHERE col = param
- NEVER run UPDATE without a WHERE clause.
""",
    "trigger": """
TRIGGER RULES:
- Wrap with DELIMITER $$ ... DELIMITER ;
- Use NEW.col for inserted/updated values, OLD.col for previous values.
- Choose BEFORE to modify values, AFTER to react/log.
""",
    "cursor": """
CURSOR RULES:
- Wrap with DELIMITER $$ ... DELIMITER ;
- DECLARE order: variables → cursor → CONTINUE HANDLER.
- OPEN → LOOP → FETCH → check done → LEAVE → CLOSE.
""",
    "transaction": """
TRANSACTION RULES:
- Wrap with DELIMITER $$ ... DELIMITER ;
- Use EXIT HANDLER FOR SQLEXCEPTION → ROLLBACK.
- Pattern: START TRANSACTION → statements → COMMIT.
""",
    "ddl": """
DDL RULES:
- Use correct data types: INT, VARCHAR(n), DECIMAL(p,s), DATE, BOOLEAN.
- Add PRIMARY KEY, FOREIGN KEY, NOT NULL, DEFAULT as required.
""",
    "select": """
SELECT RULES:
- Use proper JOINs (INNER, LEFT, RIGHT) as needed.
- GROUP BY with aggregates. HAVING for aggregate filters.
- Use CTEs or window functions when needed.
""",
    "insert": "- Use INSERT INTO table (cols) VALUES or INSERT INTO ... SELECT.\n",
    "update":  "- Always include WHERE. Never compare column to itself.\n",
    "delete":  "- Always include WHERE. Use subqueries for multi-table conditions.\n",
}

def build_prompt(sql_type: str, question: str, schema_info: str) -> str:
    rules = TYPE_RULES.get(sql_type, "Write correct MySQL 8.0 code.\n")

    schema_section = f"""
REAL TABLE SCHEMA (extracted from the problem images — use these EXACT column names):
{schema_info}
→ ONLY use the column names listed above. NEVER guess or invent column names.
""" if schema_info else """
WARNING: No image schema was provided. Infer column names carefully from the problem text only.
"""

    return f"""You are a MySQL 8.0 expert solving a coding judge problem.

OUTPUT RULES (STRICT):
- Return ONLY raw executable MySQL code.
- NO markdown, NO backticks, NO explanations, NO comments.
- Use ONLY the exact column/table names from the schema below.
{schema_section}
{rules}
════════════════════════════════
Problem:
{question}
════════════════════════════════

Return ONLY the MySQL code. Nothing else."""


# ══════════════════════════════════════════════════════════════
# SECTION 5 — CODE CLEANER
# ══════════════════════════════════════════════════════════════

def clean_code(text: str) -> str:
    for token in ["[INST]", "[/INST]", "<s>", "</s>"]:
        text = text.replace(token, "")
    text = re.sub(r"```(?:sql|mysql|plaintext)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    m = re.search(r"(DELIMITER\s+\$\$[\s\S]*?DELIMITER\s+;)", text, re.IGNORECASE)
    if m: return m.group(1).strip()

    m = re.search(r"(CREATE\s+(?:PROCEDURE|FUNCTION|TRIGGER)[\s\S]*?END\s*\$\$)", text, re.IGNORECASE)
    if m: return "DELIMITER $$\n\n" + m.group(1).strip() + "\n\nDELIMITER ;"

    m = re.search(r"(CREATE\s+TABLE[\s\S]+?;)", text, re.IGNORECASE)
    if m: return m.group(1).strip()

    m = re.search(r"((?:WITH|SELECT|INSERT|UPDATE|DELETE|ALTER|DROP)[\s\S]+?;)", text, re.IGNORECASE)
    if m: return m.group(1).strip()

    return text.strip()


# ══════════════════════════════════════════════════════════════
# SECTION 6 — MAIN ENDPOINT
# ══════════════════════════════════════════════════════════════

@app.post("/chat")
async def chat(request: ChatRequest):

    last_message = request.messages[-1]
    question, images = parse_message(last_message)

    # Step 1: Read images with vision model to get real column names
    schema_info = ""
    if images:
        schema_info = extract_schema_from_images(images, question)

    # Step 2: Classify SQL type
    sql_type = detect_sql_type(question)

    # Step 3: Build prompt with real schema injected
    prompt = build_prompt(sql_type, question, schema_info)

    # Step 4: Call Llama on Bedrock for SQL generation
    body = json.dumps({
        "prompt": prompt,
        "max_gen_len": 800,
        "temperature": 0.0,
        "top_p": 0.9
    })

    response = bedrock.invoke_model(
        modelId="meta.llama3-8b-instruct-v1:0",
        body=body,
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    raw_answer = result.get("generation", "")
    code = clean_code(raw_answer)

    return {
        "choices": [{
            "message": {"role": "assistant", "content": code}
        }]
    }
