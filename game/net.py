"""Lớp mạng không chặn (non-blocking) cho game.

- Desktop: urllib trong thread.
- Web (pygbag / WebAssembly): gọi JS fetch qua platform.window.eval, rồi poll kết quả mỗi frame.
Mọi callback đều được gọi trên main thread trong Net.poll().
"""
import json
import os
import sys
import threading

WEB = sys.platform == "emscripten"

if WEB:
    import platform  # pygbag cung cấp platform.window

    _JS = """
    if(!window.__pg){
      window.__pg={res:{}};
      window.__pgf=function(id,method,url,body,token){
        var h={'Content-Type':'application/json'};
        if(token){h['Authorization']='Bearer '+token;}
        var o={method:method,headers:h};
        if(body){o.body=body;}
        fetch(url,o).then(function(r){return r.text().then(function(t){
          window.__pg.res[id]=JSON.stringify({s:r.status,t:t});});})
        .catch(function(e){window.__pg.res[id]=JSON.stringify({s:0,t:String(e)});});
      };
      window.__pgnotify=function(msg){
        try{ if('Notification' in window){
          if(Notification.permission==='granted'){new Notification('PawHabit',{body:msg});}
          else if(Notification.permission==='default'){Notification.requestPermission();}
        }}catch(e){}
      };
    }
    """


class Req:
    def __init__(self, cb, err):
        self.cb, self.err = cb, err
        self.status, self.data, self.done = 0, None, False


class Net:
    def __init__(self):
        self.token = None
        self.pending = []
        self._id = 0
        if WEB:
            platform.window.eval(_JS)
            self.base = "http://localhost:8001"
        else:
            self.base = os.getenv("PAWHABIT_URL","http://127.0.0.1:8001")

    @property
    def busy(self):
        return bool(self.pending)

    def request(self, method, path, body=None, cb=None, err=None):
        r = Req(cb, err)
        self._id += 1
        r.id = self._id
        url = self.base + "/api" + path
        payload = json.dumps(body) if body is not None else ""
        if WEB:
            platform.window.eval("window.__pgf(%d,%s,%s,%s,%s)" % (
                r.id, json.dumps(method), json.dumps(url), json.dumps(payload), json.dumps(self.token or "")))
        else:
            threading.Thread(target=self._thread, args=(r, method, url, payload), daemon=True).start()
        self.pending.append(r)
        return r

    def _thread(self, r, method, url, payload):
        import urllib.error
        import urllib.request
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(url, data=payload.encode() if payload else None, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                r.status, text = resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            r.status, text = e.code, e.read().decode()
        except Exception as e:  # noqa
            r.status, text = 0, str(e)
            if os.getenv("PAWHABIT_DEBUG"):
                print("NET ERROR", method, url, repr(e), file=sys.stderr)
        self._finish(r, text)

    def _finish(self, r, text):
        try:
            r.data = json.loads(text) if text else {}
        except ValueError:
            r.data = {"detail": text[:80]}
        r.done = True

    def poll(self):
        for r in list(self.pending):
            if WEB and not r.done:
                raw = str(platform.window.eval("(window.__pg.res[%d]||'')" % r.id))
                if raw:
                    platform.window.eval("delete window.__pg.res[%d]" % r.id)
                    obj = json.loads(raw)
                    r.status = obj["s"]
                    self._finish(r, obj["t"])
            if r.done:
                self.pending.remove(r)
                if 200 <= r.status < 300:
                    if r.cb:
                        r.cb(r.data)
                else:
                    msg = r.data.get("detail") if isinstance(r.data, dict) else None
                    if isinstance(msg, list):  # lỗi validate của pydantic
                        msg = "Dữ liệu nhập không hợp lệ (tên 3-24 ký tự chữ/số, mật khẩu ≥ 6)"
                    if r.status == 0:
                        msg = "Không kết nối được máy chủ"
                    if r.err:
                        r.err(r.status, msg or "Lỗi không xác định")

    def notify(self, msg):
        if WEB:
            try:
                platform.window.eval("window.__pgnotify(%s)" % json.dumps(msg))
            except Exception:
                pass
