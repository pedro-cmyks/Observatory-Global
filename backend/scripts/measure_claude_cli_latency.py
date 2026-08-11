#!/usr/bin/env python3
"""Measure claude CLI headless latency for label-court-style prompts (M1).

2026-07-28 first run: the live CLI leg was BLOCKED — every `claude -p` returned
401 "OAuth access token has expired. Re-authenticate to continue." (refresh
token dead; `claude auth status` still says loggedIn). AFTER Pedro runs
`claude auth login` on the M1, re-run:

  python3 backend/scripts/measure_claude_cli_latency.py single
  python3 backend/scripts/measure_claude_cli_latency.py batch 50 haiku
  DEEPSEEK_API_KEY=... python3 backend/scripts/measure_claude_cli_latency.py deepseek 10

Findings that survive the auth blocker (see docs/research/claude-cli-leg/):
  - `--bare` NEVER reads keychain OAuth (always "Not logged in") — the wired
    leg uses --safe-mode instead (auth works, hooks/plugins skipped).
  - DeepSeek baseline on the same judge prompt: p50 1.49s / p95 1.66s (n=10).
  - CLI process overhead alone: ~1.5s wall idle, 14-27s at load-40 (the
    nightly scoped-snapshot regime), user CPU ~0.9s — pure spawn cost.

Usage:
  single          # one call per config (default model / haiku / haiku-bare / sonnet)
  batch N MODEL [bare]   # N sequential calls; watch for cap-error shapes
  deepseek N      # N DeepSeek calls, same prompt (needs DEEPSEEK_API_KEY)
"""
import json
import os
import statistics
import subprocess
import sys
import time

# Real label-court-shape prompt: label + 12 headlines (~160c), JSON verdict ask.
LABEL = "Berlin Pride Parade Restrictions"
HEADLINES = [
    "Berlin police restrict route of annual Pride parade citing security concerns",
    "Thousands march in Berlin Pride despite new route restrictions",
    "Berlin senator defends decision to shorten CSD parade route",
    "LGBTQ groups protest Berlin parade restrictions outside city hall",
    "Pride organizers say Berlin restrictions set dangerous precedent",
    "Berlin CSD 2026: what changed and why, organizers respond",
    "German capital tightens security for weekend Pride events",
    "Counter-demonstration announced along revised Berlin Pride route",
    "Berlin Pride draws 200,000 despite route dispute with police",
    "City officials meet Pride organizers after route controversy",
    "Opposition parties criticize Berlin senate over parade decision",
    "Berlin Pride ends peacefully; organizers vow legal challenge to route limits",
]

PROMPT = (
    "You are a strict fact-checker auditing a news-cluster LABEL against the "
    "actual headlines assigned to it.\n\n"
    f'LABEL: "{LABEL}"\n\nHEADLINES:\n'
    + "\n".join(f"- {h}" for h in HEADLINES)
    + "\n\nDoes the LABEL accurately describe the MAJORITY of these headlines? "
    "Judge on subject and geography, not vibe. Reply ONLY with JSON:\n"
    '{"verdict": "entailed" | "partial" | "failed", "reason": "<one short sentence>"}\n'
    "- entailed: the label fits most headlines.\n"
    "- partial: the label fits some but a large minority are off-topic.\n"
    "- failed: the label does NOT describe most headlines (wrong subject or wrong country).")


def run_cli(extra_args, timeout=120):
    cmd = ["claude", "-p", PROMPT, "--output-format", "json",
           "--no-session-persistence"] + extra_args
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"wall_s": time.monotonic() - t0, "error": "timeout"}
    wall = time.monotonic() - t0
    out = {"wall_s": wall, "rc": proc.returncode}
    if proc.returncode != 0:
        out["stderr"] = (proc.stderr or "")[:400]
        out["stdout"] = (proc.stdout or "")[:400]
        return out
    try:
        payload = json.loads(proc.stdout)
        out["result"] = (payload.get("result") or "")[:200]
        out["is_error"] = payload.get("is_error")
        out["duration_api_ms"] = payload.get("duration_api_ms")
        out["cost_usd"] = payload.get("total_cost_usd")
        out["model"] = (payload.get("modelUsage") and list(payload["modelUsage"].keys())) or None
    except (json.JSONDecodeError, ValueError):
        out["raw"] = proc.stdout[:400]
    return out


def stats(times):
    s = sorted(times)
    return {
        "n": len(s),
        "p50": round(statistics.median(s), 2),
        "p95": round(s[max(0, int(len(s) * 0.95) - 1)], 2) if len(s) > 1 else round(s[0], 2),
        "min": round(s[0], 2),
        "max": round(s[-1], 2),
        "mean": round(statistics.mean(s), 2),
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "single"
    if mode == "single":
        configs = [
            ("default-model", []),
            ("haiku", ["--model", "haiku"]),
            ("haiku-bare", ["--model", "haiku", "--bare"]),
            ("sonnet", ["--model", "sonnet"]),
        ]
        for name, args in configs:
            r = run_cli(args)
            print(json.dumps({"config": name, **r}), flush=True)
    elif mode == "batch":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        model = sys.argv[3] if len(sys.argv) > 3 else "haiku"
        extra = ["--model", model]
        if len(sys.argv) > 4 and sys.argv[4] == "bare":
            extra.append("--bare")
        times, errors = [], []
        t_start = time.monotonic()
        for i in range(n):
            r = run_cli(extra)
            ok = r.get("rc") == 0 and not r.get("is_error") and "result" in r
            if ok:
                times.append(r["wall_s"])
            else:
                errors.append({"i": i, **{k: r.get(k) for k in ("rc", "stderr", "stdout", "error", "result", "is_error")}})
            print(json.dumps({"i": i, "wall_s": round(r["wall_s"], 2),
                              "ok": ok, "verdict_snip": (r.get("result") or "")[:60]}),
                  flush=True)
        elapsed = time.monotonic() - t_start
        print(json.dumps({
            "SUMMARY": True, "model": model, "ok": len(times), "err": len(errors),
            "stats_s": stats(times) if times else None,
            "elapsed_min": round(elapsed / 60, 2),
            "calls_per_min": round(len(times) / (elapsed / 60), 2) if times else 0,
            "errors": errors[:5],
        }, indent=2), flush=True)
    elif mode == "deepseek":
        import urllib.request
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        key = os.environ["DEEPSEEK_API_KEY"]
        times, errors = [], []
        for i in range(n):
            body = json.dumps({"model": "deepseek-chat", "temperature": 0,
                               "messages": [{"role": "user", "content": PROMPT}]}).encode()
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"})
            t0 = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = json.loads(resp.read())
                wall = time.monotonic() - t0
                times.append(wall)
                snip = payload["choices"][0]["message"]["content"][:60]
                print(json.dumps({"i": i, "wall_s": round(wall, 2), "snip": snip}), flush=True)
            except Exception as e:
                errors.append(str(e)[:200])
                print(json.dumps({"i": i, "error": str(e)[:200]}), flush=True)
        print(json.dumps({"SUMMARY": True, "provider": "deepseek",
                          "ok": len(times), "err": len(errors),
                          "stats_s": stats(times) if times else None}, indent=2), flush=True)


if __name__ == "__main__":
    main()
