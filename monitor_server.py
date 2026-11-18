#!/usr/bin/env python3
"""Servidor local del Monitor bibliográfico (solo escucha en 127.0.0.1; sin dependencias externas).

Para qué sirve (una página HTML abierta desde un fichero no puede hablar con Zotero ni guardar nada en disco):
  * Sirve el documento acumulado (out/Monitor bibliográfico.html) en http://127.0.0.1:47651/.
  * POST /api/zotero  -> guarda artículos en Zotero (colección «Monitor») a través del conector local de Zotero (puerto 23119).
  * GET/POST /api/marks -> guarda en out/marks.json tus marcas de lectura (leído / importante) y notas.
Seguridad: solo 127.0.0.1; se rechazan peticiones con Host distinto (anti DNS-rebinding); las peticiones POST exigen un token
(out/server_token.txt, inyectado en la página que sirve este servidor) y Content-Type JSON; no se envían cabeceras CORS, así que
otras webs no pueden usarlo.

Uso:  python monitor_server.py          (el LaunchAgent com.TUNOMBRE.literature-monitor-server lo mantiene en marcha)
"""
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
DASH = os.path.join(OUT, "Monitor bibliográfico.html")
MARKS = os.path.join(OUT, "marks.json")
SAVED = os.path.join(OUT, "zotero_saved.json")
TOKEN_FILE = os.path.join(OUT, "server_token.txt")
HOST, PORT = "127.0.0.1", int(os.environ.get("MONITOR_PORT", "47651"))
COLLECTION = os.environ.get("MONITOR_ZOTERO_COLLECTION", "Monitor")
ZOTERO = "http://127.0.0.1:23119/connector"
LOCK = threading.Lock()


def load_token():
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(TOKEN_FILE):
        t = open(TOKEN_FILE).read().strip()
        if t:
            return t
    t = secrets.token_urlsafe(24)
    with open(TOKEN_FILE, "w") as f:
        f.write(t)
    os.chmod(TOKEN_FILE, 0o600)
    return t


