import { useState } from "react"
import axios from "axios"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis } from "recharts"

export default function App() {
  const [prompt, setPrompt] = useState("")
  const [taskType, setTaskType] = useState("general")
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const evaluate = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const res = await axios.post("http://127.0.0.1:8000/evaluate", {
        prompt, task_type: taskType
      })
      setResults(res.data)
    } catch (e) {
      setError("Failed to connect to backend. Make sure it's running.")
    }
    setLoading(false)
  }

  const chartData = results?.results.map(r => ({
    name: r.model_name,
    Quality: r.quality_score,
    Speed: Math.min(10, 5000 / Math.max(r.latency_ms, 1)),
    Latency: Math.round(r.latency_ms),
    Tokens: r.tokens_used,
  })) || []

  return (
    <div style={{minHeight:"100vh",background:"#070d14",color:"#e8f4ff",fontFamily:"'Inter',sans-serif",padding:"40px 20px"}}>
      <div style={{maxWidth:"1100px",margin:"0 auto"}}>
        
        {/* Header */}
        <div style={{textAlign:"center",marginBottom:"48px"}}>
          <h1 style={{fontSize:"2.8rem",fontWeight:"800",background:"linear-gradient(135deg,#00d4ff,#7c3aed)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent",margin:0}}>
            LLM Evaluation Framework
          </h1>
          <p style={{color:"#6b8fa8",marginTop:"12px",fontSize:"1.1rem"}}>
            Compare AI models on quality, speed & cost — in real time
          </p>
        </div>

        {/* Input */}
        <div style={{background:"#0b1520",border:"1px solid #0f2035",borderRadius:"16px",padding:"32px",marginBottom:"32px"}}>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="Enter your prompt here..."
            style={{width:"100%",minHeight:"120px",background:"#070d14",border:"1px solid #0f2035",borderRadius:"10px",color:"#e8f4ff",padding:"16px",fontSize:"1rem",resize:"vertical",outline:"none",boxSizing:"border-box"}}
          />
          <div style={{display:"flex",gap:"16px",marginTop:"16px",alignItems:"center",flexWrap:"wrap"}}>
            <select
              value={taskType}
              onChange={e => setTaskType(e.target.value)}
              style={{background:"#070d14",border:"1px solid #0f2035",borderRadius:"8px",color:"#e8f4ff",padding:"10px 16px",fontSize:"0.95rem"}}
            >
              <option value="general">General</option>
              <option value="coding">Coding</option>
              <option value="creative">Creative</option>
              <option value="analysis">Analysis</option>
              <option value="reasoning">Reasoning</option>
            </select>
            <button
              onClick={evaluate}
              disabled={loading || !prompt.trim()}
              style={{background:loading?"#0f2035":"linear-gradient(135deg,#00d4ff,#7c3aed)",border:"none",borderRadius:"10px",color:"#fff",padding:"12px 36px",fontSize:"1rem",fontWeight:"700",cursor:loading?"not-allowed":"pointer",flex:1}}
            >
              {loading ? "Evaluating all models..." : "⚡ Evaluate"}
            </button>
          </div>
          {error && <p style={{color:"#ff4444",marginTop:"12px"}}>{error}</p>}
        </div>

        {/* Results */}
        {results && (
          <>
            {/* Winner Banner */}
            <div style={{background:"linear-gradient(135deg,#00d4ff22,#7c3aed22)",border:"1px solid #00d4ff44",borderRadius:"12px",padding:"20px 28px",marginBottom:"32px",display:"flex",alignItems:"center",gap:"16px"}}>
              <span style={{fontSize:"2rem"}}>🏆</span>
              <div>
                <div style={{color:"#00d4ff",fontWeight:"700",fontSize:"1.2rem"}}>Recommended: {results.recommended_model}</div>
                <div style={{color:"#6b8fa8",marginTop:"4px"}}>{results.reasoning}</div>
              </div>
            </div>

            {/* Model Cards */}
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))",gap:"20px",marginBottom:"40px"}}>
              {results.results.map(r => (
                <div key={r.model_name} style={{background:"#0b1520",border:`1px solid ${r.winner?"#00d4ff":"#0f2035"}`,borderRadius:"16px",padding:"24px",position:"relative"}}>
                  {r.winner && <div style={{position:"absolute",top:"-12px",right:"20px",background:"linear-gradient(135deg,#00d4ff,#7c3aed)",borderRadius:"20px",padding:"4px 14px",fontSize:"0.8rem",fontWeight:"700"}}>WINNER</div>}
                  <h3 style={{margin:"0 0 16px",color:r.winner?"#00d4ff":"#e8f4ff",fontSize:"1.1rem"}}>{r.model_name}</h3>
                  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"12px",marginBottom:"16px"}}>
                    {[["Quality", r.quality_score + "/10"],["Latency", r.latency_ms + "ms"],["Tokens", r.tokens_used],["Cost/1k", "$" + r.cost_per_1k_tokens]].map(([label,val]) => (
                      <div key={label} style={{background:"#070d14",borderRadius:"8px",padding:"10px"}}>
                        <div style={{color:"#6b8fa8",fontSize:"0.75rem"}}>{label}</div>
                        <div style={{color:"#e8f4ff",fontWeight:"700",fontSize:"1.1rem"}}>{val}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{background:"#070d14",borderRadius:"8px",padding:"12px",maxHeight:"120px",overflowY:"auto"}}>
                    <p style={{margin:0,color:"#a0bcd0",fontSize:"0.85rem",lineHeight:"1.6"}}>{r.response.slice(0,300)}{r.response.length > 300 ? "..." : ""}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Charts */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"24px"}}>
              <div style={{background:"#0b1520",border:"1px solid #0f2035",borderRadius:"16px",padding:"24px"}}>
                <h3 style={{margin:"0 0 20px",color:"#00d4ff"}}>Quality Score</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData}>
                    <XAxis dataKey="name" tick={{fill:"#6b8fa8",fontSize:11}} />
                    <YAxis domain={[0,10]} tick={{fill:"#6b8fa8",fontSize:11}} />
                    <Tooltip contentStyle={{background:"#0b1520",border:"1px solid #0f2035",color:"#e8f4ff"}} />
                    <Bar dataKey="Quality" fill="#00d4ff" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{background:"#0b1520",border:"1px solid #0f2035",borderRadius:"16px",padding:"24px"}}>
                <h3 style={{margin:"0 0 20px",color:"#7c3aed"}}>Latency (ms)</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData}>
                    <XAxis dataKey="name" tick={{fill:"#6b8fa8",fontSize:11}} />
                    <YAxis tick={{fill:"#6b8fa8",fontSize:11}} />
                    <Tooltip contentStyle={{background:"#0b1520",border:"1px solid #0f2035",color:"#e8f4ff"}} />
                    <Bar dataKey="Latency" fill="#7c3aed" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
