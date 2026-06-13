from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from models import EvalRequest
from evaluator import evaluate, init_db, save_feedback
from groq import Groq
from dotenv import load_dotenv
import os
import sqlite3
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI(title="LLM Evaluation Framework", version="2.0.0")

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
    return {"message": "LLM Eval API is running", "version": "2.0.0"}

@app.post("/evaluate")
async def run_evaluation(request: EvalRequest):
    result = await evaluate(request.prompt, request.task_type)
    return result

@app.post("/detect-task")
async def detect_task(request: EvalRequest):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": f"""Classify this prompt into exactly one category: coding, creative, analysis, reasoning, or general.
Prompt: "{request.prompt}"
Reply with ONLY the category word, nothing else."""}],
            max_tokens=10
        )
        task = response.choices[0].message.content.strip().lower()
        if task not in ["coding", "creative", "analysis", "reasoning", "general"]:
            task = "general"
        return {"task_type": task}
    except:
        return {"task_type": "general"}

@app.get("/history")
def get_history():
    conn = sqlite3.connect("evaluations.db")
    c = conn.cursor()
    c.execute("SELECT * FROM evaluations ORDER BY timestamp DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return {"evaluations": rows}

@app.get("/stats")
def get_stats():
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

@app.get("/heatmap")
def get_heatmap():
    conn = sqlite3.connect("evaluations.db")
    c = conn.cursor()
    models = ["LLaMA 70B", "LLaMA 8B", "Gemini 2.0 Flash"]
    tasks = ["coding", "creative", "analysis", "reasoning", "general"]
    heatmap = {}
    for model in models:
        heatmap[model] = {}
        for task in tasks:
            c.execute("""SELECT COUNT(*) as wins FROM evaluations
                WHERE model_name=? AND task_type=? AND quality_score=(
                    SELECT MAX(quality_score) FROM evaluations e2
                    WHERE e2.timestamp=evaluations.timestamp
                )""", (model, task))
            row = c.fetchone()
            c.execute("SELECT COUNT(*) FROM evaluations WHERE task_type=?", (task,))
            total = c.fetchone()[0]
            wins = row[0] if row else 0
            heatmap[model][task] = round((wins / max(total, 1)) * 100)
    conn.close()
    return {"heatmap": heatmap, "tasks": tasks, "models": models}

@app.get("/memory")
def get_memory():
    conn = sqlite3.connect("evaluations.db")
    c = conn.cursor()
    c.execute("""SELECT task_type, model_name, COUNT(*) as wins
        FROM evaluations
        WHERE quality_score = (
            SELECT MAX(e2.quality_score) FROM evaluations e2
            WHERE e2.task_type = evaluations.task_type
        )
        GROUP BY task_type, model_name
        ORDER BY wins DESC""")
    rows = c.fetchall()
    memory = {}
    for task, model, wins in rows:
        if task not in memory:
            memory[task] = {"best_model": model, "wins": wins}
    conn.close()
    return {"memory": memory}

@app.post("/feedback")
async def submit_feedback(request: dict):
    save_feedback(
        prompt=request.get("prompt", ""),
        predicted_winner=request.get("predicted_winner", ""),
        task_type=request.get("task_type", "general"),
        helpful=1 if request.get("helpful") else 0
    )
    return {"status": "saved"}

@app.get("/feedback-stats")
def get_feedback_stats():
    conn = sqlite3.connect("evaluations.db")
    c = conn.cursor()
    c.execute("""SELECT predicted_winner, task_type,
        SUM(helpful) as thumbs_up,
        COUNT(*) - SUM(helpful) as thumbs_down,
        COUNT(*) as total,
        ROUND(SUM(helpful) * 100.0 / COUNT(*), 0) as approval_rate
        FROM feedback
        GROUP BY predicted_winner, task_type
        ORDER BY approval_rate DESC""")
    rows = c.fetchall()
    conn.close()
    stats = [{"model": r[0], "task": r[1], "thumbs_up": r[2],
              "thumbs_down": r[3], "total": r[4], "approval_rate": r[5]} for r in rows]
    return {"feedback_stats": stats}

@app.get("/benchmarks")
def get_benchmarks():
    benchmarks = {
        "coding": [
            "Write a Python function to reverse a linked list",
            "Explain the difference between REST and GraphQL APIs",
            "Write SQL to find top 10 customers by revenue",
            "Debug this code: for i in range(10) print(i)",
            "What is the time complexity of quicksort?"
        ],
        "creative": [
            "Write a tagline for an AI startup",
            "Write a short poem about machine learning",
            "Create a product name for an LLM evaluation tool",
            "Write an elevator pitch for a data analytics app",
            "Describe AI in one metaphor"
        ],
        "analysis": [
            "Summarize the key benefits of cloud computing for enterprise",
            "What are the tradeoffs between SQL and NoSQL databases?",
            "Analyze the pros and cons of remote work",
            "What is the ROI formula and how is it calculated?",
            "Compare supervised vs unsupervised learning"
        ],
        "reasoning": [
            "Explain how transformer neural networks work",
            "What happens when an unstoppable force meets an immovable object?",
            "If all Bloops are Razzles and all Razzles are Lazzles, are all Bloops Lazzles?",
            "What is the CAP theorem in distributed systems?",
            "Explain the Monty Hall problem"
        ],
        "general": [
            "What are the best practices for database indexing?",
            "Generate a professional email declining a meeting request",
            "What is ambient intelligence?",
            "Explain LLM evaluation in simple terms",
            "What makes a good product manager?"
        ]
    }
    return {"benchmarks": benchmarks}

@app.post("/export-pdf")
async def export_pdf(request: EvalRequest):
    result = await evaluate(request.prompt, request.task_type)
    filename = "/tmp/llm_eval_report.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("LLM Evaluation Report", styles['Title']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Prompt: {request.prompt}", styles['Normal']))
    story.append(Paragraph(f"Task Type: {request.task_type}", styles['Normal']))
    story.append(Paragraph(f"Recommended Model: {result['recommended_model']}", styles['Heading2']))
    story.append(Paragraph(f"Reasoning: {result['reasoning']}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    data = [["Model", "Quality", "Latency", "Tokens", "Cost/1k", "Confidence", "Winner"]]
    for r in result["results"]:
        data.append([
            r["model_name"],
            f"{r['quality_score']}/10",
            str(r["latency_ms"])+"ms",
            str(r["tokens_used"]),
            f"${r['cost_per_1k_tokens']}",
            f"{r.get('confidence', 0)}%",
            "✓" if r["winner"] else ""
        ])
    table = Table(data, colWidths=[1.6*inch, 0.7*inch, 0.9*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0b1520')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(table)
    doc.build(story)
    return FileResponse(filename, media_type="application/pdf", filename="llm_eval_report.pdf")

@app.post("/batch-evaluate")
async def batch_evaluate(request: dict):
    prompts = request.get("prompts", [])
    task_type = request.get("task_type", "general")
    if len(prompts) > 20:
        prompts = prompts[:20]
    all_results = []
    for prompt in prompts:
        try:
            result = await evaluate(prompt, task_type)
            all_results.append(result)
        except:
            pass
    model_stats = {}
    for eval_result in all_results:
        for r in eval_result["results"]:
            name = r["model_name"]
            if name not in model_stats:
                model_stats[name] = {"total_tokens": 0, "total_cost": 0, "wins": 0, "avg_quality": []}
            model_stats[name]["total_tokens"] += r["tokens_used"]
            model_stats[name]["total_cost"] += (r["tokens_used"] / 1000) * r["cost_per_1k_tokens"]
            model_stats[name]["avg_quality"].append(r["quality_score"])
            if r["winner"]:
                model_stats[name]["wins"] += 1
    for name in model_stats:
        scores = model_stats[name]["avg_quality"]
        model_stats[name]["avg_quality"] = round(sum(scores)/len(scores), 2) if scores else 0
        model_stats[name]["total_cost"] = round(model_stats[name]["total_cost"], 4)
    viable = {k:v for k,v in model_stats.items() if v["avg_quality"] >= 6}
    cheapest = min(viable.items(), key=lambda x: x[1]["total_cost"]) if viable else None
    most_expensive = max(model_stats.items(), key=lambda x: x[1]["total_cost"])
    monthly_saving = 0
    if cheapest and cheapest[0] != most_expensive[0]:
        monthly_saving = round((most_expensive[1]["total_cost"] - cheapest[1]["total_cost"]) * 720, 2)
    return {
        "total_prompts": len(all_results),
        "results": all_results,
        "model_stats": model_stats,
        "recommended_model": cheapest[0] if cheapest else None,
        "monthly_saving_usd": monthly_saving,
        "insight": f"Switching to {cheapest[0]} saves ~${monthly_saving}/month at scale" if cheapest and monthly_saving > 0 else "Models are similarly priced"
    }


