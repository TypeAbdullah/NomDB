from __future__ import annotations
import argparse
import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from nomdb.client.client import Client
from nomdb.protocol.exceptions import NomDBError

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NomDB Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(22, 30, 49, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --accent: #06b6d4;
      --success: #10b981;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-dim: #9ca3af;
      --sidebar-w: 320px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      height: 100vh;
      overflow: hidden;
      background-image: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                        radial-gradient(circle at 90% 80%, rgba(6, 182, 212, 0.08) 0%, transparent 40%);
    }
    #sidebar {
      width: var(--sidebar-w);
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border-right: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .brand {
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid var(--card-border);
    }
    .brand-logo {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      border-radius: 8px;
      display: grid;
      place-items: center;
      font-weight: 700;
      color: #fff;
    }
    .brand h1 { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.5px; }
    .brand span { font-size: 0.75rem; color: var(--accent); background: rgba(6,182,212,0.15); padding: 2px 6px; border-radius: 4px; margin-left: auto; }
    .search-box { padding: 14px 16px; border-bottom: 1px solid var(--card-border); }
    .search-input {
      width: 100%;
      padding: 9px 12px;
      background: rgba(11, 15, 25, 0.8);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: #fff;
      font-size: 0.85rem;
      outline: none;
    }
    .search-input:focus { border-color: var(--primary); }
    .keys-header {
      padding: 10px 16px;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      display: flex;
      justify-content: space-between;
    }
    #key-list {
      flex: 1;
      overflow-y: auto;
      list-style: none;
    }
    .key-item {
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255,255,255,0.03);
      cursor: pointer;
      transition: all 0.15s;
    }
    .key-item:hover { background: rgba(99, 102, 241, 0.1); }
    .key-item.active { background: rgba(99, 102, 241, 0.2); border-left: 3px solid var(--primary); }
    .key-name { font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
    .badge {
      font-size: 0.65rem;
      font-weight: 600;
      text-transform: uppercase;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .badge-string { background: rgba(99, 102, 241, 0.2); color: #818cf8; }
    .badge-hash { background: rgba(236, 72, 153, 0.2); color: #f472b6; }
    .badge-list { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
    .badge-set { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .badge-zset { background: rgba(6, 182, 212, 0.2); color: #22d3ee; }

    #main {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
    }
    .topbar {
      padding: 16px 24px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-bg);
      backdrop-filter: blur(16px);
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      padding: 24px;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
      backdrop-filter: blur(10px);
    }
    .stat-title { font-size: 0.75rem; text-transform: uppercase; color: var(--text-dim); margin-bottom: 6px; }
    .stat-value { font-size: 1.4rem; font-weight: 700; color: #fff; }

    .content-area {
      flex: 1;
      padding: 0 24px 24px 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 20px;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .card-title { font-size: 1.05rem; font-weight: 600; }
    .btn {
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn:hover { background: var(--primary-hover); }
    .btn-danger { background: var(--danger); }
    .btn-danger:hover { background: #dc2626; }
    .btn-secondary { background: rgba(255,255,255,0.08); }
    .btn-secondary:hover { background: rgba(255,255,255,0.15); }

    .value-viewer {
      background: rgba(11, 15, 25, 0.9);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.88rem;
      overflow-x: auto;
      max-height: 380px;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
    th { color: var(--text-dim); font-size: 0.75rem; text-transform: uppercase; }

    .console-input-row { display: flex; gap: 10px; margin-top: 12px; }
    .console-input {
      flex: 1;
      padding: 10px 14px;
      background: rgba(11, 15, 25, 0.9);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: #fff;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.9rem;
      outline: none;
    }
    .console-out {
      margin-top: 12px;
      padding: 12px;
      background: rgba(0,0,0,0.5);
      border-radius: 6px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      max-height: 180px;
      overflow-y: auto;
      white-space: pre-wrap;
    }

    /* Modal */
    .modal-backdrop {
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
      display: none; place-items: center; z-index: 100;
    }
    .modal {
      background: #131b2e;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
      width: 480px;
      max-width: 90vw;
    }
    .modal h2 { font-size: 1.15rem; margin-bottom: 16px; }
    .form-group { margin-bottom: 14px; }
    .form-label { display: block; font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; margin-bottom: 6px; }
    .form-control {
      width: 100%; padding: 9px 12px; background: rgba(11, 15, 25, 0.8);
      border: 1px solid var(--card-border); border-radius: 6px; color: #fff; font-size: 0.85rem; outline: none;
    }
    .modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
  </style>
</head>
<body>

  <!-- Sidebar -->
  <div id="sidebar">
    <div class="brand">
      <div class="brand-logo">N</div>
      <h1>NomDB</h1>
      <span>v1.0</span>
    </div>
    <div class="search-box">
      <input type="text" id="search" class="search-input" placeholder="Search keys (e.g. user:*)" oninput="filterKeys()">
    </div>
    <div class="keys-header">
      <span>Keyspace (<span id="key-count">0</span>)</span>
      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.7rem;" onclick="loadKeys()">Refresh</button>
    </div>
    <ul id="key-list"></ul>
  </div>

  <!-- Main Content -->
  <div id="main">
    <div class="topbar">
      <h2 id="topbar-title">Overview</h2>
      <div style="display: flex; gap: 10px;">
        <button class="btn" onclick="openCreateModal()">+ Add Key</button>
        <button class="btn btn-secondary" onclick="loadStats()">Refresh Stats</button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-title">Total Keys</div>
        <div class="stat-value" id="stat-keys">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Memory Used</div>
        <div class="stat-value" id="stat-mem">0.00 M</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Ops / Sec</div>
        <div class="stat-value" id="stat-ops">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Uptime</div>
        <div class="stat-value" id="stat-uptime">0s</div>
      </div>
    </div>

    <div class="content-area">
      <!-- Key Inspector -->
      <div class="card" id="key-inspector" style="display: none;">
        <div class="card-header">
          <div>
            <span class="card-title" id="inspect-key-name"></span>
            <span class="badge" id="inspect-type-badge" style="margin-left: 10px;"></span>
            <span style="font-size: 0.8rem; color: var(--text-dim); margin-left: 10px;">TTL: <span id="inspect-ttl">-1</span>s</span>
          </div>
          <button class="btn btn-danger" onclick="deleteCurrentKey()">Delete Key</button>
        </div>
        <div class="value-viewer" id="inspect-value"></div>
      </div>

      <!-- Console / Query Runner -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Console & Query Runner</span>
        </div>
        <div class="console-input-row">
          <input type="text" id="console-cmd" class="console-input" placeholder="Enter command e.g. GET user:1, HGETALL profile, DBSIZE" onkeydown="if(event.key==='Enter') runQuery()">
          <button class="btn" onclick="runQuery()">Execute</button>
        </div>
        <div class="console-out" id="console-result">Ready. Enter any NomDB / Redis command above.</div>
      </div>
    </div>
  </div>

  <!-- Create Key Modal -->
  <div class="modal-backdrop" id="create-modal">
    <div class="modal">
      <h2>Add New Key</h2>
      <div class="form-group">
        <label class="form-label">Key Name</label>
        <input type="text" id="new-key-name" class="form-control" placeholder="e.g. user:100">
      </div>
      <div class="form-group">
        <label class="form-label">Data Type</label>
        <select id="new-key-type" class="form-control" onchange="toggleTypeInputs()">
          <option value="string">String</option>
          <option value="hash">Hash (JSON/Key-Value)</option>
          <option value="list">List (Comma separated)</option>
          <option value="set">Set (Comma separated)</option>
          <option value="zset">Sorted Set (score:member, ...)</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Value</label>
        <textarea id="new-key-value" class="form-control" rows="4" placeholder="Value content"></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">TTL in Seconds (Optional)</label>
        <input type="number" id="new-key-ttl" class="form-control" placeholder="e.g. 3600">
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick="closeCreateModal()">Cancel</button>
        <button class="btn" onclick="submitCreateKey()">Save Key</button>
      </div>
    </div>
  </div>

  <script>
    let allKeys = [];
    let currentKey = null;

    async function loadStats() {
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-keys').innerText = data.total_keys || 0;
        document.getElementById('stat-mem').innerText = data.used_memory_human || '0.00M';
        document.getElementById('stat-ops').innerText = data.instantaneous_ops_per_sec || 0;
        document.getElementById('stat-uptime').innerText = (data.uptime_in_seconds || 0) + 's';
      } catch (e) {
        console.error("Stats load error:", e);
      }
    }

    async function loadKeys() {
      try {
        const res = await fetch('/api/keys');
        allKeys = await res.json();
        document.getElementById('key-count').innerText = allKeys.length;
        renderKeys(allKeys);
      } catch (e) {
        console.error("Keys load error:", e);
      }
    }

    function renderKeys(keys) {
      const list = document.getElementById('key-list');
      list.innerHTML = '';
      keys.forEach(k => {
        const li = document.createElement('li');
        li.className = 'key-item' + (currentKey === k.name ? ' active' : '');
        li.innerHTML = `
          <span class="key-name" title="${k.name}">${k.name}</span>
          <span class="badge badge-${k.type}">${k.type}</span>
        `;
        li.onclick = () => inspectKey(k.name);
        list.appendChild(li);
      });
    }

    function filterKeys() {
      const q = document.getElementById('search').value.toLowerCase();
      const filtered = allKeys.filter(k => k.name.toLowerCase().includes(q));
      renderKeys(filtered);
    }

    async function inspectKey(name) {
      currentKey = name;
      renderKeys(allKeys);
      try {
        const res = await fetch(`/api/key?name=${encodeURIComponent(name)}`);
        const data = await res.json();
        
        document.getElementById('key-inspector').style.display = 'block';
        document.getElementById('inspect-key-name').innerText = data.name;
        document.getElementById('inspect-ttl').innerText = data.ttl;
        
        const badge = document.getElementById('inspect-type-badge');
        badge.className = `badge badge-${data.type}`;
        badge.innerText = data.type;

        const valElem = document.getElementById('inspect-value');
        if (data.type === 'string') {
          valElem.innerText = data.value;
        } else if (data.type === 'hash') {
          let rows = Object.entries(data.value).map(([f, v]) => `<tr><td><strong>${f}</strong></td><td>${v}</td></tr>`).join('');
          valElem.innerHTML = `<table><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>${rows}</tbody></table>`;
        } else if (data.type === 'list' || data.type === 'set') {
          let rows = data.value.map((v, idx) => `<tr><td style="width: 50px;">#${idx}</td><td>${v}</td></tr>`).join('');
          valElem.innerHTML = `<table><thead><tr><th>Index</th><th>Element</th></tr></thead><tbody>${rows}</tbody></table>`;
        } else if (data.type === 'zset') {
          let rows = data.value.map((item) => `<tr><td>${item[0]}</td><td style="width: 120px;">${item[1]}</td></tr>`).join('');
          valElem.innerHTML = `<table><thead><tr><th>Member</th><th>Score</th></tr></thead><tbody>${rows}</tbody></table>`;
        }
      } catch (e) {
        console.error("Inspect error:", e);
      }
    }

    async function deleteCurrentKey() {
      if (!currentKey || !confirm(`Delete key "${currentKey}"?`)) return;
      await fetch(`/api/key?name=${encodeURIComponent(currentKey)}`, { method: 'DELETE' });
      document.getElementById('key-inspector').style.display = 'none';
      currentKey = null;
      loadKeys();
      loadStats();
    }

    function openCreateModal() { document.getElementById('create-modal').style.display = 'grid'; }
    function closeCreateModal() { document.getElementById('create-modal').style.display = 'none'; }

    async function submitCreateKey() {
      const name = document.getElementById('new-key-name').value.trim();
      const type = document.getElementById('new-key-type').value;
      const value = document.getElementById('new-key-value').value;
      const ttl = document.getElementById('new-key-ttl').value;

      if (!name) return alert("Please enter key name");

      await fetch('/api/key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, type, value, ttl: ttl ? parseInt(ttl) : null })
      });

      closeCreateModal();
      loadKeys();
      loadStats();
      inspectKey(name);
    }

    async function runQuery() {
      const cmd = document.getElementById('console-cmd').value.trim();
      if (!cmd) return;
      try {
        const res = await fetch('/api/exec', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd })
        });
        const data = await res.json();
        document.getElementById('console-result').innerText = typeof data.result === 'object' ? JSON.stringify(data.result, null, 2) : data.result;
        loadStats();
        loadKeys();
      } catch (e) {
        document.getElementById('console-result').innerText = 'Error: ' + e;
      }
    }

    // Init
    loadStats();
    loadKeys();
    setInterval(loadStats, 5000);
  </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    client: Client = None

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            body = HTML_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/stats":
            info_raw = self.client.execute_command("INFO")
            info_str = info_raw.decode("utf-8") if isinstance(info_raw, bytes) else str(info_raw)
            stats = {}
            for line in info_str.splitlines():
                if ":" in line and not line.startswith("#"):
                    k, v = line.split(":", 1)
                    stats[k] = v
            self._send_json(stats)
            return

        if parsed.path == "/api/keys":
            raw_keys = self.client.execute_command("KEYS", "*") or []
            results = []
            for k in raw_keys:
                k_str = k.decode("utf-8", errors="replace") if isinstance(k, bytes) else str(k)
                t_str = self.client.execute_command("TYPE", k_str)
                t_str = t_str.decode("utf-8") if isinstance(t_str, bytes) else str(t_str)
                results.append({"name": k_str, "type": t_str})
            self._send_json(results)
            return

        if parsed.path == "/api/key":
            qs = parse_qs(parsed.query)
            key_name = qs.get("name", [""])[0]
            if not key_name:
                self._send_json({"error": "Missing key name"}, 400)
                return

            t_raw = self.client.execute_command("TYPE", key_name)
            t_str = t_raw.decode("utf-8") if isinstance(t_raw, bytes) else str(t_raw)
            ttl = self.client.execute_command("TTL", key_name)

            val = None
            if t_str == "string":
                res = self.client.execute_command("GET", key_name)
                val = res.decode("utf-8", errors="replace") if isinstance(res, bytes) else str(res)
            elif t_str == "hash":
                res = self.client.execute_command("HGETALL", key_name)
                val = {}
                for i in range(0, len(res), 2):
                    f = res[i].decode("utf-8", errors="replace") if isinstance(res[i], bytes) else str(res[i])
                    v = res[i+1].decode("utf-8", errors="replace") if isinstance(res[i+1], bytes) else str(res[i+1])
                    val[f] = v
            elif t_str == "list":
                res = self.client.execute_command("LRANGE", key_name, "0", "-1")
                val = [item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item) for item in res]
            elif t_str == "set":
                res = self.client.execute_command("SMEMBERS", key_name)
                val = [item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item) for item in res]
            elif t_str == "zset":
                res = self.client.execute_command("ZRANGE", key_name, "0", "-1", "WITHSCORES")
                val = []
                for i in range(0, len(res), 2):
                    m = res[i].decode("utf-8", errors="replace") if isinstance(res[i], bytes) else str(res[i])
                    s = res[i+1].decode("utf-8", errors="replace") if isinstance(res[i+1], bytes) else str(res[i+1])
                    val.append([m, s])

            self._send_json({"name": key_name, "type": t_str, "ttl": ttl, "value": val})
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        payload = json.loads(body.decode("utf-8")) if body else {}

        if parsed.path == "/api/key":
            name = payload.get("name")
            k_type = payload.get("type", "string")
            val = payload.get("value", "")
            ttl = payload.get("ttl")

            if k_type == "string":
                args = ["SET", name, val]
                if ttl:
                    args.extend(["EX", str(ttl)])
                self.client.execute_command(*args)
            elif k_type == "hash":
                try:
                    pairs = json.loads(val) if val.startswith("{") else {}
                    args = ["HSET", name]
                    for f, v in pairs.items():
                        args.extend([f, str(v)])
                    self.client.execute_command(*args)
                except Exception:
                    self.client.execute_command("HSET", name, "val", val)
            elif k_type == "list":
                items = [x.strip() for x in val.split(",") if x.strip()]
                self.client.execute_command("RPUSH", name, *items)
            elif k_type == "set":
                items = [x.strip() for x in val.split(",") if x.strip()]
                self.client.execute_command("SADD", name, *items)
            elif k_type == "zset":
                items = [x.strip().split(":") for x in val.split(",") if ":" in x]
                args = ["ZADD", name]
                for s, m in items:
                    args.extend([s.strip(), m.strip()])
                self.client.execute_command(*args)

            self._send_json({"status": "ok"})
            return

        if parsed.path == "/api/exec":
            cmd_str = payload.get("command", "")
            tokens = cmd_str.strip().split()
            if not tokens:
                self._send_json({"result": ""})
                return
            try:
                res = self.client.execute_command(*tokens)
                if isinstance(res, bytes):
                    res = res.decode("utf-8", errors="replace")
                elif isinstance(res, list):
                    res = [x.decode("utf-8", errors="replace") if isinstance(x, bytes) else x for x in res]
                self._send_json({"result": res})
            except Exception as e:
                self._send_json({"result": f"(error) {e}"})
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/key":
            qs = parse_qs(parsed.query)
            key_name = qs.get("name", [""])[0]
            if key_name:
                self.client.execute_command("DEL", key_name)
                self._send_json({"status": "ok"})
                return
        self.send_error(400, "Bad Request")


def main():
    parser = argparse.ArgumentParser(description="NomDB Web Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard bind host")
    parser.add_argument("--port", type=int, default=8080, help="Dashboard port (default: 8080)")
    parser.add_argument("--db-host", default="127.0.0.1", help="NomDB server host")
    parser.add_argument("--db-port", type=int, default=6379, help="NomDB server port")
    args = parser.parse_args()

    DashboardHandler.client = Client(host=args.db_host, port=args.db_port)
    server = HTTPServer((args.host, args.port), DashboardHandler)
    print(f"NomDB Web Dashboard running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
