from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


def calculate_percentile(data: list[float | int], percentile: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_data[int(k)])
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return round(float(d0 + d1), 2)


def get_dashboard_metrics(time_range_minutes: int = 60) -> dict[str, Any]:
    if not LOG_PATH.exists():
        records: list[dict[str, Any]] = []
    else:
        raw_lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
        records = []
        for line in raw_lines:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue

    now = datetime.now(timezone.utc)

    filtered_records = records

    # Panel 1: Latency & TTFT
    latencies = [r["latency_ms"] for r in filtered_records if r.get("event") == "response_sent" and "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in filtered_records if r.get("event") == "response_sent" and "ttft_ms" in r]

    latency_p50 = calculate_percentile(latencies, 50)
    latency_p95 = calculate_percentile(latencies, 95)
    latency_p99 = calculate_percentile(latencies, 99)
    ttft_p95 = calculate_percentile(ttfts, 95)

    # Panel 2: Traffic
    request_received = [r for r in filtered_records if r.get("event") == "request_received"]
    total_requests = len(request_received)
    rpm = round(total_requests / max(1.0, time_range_minutes), 2)

    # Panel 3: Errors
    request_failed = [r for r in filtered_records if r.get("event") == "request_failed"]
    total_failed = len(request_failed)
    error_rate_pct = round((total_failed / max(1, total_requests)) * 100, 2)

    error_types: dict[str, int] = {}
    for r in request_failed:
        err = r.get("error_type", "UnknownError")
        error_types[err] = error_types.get(err, 0) + 1

    tool_events = [r for r in filtered_records if r.get("tool_success") is not None]
    tool_success_count = sum(1 for r in tool_events if r.get("tool_success") is True)
    tool_success_rate_pct = round((tool_success_count / max(1, len(tool_events))) * 100, 2) if tool_events else 100.0

    # Panel 4: Cost
    cost_records = [r["cost_usd"] for r in filtered_records if r.get("event") == "response_sent" and "cost_usd" in r]
    total_cost_usd = round(sum(cost_records), 6)

    # Panel 5: Tokens
    tokens_in = sum(r.get("tokens_in", 0) for r in filtered_records if r.get("event") == "response_sent")
    tokens_out = sum(r.get("tokens_out", 0) for r in filtered_records if r.get("event") == "response_sent")
    total_tokens = tokens_in + tokens_out

    # Panel 6: Quality
    quality_scores = [r["quality_score"] for r in filtered_records if r.get("event") == "response_sent" and "quality_score" in r]
    mean_quality = round(sum(quality_scores) / max(1, len(quality_scores)), 3) if quality_scores else 0.0

    # Timeline buckets for charts
    timeline: list[dict[str, Any]] = []
    resp_count = 0
    running_cost = 0.0
    for idx, r in enumerate(filtered_records):
        if r.get("event") == "response_sent":
            resp_count += 1
            running_cost += r.get("cost_usd", 0.0)
            timeline.append({
                "index": resp_count,
                "ts": r.get("ts", "")[-12:-4] if r.get("ts") else f"#{resp_count}",
                "latency_ms": r.get("latency_ms", 0),
                "ttft_ms": r.get("ttft_ms", 0),
                "cost_usd": round(running_cost, 5),
                "tokens_in": r.get("tokens_in", 0),
                "tokens_out": r.get("tokens_out", 0),
                "quality_score": r.get("quality_score", 0.0),
            })

    return {
        "title": "K4-L3B Day 13 Monitoring & LLMOps",
        "time_range_minutes": time_range_minutes,
        "refresh_seconds": 30,
        "total_records": len(filtered_records),
        "panels": {
            "latency": {
                "id": "latency",
                "title": "Latency percentiles and TTFT",
                "unit": "ms",
                "p50": latency_p50,
                "p95": latency_p95,
                "p99": latency_p99,
                "ttft_p95": ttft_p95,
                "threshold": {"operator": "lte", "value": 3000, "status": "PASS" if latency_p95 <= 3000 else "ALERT"},
            },
            "traffic": {
                "id": "traffic",
                "title": "Request traffic",
                "unit": "requests_per_minute",
                "count": total_requests,
                "rate_per_minute": rpm,
                "threshold": {"operator": "gte", "value": 1, "status": "PASS" if total_requests >= 1 else "ALERT"},
            },
            "errors": {
                "id": "errors",
                "title": "Error rate and retrieval success",
                "unit": "percent",
                "error_rate_pct": error_rate_pct,
                "error_types": error_types,
                "tool_success_rate_pct": tool_success_rate_pct,
                "threshold": {"operator": "lte", "value": 2.0, "status": "PASS" if error_rate_pct <= 2.0 else "ALERT"},
            },
            "cost": {
                "id": "cost",
                "title": "Cost over time",
                "unit": "usd",
                "total": total_cost_usd,
                "threshold": {"operator": "lte", "value": 2.5, "status": "PASS" if total_cost_usd <= 2.5 else "ALERT"},
            },
            "tokens": {
                "id": "tokens",
                "title": "Input and output tokens",
                "unit": "tokens",
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total": total_tokens,
                "threshold": {"operator": "lte", "value": 50000, "status": "PASS" if total_tokens <= 50000 else "ALERT"},
            },
            "quality": {
                "id": "quality",
                "title": "Quality proxy",
                "unit": "score_0_to_1",
                "mean": mean_quality,
                "threshold": {"operator": "gte", "value": 0.75, "status": "PASS" if mean_quality >= 0.75 else "ALERT"},
            },
        },
        "timeline": timeline,
    }


def render_dashboard_html() -> str:
    data = get_dashboard_metrics()
    p = data["panels"]
    t = data["timeline"]

    labels_json = json.dumps([item["ts"] for item in t])
    latency_json = json.dumps([item["latency_ms"] for item in t])
    ttft_json = json.dumps([item["ttft_ms"] for item in t])
    cost_json = json.dumps([item["cost_usd"] for item in t])
    tokens_in_json = json.dumps([item["tokens_in"] for item in t])
    tokens_out_json = json.dumps([item["tokens_out"] for item in t])
    quality_json = json.dumps([item["quality_score"] for item in t])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <title>K4-L3B Day 13 Monitoring & LLMOps Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background: #0f172a; color: #f8fafc; padding: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid #334155; padding-bottom: 16px; }}
        .header h1 {{ font-size: 24px; font-weight: 700; color: #38bdf8; }}
        .meta-badges {{ display: flex; gap: 12px; }}
        .badge {{ background: #1e293b; padding: 6px 14px; border-radius: 9999px; font-size: 13px; border: 1px solid #475569; }}
        .badge strong {{ color: #38bdf8; }}
        .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        @media (max-width: 1200px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        .panel {{ background: #1e293b; border-radius: 12px; padding: 18px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); display: flex; flex-direction: column; }}
        .panel-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
        .panel-title {{ font-size: 15px; font-weight: 600; color: #e2e8f0; }}
        .panel-unit {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metrics-summary {{ display: flex; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }}
        .metric-item {{ display: flex; flex-direction: column; }}
        .metric-label {{ font-size: 11px; color: #94a3b8; }}
        .metric-val {{ font-size: 22px; font-weight: 700; color: #f8fafc; }}
        .threshold-pill {{ font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 600; margin-top: 4px; display: inline-block; }}
        .pass {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }}
        .alert {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
        .chart-box {{ height: 160px; position: relative; width: 100%; margin-top: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>K4-L3B Day 13 Monitoring & LLMOps</h1>
            <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Contract: config/dashboard.yaml | Data: data/logs.jsonl | Student: Võ Trường An (2A202602656)</p>
        </div>
        <div class="meta-badges">
            <div class="badge">Time Range: <strong>60 min</strong></div>
            <div class="badge">Auto Refresh: <strong>30s</strong></div>
            <div class="badge">Records: <strong>{data['total_records']}</strong></div>
        </div>
    </div>

    <div class="grid">
        <!-- Panel 1: Latency -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <div class="panel-title">1. Latency & TTFT</div>
                    <div class="panel-unit">Unit: ms</div>
                </div>
                <div class="threshold-pill {p['latency']['threshold']['status'].lower()}">
                    Threshold: P95 &le; 3000ms ({p['latency']['threshold']['status']})
                </div>
            </div>
            <div class="metrics-summary">
                <div class="metric-item"><span class="metric-label">P50</span><span class="metric-val">{p['latency']['p50']}ms</span></div>
                <div class="metric-item"><span class="metric-label">P95</span><span class="metric-val" style="color: #38bdf8;">{p['latency']['p95']}ms</span></div>
                <div class="metric-item"><span class="metric-label">P99</span><span class="metric-val">{p['latency']['p99']}ms</span></div>
                <div class="metric-item"><span class="metric-label">TTFT P95</span><span class="metric-val">{p['latency']['ttft_p95']}ms</span></div>
            </div>
            <div class="chart-box"><canvas id="chartLatency"></canvas></div>
        </div>

        <!-- Panel 2: Traffic -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <div class="panel-title">2. Request Traffic</div>
                    <div class="panel-unit">Unit: requests / min</div>
                </div>
                <div class="threshold-pill {p['traffic']['threshold']['status'].lower()}">
                    Threshold: Rate &ge; 1 req/min ({p['traffic']['threshold']['status']})
                </div>
            </div>
            <div class="metrics-summary">
                <div class="metric-item"><span class="metric-label">Total Requests</span><span class="metric-val" style="color: #38bdf8;">{p['traffic']['count']}</span></div>
                <div class="metric-item"><span class="metric-label">Throughput</span><span class="metric-val">{p['traffic']['rate_per_minute']} /m</span></div>
            </div>
            <div class="chart-box"><canvas id="chartTraffic"></canvas></div>
        </div>

        <!-- Panel 3: Errors -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <div class="panel-title">3. Error Rate & Retrieval</div>
                    <div class="panel-unit">Unit: %</div>
                </div>
                <div class="threshold-pill {p['errors']['threshold']['status'].lower()}">
                    Threshold: Error &le; 2.0% ({p['errors']['threshold']['status']})
                </div>
            </div>
            <div class="metrics-summary">
                <div class="metric-item"><span class="metric-label">Error Rate</span><span class="metric-val" style="color: {'#4ade80' if p['errors']['error_rate_pct'] <= 2.0 else '#f87171'};">{p['errors']['error_rate_pct']}%</span></div>
                <div class="metric-item"><span class="metric-label">Retrieval Success</span><span class="metric-val" style="color: #38bdf8;">{p['errors']['tool_success_rate_pct']}%</span></div>
            </div>
            <div class="chart-box"><canvas id="chartErrors"></canvas></div>
        </div>

        <!-- Panel 4: Cost -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <div class="panel-title">4. Cost Over Time</div>
                    <div class="panel-unit">Unit: USD</div>
                </div>
                <div class="threshold-pill {p['cost']['threshold']['status'].lower()}">
                    Threshold: Total &le; $2.50 ({p['cost']['threshold']['status']})
                </div>
            </div>
            <div class="metrics-summary">
                <div class="metric-item"><span class="metric-label">Total Cost</span><span class="metric-val" style="color: #38bdf8;">${p['cost']['total']}</span></div>
            </div>
            <div class="chart-box"><canvas id="chartCost"></canvas></div>
        </div>

        <!-- Panel 5: Tokens -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <div class="panel-title">5. Input & Output Tokens</div>
                    <div class="panel-unit">Unit: tokens</div>
                </div>
                <div class="threshold-pill {p['tokens']['threshold']['status'].lower()}">
                    Threshold: Total &le; 50,000 ({p['tokens']['threshold']['status']})
                </div>
            </div>
            <div class="metrics-summary">
                <div class="metric-item"><span class="metric-label">Tokens In</span><span class="metric-val">{p['tokens']['tokens_in']}</span></div>
                <div class="metric-item"><span class="metric-label">Tokens Out</span><span class="metric-val">{p['tokens']['tokens_out']}</span></div>
                <div class="metric-item"><span class="metric-label">Total</span><span class="metric-val" style="color: #38bdf8;">{p['tokens']['total']}</span></div>
            </div>
            <div class="chart-box"><canvas id="chartTokens"></canvas></div>
        </div>

        <!-- Panel 6: Quality -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <div class="panel-title">6. Quality Proxy</div>
                    <div class="panel-unit">Unit: score (0 to 1)</div>
                </div>
                <div class="threshold-pill {p['quality']['threshold']['status'].lower()}">
                    Threshold: Mean &ge; 0.75 ({p['quality']['threshold']['status']})
                </div>
            </div>
            <div class="metrics-summary">
                <div class="metric-item"><span class="metric-label">Mean Quality</span><span class="metric-val" style="color: {'#4ade80' if p['quality']['mean'] >= 0.75 else '#f87171'};">{p['quality']['mean']}</span></div>
            </div>
            <div class="chart-box"><canvas id="chartQuality"></canvas></div>
        </div>
    </div>

    <script>
        const labels = {labels_json};
        const defaultChartOptions = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 10 }} }} }} }},
            scales: {{
                x: {{ ticks: {{ color: '#64748b', font: {{ size: 9 }} }}, grid: {{ color: '#334155' }} }},
                y: {{ ticks: {{ color: '#64748b', font: {{ size: 9 }} }}, grid: {{ color: '#334155' }} }}
            }}
        }};

        // Chart 1: Latency
        new Chart(document.getElementById('chartLatency'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Latency (ms)', data: {latency_json}, borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)', tension: 0.3, fill: true }},
                    {{ label: 'TTFT (ms)', data: {ttft_json}, borderColor: '#a855f7', tension: 0.3 }}
                ]
            }},
            options: defaultChartOptions
        }});

        // Chart 2: Traffic
        new Chart(document.getElementById('chartTraffic'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Requests', data: labels.map(() => 1), backgroundColor: '#38bdf8' }}]
            }},
            options: defaultChartOptions
        }});

        // Chart 3: Errors
        new Chart(document.getElementById('chartErrors'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Retrieval Success %', data: labels.map(() => {p['errors']['tool_success_rate_pct']}), borderColor: '#4ade80', tension: 0.1 }}]
            }},
            options: {{ ...defaultChartOptions, scales: {{ ...defaultChartOptions.scales, y: {{ min: 0, max: 105, ticks: {{ color: '#64748b' }}, grid: {{ color: '#334155' }} }} }} }}
        }});

        // Chart 4: Cost
        new Chart(document.getElementById('chartCost'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Cumulative Cost ($)', data: {cost_json}, borderColor: '#fbbf24', tension: 0.3, fill: true, backgroundColor: 'rgba(251, 191, 36, 0.1)' }}]
            }},
            options: defaultChartOptions
        }});

        // Chart 5: Tokens
        new Chart(document.getElementById('chartTokens'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'In', data: {tokens_in_json}, backgroundColor: '#60a5fa' }},
                    {{ label: 'Out', data: {tokens_out_json}, backgroundColor: '#f472b6' }}
                ]
            }},
            options: {{ ...defaultChartOptions, scales: {{ ...defaultChartOptions.scales, x: {{ stacked: true }}, y: {{ stacked: true }} }} }}
        }});

        // Chart 6: Quality
        new Chart(document.getElementById('chartQuality'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Quality Score', data: {quality_json}, borderColor: '#4ade80', tension: 0.3 }}]
            }},
            options: {{ ...defaultChartOptions, scales: {{ ...defaultChartOptions.scales, y: {{ min: 0, max: 1.0, ticks: {{ color: '#64748b' }}, grid: {{ color: '#334155' }} }} }} }}
        }});
    </script>
</body>
</html>
"""
