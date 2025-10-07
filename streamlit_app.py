import re
from urllib.parse import urljoin
import httpx
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Watch Together - DASH", page_icon="🎬", layout="wide")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

MPD_URL_RE = re.compile(r'https?://[^"]+\.mpd(?:\?[^"]*)?', re.I)
SRC_ATTR_RE = re.compile(r'''src\s*=\s*["']([^"']+)["']''', re.I)

# ---- Utils ----
def absolutize(base: str, path: str) -> str:
    return urljoin(base, path)

def fetch_text(url: str, timeout: float = 20.0):
    with httpx.Client(headers=UA, follow_redirects=True, timeout=timeout) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text, str(r.url)

def find_mpd_in_html(html: str, base_url: str):
    found = set()
    for u in MPD_URL_RE.findall(html):
        found.add(u)
    for m in SRC_ATTR_RE.finditer(html):
        val = m.group(1)
        if ".mpd" in val.lower():
            found.add(absolutize(base_url, val))
    return list(dict.fromkeys(found))

def find_iframes(html: str, base_url: str):
    iframes = []
    for m in SRC_ATTR_RE.finditer(html):
        val = m.group(1)
        ctx = html[max(0, m.start()-20):m.start()+20].lower()
        if "<iframe" in ctx:
            iframes.append(absolutize(base_url, val))
    return list(dict.fromkeys(iframes))

def choose_first(candidates: list[str]) -> str | None:
    if not candidates:
        return None
    return candidates[0]

def find_mpd_deep(page_url: str, iframe_depth: int = 1, max_iframes_per_level: int = 10):
    try:
        html, final_url = fetch_text(page_url)
    except Exception as e:
        return None, [], f"Fetch failed: {e}"

    all_candidates = find_mpd_in_html(html, final_url)
    frontier = find_iframes(html, final_url)[:max_iframes_per_level]
    seen = set()
    for _ in range(iframe_depth):
        next_frontier = []
        for iframe_url in frontier:
            if iframe_url in seen:
                continue
            seen.add(iframe_url)
            try:
                ihtml, ifinal = fetch_text(iframe_url)
            except Exception:
                continue
            all_candidates += find_mpd_in_html(ihtml, ifinal)
            next_frontier += find_iframes(ihtml, ifinal)[:max_iframes_per_level]
        frontier = next_frontier

    deduped = list(dict.fromkeys(all_candidates))
    best = choose_first(deduped)
    return best, deduped, None

# ---- UI ----
st.title("🎬 Watch Together (MPEG-DASH)")
st.caption("Paste a video page with .mpd/.m4s DASH streaming. You'll stream + sync with one friend, no backend.")

url = st.text_input("Enter Page URL with .mpd video", placeholder="https://example.com/watch")
room_id = st.text_input("Room ID (same for both viewers)", placeholder="example123")
col1, col2 = st.columns([1, 1])

with col1:
    depth = st.selectbox("Iframe depth", options=[0,1,2], index=1)
with col2:
    run = st.button("🎯 Fetch Video")

if run and url:
    with st.spinner("Scanning page for .mpd..."):
        best_mpd, candidates, err = find_mpd_deep(url, iframe_depth=int(depth))
    if err:
        st.error(err)
    elif not best_mpd:
        st.warning("No .mpd URLs found.")
    else:
        st.success("MPD video found! Launching player...")

        components.html(f"""
        <html>
        <head>
          <script src='https://cdn.dashjs.org/latest/dash.all.min.js'></script>
          <script src="https://cdn.jsdelivr.net/npm/peerjs@1.5.2/dist/peerjs.min.js"></script>
        </head>
        <body style='margin:0;background:#000;color:#fff;'>
            <video id="video" controls autoplay style="width:100%; height:70vh;"></video>
            <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 20px;">
              <div><b>You:</b> <span id="me"></span> | <b>Peer:</b> <span id="peer"></span></div>
              <button onclick="location.reload()">Exit</button>
            </div>
            <div id="chat" style="padding:10px; height:25vh; overflow:auto; background:#111;"></div>
            <input id="msg" placeholder="Type message..." style="width:80%; padding:6px;"><button onclick="sendMsg()">Send</button>

            <script>
              const mpdUrl = "{best_mpd}";
              const player = dashjs.MediaPlayer().create();
              const video = document.getElementById("video");
              player.initialize(video, mpdUrl, true);

              const peer = new Peer("{room_id}" + Math.random().toString(36).substring(7));
              document.getElementById("me").innerText = peer.id;
              let conn;

              peer.on("open", id => {
                const hostId = "{room_id}-host";
                if (id.includes("host")) {
                  peer.on("connection", c => {
                    conn = c;
                    setup();
                  });
                } else {
                  conn = peer.connect(hostId);
                  conn.on("open", setup);
                }
              });

              function setup() {
                document.getElementById("peer").innerText = conn.peer;
                conn.on("data", data => {
                  if (data.t === "chat") addChat("Peer", data.msg);
                  if (data.t === "sync") sync(data);
                });
              }

              function sendMsg() {
                const val = document.getElementById("msg").value;
                if (!val) return;
                addChat("You", val);
                conn.send({ t: "chat", msg: val });
                document.getElementById("msg").value = "";
              }

              function addChat(who, msg) {
                document.getElementById("chat").innerHTML += `<div><b>${who}:</b> ${msg}</div>`;
              }

              function sync(data) {
                if (Math.abs(video.currentTime - data.time) > 0.5)
                  video.currentTime = data.time;
                if (data.action === "play") video.play();
                else if (data.action === "pause") video.pause();
              }

              video.onplay = () => conn?.send({ t: "sync", action: "play", time: video.currentTime });
              video.onpause = () => conn?.send({ t: "sync", action: "pause", time: video.currentTime });
              video.onseeked = () => conn?.send({ t: "sync", action: "seek", time: video.currentTime });
            </script>
        </body>
        </html>
        """, height=720)

        with st.expander("Show all .mpd candidates"):
            for u in candidates:
                st.code(u)

st.markdown("""
---
### ℹ️ Notes
- Works best for DASH-based video players (.mpd and .m4s segments)
- Real-time P2P sync + chat with PeerJS (no backend needed)
- Test with two browser tabs using same Room ID
""")
