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
LOCAL_API = "http://localhost:8001"   # cổng API khi chạy thử trên máy (đổi nếu bạn chạy cổng khác)

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
    }
    window.__pgnotify=function(msg){
      try{
        if(!('Notification' in window)){return 'unsupported';}
        if(Notification.permission==='granted'){new Notification('PawHabit',{body:msg});return 'sent';}
        if(Notification.permission==='default'){Notification.requestPermission();return 'asked';}
        return 'denied';
      }catch(e){return 'error:'+e;}
    };
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
            api = str(platform.window.eval("(new URLSearchParams(location.search).get('api')||'')"))
            host = str(platform.window.eval("location.hostname"))
            if api.startswith("http"):                    # 1) ?api=http://... được ưu tiên
                self.base = api.rstrip("/")
            elif host in ("localhost", "127.0.0.1"):      # 2) chạy thử trên máy
                self.base = LOCAL_API
            else:                                         # 3) đã deploy: API cùng domain với trang game
                self.base = "https://petgame-hyk7.onrender.com"
        else:
            self.base = os.getenv("PAWHABIT_URL", LOCAL_API)

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
                        why = r.data.get("detail", "") if isinstance(r.data, dict) else ""
                        msg = "Không kết nối được %s (%s)" % (self.base, str(why)[:50])
                    elif r.status in (404, 405) and WEB:
                        msg = "Không thấy API tại %s – kiểm tra cổng hoặc thêm ?api=URL" % self.base
                    if r.err:
                        r.err(r.status, msg or "Lỗi không xác định")

    def notify(self, msg):
        """Trả về: sent | asked | denied | unsupported | desktop | error:..."""
        if not WEB:
            return "desktop"
        try:
            return str(platform.window.eval("window.__pgnotify(%s)" % json.dumps(msg)))
        except Exception as e:
            return "error:%s" % e

    def copy(self, text):
        """Sao chép vào clipboard (chỉ bản web). Trả về: ok | desktop | error:..."""
        if not WEB:
            return "desktop"
        try:
            return str(platform.window.eval(
                "(function(t){try{navigator.clipboard.writeText(t);return 'ok';}catch(e){return 'error:'+e;}})(%s)" % json.dumps(text)))
        except Exception as e:
            return "error:%s" % e

    def open_url(self, url):
        """Mở link ở tab/trình duyệt mới."""
        try:
            if WEB:
                platform.window.eval("window.open(%s,'_blank')" % json.dumps(url))
            else:
                import webbrowser
                webbrowser.open(url)
            return "ok"
        except Exception as e:
            return "error:%s" % e