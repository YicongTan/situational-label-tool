#!/usr/bin/env python3
"""Start the labelling page on this computer: python3 start.py

Needs only Python 3.8+. Opens the page in your browser and saves every answer to answers/labels_NAME.jsonl.
Nothing leaves this computer. When you finish, send that file to Yicong.
"""
import functools
import http.server
import json
import os
import re
import threading
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANSWERS = HERE / "answers"
NAME = re.compile(r"^[a-z0-9_-]{1,40}$")
SID = re.compile(r"^s[0-9]{3}$")


def read_rows(user):
    path = ANSWERS / f"labels_{user}.jsonl"
    if not path.exists():
        return {}
    return {r["sid"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def write_rows(user, rows):
    ANSWERS.mkdir(exist_ok=True)
    path = ANSWERS / f"labels_{user}.jsonl"
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(rows[k], ensure_ascii=False) + "\n" for k in sorted(rows)), encoding="utf-8")
    os.replace(tmp, path)


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = self.path.split("/")
        if self.path.startswith("/api/"):
            if len(parts) == 4 and parts[2] == "labels" and NAME.match(parts[3]):
                return self.reply(200, read_rows(parts[3]))
            return self.reply(404, {})
        return super().do_GET()

    def do_PUT(self):
        parts = self.path.split("/")
        if len(parts) != 5 or parts[2] != "labels" or not NAME.match(parts[3]) or not SID.match(parts[4]):
            return self.reply(404, {})
        rec = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        rows = read_rows(parts[3])
        if parts[4] not in rows or rec["ts"] >= rows[parts[4]]["ts"]:
            rows[parts[4]] = rec
            write_rows(parts[3], rows)
        return self.reply(200, {})


def main():
    handler = functools.partial(Handler, directory=str(HERE / "site"))
    # Single-threaded on purpose, so two saves can never overwrite each other's file.
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Labelling page: {url}\nAnswers: {ANSWERS}\nPress Ctrl+C here when you stop. Your answers are already saved.", flush=True)
    threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
