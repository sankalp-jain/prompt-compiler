import os
import json
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST"], allow_headers=["Content-Type"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

META_PROMPT = """You are an expert prompt engineer. Given a use case, produce a high-quality
system prompt and user prompt that an experienced developer would hand to an LLM.

Rules:
- system_prompt: sets the LLM's role, constraints, and output format
- user_prompt: the concrete task or question, written to elicit the best possible response
- Be specific, not generic
- Avoid filler phrases ("As an AI...", "Certainly!", etc.)
- Output valid JSON only — no markdown, no extra text

Output schema:
{
  "system_prompt": "<string>",
  "user_prompt": "<string>"
}

- Avoid generic phrases like "You are an AI language model"
- Be explicit about output format and expectations
- Optimize for production-ready code

"""


class GenerateRequest(BaseModel):
    use_case: str


class GenerateResponse(BaseModel):
    system_prompt: str
    user_prompt: str


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": META_PROMPT},
            {"role": "user", "content": f"Use case: {req.use_case}"},
        ],
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {raw}")

    if "system_prompt" not in data or "user_prompt" not in data:
        raise HTTPException(status_code=502, detail=f"LLM response missing required keys: {data}")

    return GenerateResponse(**data)
