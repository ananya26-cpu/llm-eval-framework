import asyncio
import time
import sqlite3
from groq import Groq
from google import genai
from dotenv import load_dotenv
import os
import json

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DB_PATH = "evaluations.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT,
        model_name TEXT,
        response TEXT,
        latency_ms REAL,
        tokens_used INTEGER,
        cost_per_1k REAL,
        quality_score REAL,
        task_type TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def save_result(prompt, result, task_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO evaluations 
        (prompt, model_name, response, latency_ms, tokens_used, cost_per_1k, quality_score, task_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (prompt, result["model_name"], result["response"],
         result["latency_ms"], result["tokens_used"],
         result["cost_per_1k_tokens"], result["quality_score"], task_type))
    conn.commit()
    conn.close()

async def call_groq(prompt, model_id, model_name, cost):
    loop = asyncio.get_event_loop()
    start = time.time()
    try:
        response = await loop.run_in_executor(None, lambda: groq_client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        ))
        latency = round((time.time() - start) * 1000, 2)
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return {"model_name": model_name, "response": text, "latency_ms": latency,
                "tokens_used": tokens, "cost_per_1k_tokens": cost, "quality_score": 0.0}
    except Exception as e:
        return {"model_name": model_name, "response": f"Error: {str(e)}",
                "latency_ms": 0, "tokens_used": 0, "cost_per_1k_tokens": cost, "quality_score": 0.0}

async def call_gemini(prompt):
    loop = asyncio.get_event_loop()
    start = time.time()
    try:
        response = await loop.run_in_executor(None, lambda: gemini_client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        ))
        latency = round((time.time() - start) * 1000, 2)
        text = response.text
        tokens = len(text.split()) * 2
        return {"model_name": "Gemini 2.0 Flash", "response": text, "latency_ms": latency,
                "tokens_used": tokens, "cost_per_1k_tokens": 0.0, "quality_score": 0.0}
    except Exception as e:
        return {"model_name": "Gemini 2.0 Flash", "response": f"Error: {str(e)}",
                "latency_ms": 0, "tokens_used": 0, "cost_per_1k_tokens": 0.0, "quality_score": 0.0}

def score_quality(results, prompt):
    try:
        responses_text = ""
        for r in results:
            responses_text += f"\nModel: {r['model_name']}\nResponse: {r['response'][:300]}\n"
        judge_prompt = f"""You are an AI judge. Score each model response from 0-10 based on accuracy, clarity, and helpfulness for this prompt: "{prompt}"
{responses_text}
Reply ONLY with a JSON like: {{"LLaMA 70B": 8.5, "LLaMA 8B": 7.0, "Gemini 2.0 Flash": 9.0}}"""
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": judge_prompt}],
            max_tokens=100
        )
        scores_text = response.choices[0].message.content
        s = scores_text.find("{")
        e = scores_text.rfind("}") + 1
        scores = json.loads(scores_text[s:e])
        for r in results:
            r["quality_score"] = scores.get(r["model_name"], 5.0)
    except:
        for r in results:
            r["quality_score"] = 5.0
    return results

def pick_winner(results):
    best = None
    best_score = -1
    for r in results:
        combined = (r["quality_score"] * 0.5) + \
                   (1000 / max(r["latency_ms"], 1) * 0.3) + \
                   ((1 - r["cost_per_1k_tokens"]) * 0.2)
        if combined > best_score:
            best_score = combined
            best = r
    return best["model_name"] if best else results[0]["model_name"]

async def evaluate(prompt, task_type="general"):
    tasks = [
        call_groq(prompt, "llama-3.3-70b-versatile", "LLaMA 70B", 0.59),
        call_groq(prompt, "llama-3.1-8b-instant", "LLaMA 8B", 0.05),
        call_gemini(prompt)
    ]
    results = list(await asyncio.gather(*tasks))
    results = score_quality(results, prompt)
    winner = pick_winner(results)
    for r in results:
        r["winner"] = (r["model_name"] == winner)
        save_result(prompt, r, task_type)
    reasoning = f"{winner} scored highest on combined quality, speed, and cost efficiency."
    return {"prompt": prompt, "results": results, "recommended_model": winner, "reasoning": reasoning}
