import { useState } from "react"
import axios from "axios"
import "./App.css"

const COLORS = ['#9b8fd0', '#e8a87c', '#6dbfa8']

function sname(n) {
  if (!n) return n

  const l = n.toLowerCase()

  if (l.includes('70b')) return 'LLaMA 70B'
  if (l.includes('8b')) return 'LLaMA 8B'
  if (l.includes('gemini')) return 'Gemini'

  return n.split('/').pop().split('-').slice(0, 2).join('-')
}

export default function App() {
  const [prompt, setPrompt] = useState("")
  const [task, setTask] = useState("general")
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const evaluate = async () => {
    if (!prompt.trim()) return

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const res = await axios.post(
        "https://llm-eval-framework-2.onrender.com/evaluate",
        {
          prompt,
          task_type: task
        }
      )

      setResults(res.data)
    } catch (e) {
      setError(
        `Backend unreachable — make sure it's running. (${e.message})`
      )
    }

    setLoading(false)
  }

  const validResults =
    results?.results?.filter(
      (r) =>
        r.response &&
        !r.response.toLowerCase().includes("error") &&
        !r.response.toLowerCase().includes("quota") &&
        !r.response.toLowerCase().includes("invalid api key")
    ) || []

  const bestModel =
    validResults.length > 0
      ? [...validResults].sort(
          (a, b) => b.quality_score - a.quality_score
        )[0]
      : null

  const cd =
    results?.results?.map((r, i) => ({
      name: sname(r.model_name),
      model_name: r.model_name,
      color: COLORS[i % 3],
      quality: r.quality_score || 0,
      latency: r.latency_ms || 0,
      tokens: r.tokens_used || 0,
      cost: r.cost_per_1k_tokens || 0,
      winner: bestModel?.model_name === r.model_name,
      response: r.response || '',
      failed:
        r.response?.toLowerCase().includes("error") ||
        r.response?.toLowerCase().includes("quota") ||
        r.response?.toLowerCase().includes("invalid api key")
    })) || []

  const maxLat = Math.max(...cd.map(d => d.latency), 1)

  const TASKS = [
    "general",
    "coding",
    "creative",
    "analysis",
    "reasoning"
  ]

  return (
    <div className="root">
      <div className="shell">

        {/* Top bar */}
        <div className="topbar">
          <div className="topbar-orb">
            <span className="orb-icon">⚙</span>
          </div>

          <div>
            <div className="topbar-title">
              LLM Eval Framework
            </div>

            <div className="topbar-sub">
              llama-70b · llama-8b · gemini-flash
            </div>
          </div>

          <div className="topbar-dots">
            <div className="dot dot-r" />
            <div className="dot dot-y" />
            <div className="dot dot-g" />
          </div>
        </div>

        {/* Body */}
        <div className="body">

          <div className="section-label">
            Prompt
          </div>

          <div className="prompt-wrap">
            <div className="prompt-inner">

              <textarea
                className="pinput"
                placeholder="enter your prompt here..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
              />

              <div className="controls">

                <div className="chip-row">
                  {TASKS.map((t) => (
                    <button
                      key={t}
                      className={`chip${task === t ? ' active' : ''}`}
                      onClick={() => setTask(t)}
                    >
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                  ))}
                </div>

                <button
                  className="evalbtn"
                  disabled={loading || !prompt.trim()}
                  onClick={evaluate}
                >
                  <span
                    className={`pdot${loading ? ' spin-on' : ''}`}
                  />

                  {loading
                    ? 'Evaluating...'
                    : 'Evaluate'}
                </button>

              </div>
            </div>
          </div>

          {error && (
            <div className="err">
              ⚠ {error}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="loading-wrap">

              <div className="lring" />

              <div className="ltxt">
                Evaluating all models in parallel...
              </div>

              <div className="lmodels">
                {['LLaMA 70B', 'LLaMA 8B', 'Gemini'].map((n) => (
                  <div className="lm" key={n}>
                    <div className="lmname">{n}</div>
                    <div className="sring" />
                  </div>
                ))}
              </div>

            </div>
          )}

          {/* Results */}
          {results && !loading && (
            <div className="results">

              {/* Winner */}
              <div className="winner-card">

                <div className="winner-orb">
                  🏆
                </div>

                <div>

                  <div className="winner-tag">
                    Recommended model
                  </div>

                  <div className="winner-name">
                    {bestModel
                      ? sname(bestModel.model_name)
                      : "No valid model"}
                  </div>

                  <div className="winner-reason">
                    {bestModel
                      ? "Best successful response based on quality score"
                      : "All model providers failed"}
                  </div>

                </div>
              </div>

              {/* Model cards */}
              <div className="models-grid">

                {cd.map((m) => (
                  <div
                    className={`mcard${m.winner ? ' best' : ''}`}
                    key={m.name}
                  >

                    {m.winner && (
                      <div className="mbadge">
                        Winner
                      </div>
                    )}

                    <div className="mname">
                      {m.name}
                    </div>

                    <div className="qbar-row">
                      <span>Quality</span>
                      <span>{m.quality}/10</span>
                    </div>

                    <div className="qbar-bg">
                      <div
                        className="qbar-fill"
                        style={{
                          width: `${m.quality * 10}%`,
                          background: m.color
                        }}
                      />
                    </div>

                    <div className="sgrid">

                      <div className="scell">
                        <div className="slabel">
                          Latency
                        </div>

                        <div className="sval">
                          {m.latency}ms
                        </div>
                      </div>

                      <div className="scell">
                        <div className="slabel">
                          Tokens
                        </div>

                        <div className="sval">
                          {m.tokens}
                        </div>
                      </div>

                      <div className="scell scell-full">
                        <div className="slabel">
                          Cost / 1k tokens
                        </div>

                        <div className="sval">
                          ${Number(m.cost).toFixed(4)}
                        </div>
                      </div>

                    </div>

                    <div
                      className={`snippet ${m.failed ? 'failed' : ''}`}
                    >
                      {m.response.slice(0, 200)}
                    </div>

                  </div>
                ))}

              </div>

              {/* Charts */}
              <div className="charts-row">

                <div className="cchart">

                  <div className="ctitle">
                    Quality score
                  </div>

                  <div className="bar-area">

                    {cd.map((m) => (
                      <div className="bgroup" key={m.name}>

                        <div className="bval">
                          {m.quality}
                        </div>

                        <div
                          className="bfill"
                          style={{
                            height: `${m.quality * 10}%`,
                            background: m.color
                          }}
                        />

                        <div className="bname">
                          {m.name.split(' ').slice(-1)[0]}
                        </div>

                      </div>
                    ))}

                  </div>
                </div>

                <div className="cchart">

                  <div className="ctitle">
                    Latency (ms)
                  </div>

                  <div className="bar-area">

                    {cd.map((m) => (
                      <div className="bgroup" key={m.name}>

                        <div className="bval">
                          {m.latency}
                        </div>

                        <div
                          className="bfill"
                          style={{
                            height: `${Math.max(
                              (m.latency / maxLat) * 100,
                              4
                            )}%`,
                            background: m.color
                          }}
                        />

                        <div className="bname">
                          {m.name.split(' ').slice(-1)[0]}
                        </div>

                      </div>
                    ))}

                  </div>
                </div>

              </div>

            </div>
          )}

        </div>
      </div>
    </div>
  )
}
