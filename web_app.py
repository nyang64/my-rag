# web_app.py
import os
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from openai import RateLimitError
from dotenv import load_dotenv
import re

# --- Reuse your RAG chain ---
from scraper.raq_query import rag_chain, invoke_with_retry, retrieve_top3

load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

def clean_response(text: str) -> str:
    """Remove DeepSeek control tokens and extra whitespace."""
    # Remove <｜begin▁of▁sentence｜>, <｜end▁of▁sentence｜>, etc.
    text = re.sub(r"<｜[^｜]+｜>", "", text)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace
    return text.strip()

@app.post("/ask")
async def ask(query: str = Form(...)):
    async def stream_answer():
        try:
            answer = clean_response(invoke_with_retry(rag_chain, query))
            docs = retrieve_top3(query)

            # ← Use \n (not <br>) — JS will convert
            sources = "\n".join([
                f"<a href='{d.metadata['url']}' target='_blank'>{d.metadata.get('title', 'Page')}</a>"
                for d in docs
            ]) if docs else "No sources."

            full = f"{answer}\n\nSources:\n{sources}"
            for char in full:
                yield char
                await asyncio.sleep(0.01)

        except RateLimitError:
            yield "Rate limited. Retrying..."
            await asyncio.sleep(2)
            async for char in stream_answer():
                yield char
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(stream_answer(), media_type="text/plain")