TOKEN = load_token()


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------------------------
# Zotero (conector local). Si Zotero no está abierto, el servidor lo dice y no hace nada.
# ---------------------------------------------------------------------------------------------
def zot(endpoint, data=None, timeout=15):
    body = json.dumps(data if data is not None else {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{ZOTERO}/{endpoint}", data=body, headers={
        "Content-Type": "application/json", "X-Zotero-Connector-API-Version": "3"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode("utf-8")
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(txt) if txt else None
        except ValueError:
            return e.code, {"error": txt}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return 0, None


def zotero_alive():
    try:
        with urllib.request.urlopen("http://127.0.0.1:23119/connector/ping", timeout=3) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def find_collection(name):
    st, d = zot("getSelectedCollection")
    if st != 200 or not d:
        return None, "Zotero no respondió a getSelectedCollection"
    cands = [t for t in d.get("targets", []) if t.get("id", "").startswith("C") and t.get("name") == name]
    if not cands:
        return None, f"No encuentro la colección «{name}» en Zotero (¿está creada?)"
    return min(cands, key=lambda t: t.get("level", 0))["id"], None


def article_key(a):
    return (a.get("pmid") or (a.get("doi") or "").lower() or a.get("title", "")[:80]).lower()


def zotero_item(a, month):
    creators = []
    for au in a.get("authors", []):
        parts = au.rsplit(" ", 1)
        if len(parts) == 2 and re.fullmatch(r"[A-ZÁÉÍÓÚÜÑ]{1,4}", parts[1]):
            creators.append({"creatorType": "author", "lastName": parts[0], "firstName": parts[1]})
        else:
            creators.append({"creatorType": "author", "name": au})
    url = f"https://doi.org/{a['doi']}" if a.get("doi") else (f"https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/" if a.get("pmid") else "")
    item = {"itemType": "journalArticle", "id": "i1", "title": a["title"], "creators": creators,
            "abstractNote": a.get("abstract", ""), "publicationTitle": a.get("journal", ""), "volume": a.get("volume", ""),
            "issue": a.get("issue", ""), "pages": a.get("pages", ""), "date": str(a.get("year", "")), "DOI": a.get("doi", ""),
            "url": url, "extra": f"PMID: {a['pmid']}" if a.get("pmid") else "",
            "tags": [{"tag": "lit-monitor"}] + ([{"tag": f"lit-monitor {month}"}] if month else [])}
    return {k: v for k, v in item.items() if v not in ("", [], None)} | {"id": "i1"}


def save_to_zotero(articles, month):
    if not zotero_alive():
        return 503, {"error": "Zotero no está abierto. Ábrelo y vuelve a intentarlo."}
    target, err = find_collection(COLLECTION)
    if err:
        return 404, {"error": err}
    results = []
    with LOCK:
        saved = read_json(SAVED, {})
        for a in articles[:200]:
            k = article_key(a)
            if k in saved:
                results.append({"key": k, "status": "ya_guardado"})
                continue
            sid = "litmon-" + hashlib.md5(k.encode()).hexdigest()[:14]
            st, resp = zot("saveItems", {"sessionID": sid, "uri": "https://pubmed.ncbi.nlm.nih.gov/",
                                         "items": [zotero_item(a, month)]})
            if st in (200, 201, 409):
                st2, _ = zot("updateSession", {"sessionID": sid, "target": target})
                saved[k] = {"collection": COLLECTION, "date": time.strftime("%Y-%m-%d"), "moved": st2 in (200, 201)}
                results.append({"key": k, "status": "guardado" if st != 409 else "ya_guardado"})
            else:
                results.append({"key": k, "status": "error", "http": st, "detail": str(resp)[:200]})
        write_json(SAVED, saved)
    ok = sum(1 for r in results if r["status"] in ("guardado", "ya_guardado"))
    return 200, {"collection": COLLECTION, "ok": ok, "total": len(results), "results": results}


# ---------------------------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "LitMonitor/1.0"

    def log_message(self, fmt, *args):  # log mínimo a stderr (va a out/server.log)
        sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _host_ok(self):
        return (self.headers.get("Host") or "").split(":")[0] in ("127.0.0.1", "localhost")

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if not self._host_ok():
            return self._send(403, {"error": "host no permitido"})
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(DASH, encoding="utf-8") as f:
                    html = f.read()
            except OSError:
                return self._send(404, "Aún no hay documento: ejecuta literature_monitor.py".encode(), "text/plain; charset=utf-8")
            inj = f'<script>window.MONITOR_SERVER={{token:"{TOKEN}",collection:"{COLLECTION}"}};</script>'
            html = html.replace("</head>", inj + "</head>", 1)
            return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/ping":
            return self._send(200, {"ok": True})
        if path == "/api/state":
            return self._send(200, {"marks": read_json(MARKS, {}), "zotero_saved": sorted(read_json(SAVED, {}).keys()),
                                    "zotero_alive": zotero_alive(), "collection": COLLECTION})
        return self._send(404, {"error": "no encontrado"})

    def do_POST(self):  # noqa: N802
        if not self._host_ok():
            return self._send(403, {"error": "host no permitido"})
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"):
            return self._send(403, {"error": "origen no permitido"})
        if self.headers.get("X-Monitor-Token") != TOKEN or "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._send(403, {"error": "token o tipo de contenido no válidos"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 5_000_000:
                return self._send(413, {"error": "petición demasiado grande"})
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, {"error": "JSON no válido"})
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/zotero":
            arts = body.get("articles") or []
            if not isinstance(arts, list) or not arts:
                return self._send(400, {"error": "sin artículos"})
            code, resp = save_to_zotero(arts, str(body.get("month", ""))[:7])
            return self._send(code, resp)
        if path == "/api/marks":
            ident = str(body.get("id", "")).lower()[:200]
            if not ident:
                return self._send(400, {"error": "falta id"})
            with LOCK:
                marks = read_json(MARKS, {})
                cur = marks.get(ident, {})
                for k in ("state", "note"):
                    if k in body:
                        cur[k] = str(body[k])[:5000]
                cur["updated"] = time.strftime("%Y-%m-%d %H:%M")
                if not cur.get("state") and not cur.get("note"):
                    marks.pop(ident, None)
                else:
                    marks[ident] = cur
                write_json(MARKS, marks)
            return self._send(200, {"ok": True})
        if path == "/api/marks/import":
            data = body.get("marks")
            if not isinstance(data, dict):
                return self._send(400, {"error": "formato no válido"})
            with LOCK:
                marks = read_json(MARKS, {})
                marks.update({str(k).lower()[:200]: v for k, v in data.items() if isinstance(v, dict)})
                write_json(MARKS, marks)
            return self._send(200, {"ok": True, "total": len(marks)})
        return self._send(404, {"error": "no encontrado"})


def main():
    os.makedirs(OUT, exist_ok=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Monitor bibliográfico en http://{HOST}:{PORT}/  (colección Zotero: {COLLECTION})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
