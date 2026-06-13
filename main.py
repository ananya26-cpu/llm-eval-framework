
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import EvalRequest
from evaluator import evaluate, init_db
import asyncio

app = FastAPI(title="LLM Evaluation Framework", version="1.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
	init_db()

@app.get("/")
def root():
	return {"message": "LLM Eval API is running", "docs": "/docs"}

@app.post("/evaluate")
async def run_evaluation(request: EvalRequest):
	result = await evaluate(request.prompt, request.task_type)
	return result

@app.get("/history")
def get_history():
	import sqlite3
	conn = sqlite3.connect("evaluations.db")
	c = conn.cursor()
	c.execute("SELECT * FROM evaluations ORDER BY timestamp DESC LIMIT 50")
	rows = c.fetchall()
	conn.close()
	return {"evaluations": rows}

@app.get("/stats")
def get_stats():
	import sqlite3
	conn = sqlite3.connect("evaluations.db")
	c = conn.cursor()
	c.execute("""SELECT model_name, 
		ROUND(AVG(quality_score), 2) as avg_quality,
		ROUND(AVG(latency_ms), 2) as avg_latency,
		COUNT(*) as total_evals
		FROM evaluations GROUP BY model_name""")
	rows = c.fetchall()
	conn.close()
	return {"stats": rows}
