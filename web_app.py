# web_app.py
import os
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from openai import RateLimitError
from dotenv import load_dotenv

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

@app.post("/ask")
async def ask(query: str = Form(...)):
    async def stream_answer():
        try:
            # Get answer
            answer = invoke_with_retry(rag_chain, query)

            # Get source docs
            #result = rag_chain.invoke({"question": query})
            #docs = result.get("context", [])
            docs = retrieve_top3(query)
            sources = "<br>".join([
                   f"<a href='{d.metadata['url']}' target='_blank'>{d.metadata.get('title', 'Page')}</a>"
                   for d in docs
            ]) if docs else "No sources."
            #docs = retrieved if isinstance(retrieved, list) else []
            
            full = f"{answer}<br>Sources:<br>{sources}"
            for char in full:
                yield char
                await asyncio.sleep(0.01)

        except RateLimitError:
            yield "Rate limited. Retrying..."
            await asyncio.sleep(2)
            async for char in ask(query):
                yield char
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(stream_answer(), media_type="text/plain")
