import streamlit as st
import re
from urllib.parse import urljoin
import httpx

st.set_page_config(page_title="🎥 DASH Video Sync + Chat", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    #MainMenu, header, footer {visibility: hidden;}
    video { width: 100%; max-height: 70vh; border-radius: 8px; background: #000; }
    .chat-box { background: #111; padding: 10px; height: 200px; overflow-y: auto; border-radius: 8px; color: white; }
    </style>
""", unsafe_allow_html=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124 Safari/537.36"}

MPD_RE = re.compile(r'https?://[^"]+\.mpd(?:\?[^"\s]*)?', re.I)
SRC_RE = re.compile(r'''src\s*=\s*"([^"]+)"''', re.I)


def absolutize(base: str, path: str) -> str:
    return urljoin(base, path)

def fetch_html(url: str):
    try:
        with httpx.Client(headers=UA, follow_redirects=True, timeout=15.0) as c:
            r = c.get(url)
            r.raise_for_status()
            return r.text, str(r.url)
    except Exception as e:
        st.error(f"Error fetching: {e}")
        return None, None

def find_mpd_links(html: str, base_url: str):
    links = set(MPD_RE.findall(html))
    # Add src="..." checks
    for match in SRC_RE.finditer(html):
        val = match.group(1)
        if ".mpd" in val:
            links.add(absolutize(base_url, val))
    return list(links)

st.title("🎬 DASH Video Player + Chat (No Backend)")
st.caption("Paste a video page URL (with .mpd/.m4s streaming). Room sync & chat handled via PeerJS (frontend-only).")

url = st.text_input("🔗 Video Page URL", placeholder="https://example.com/watch?id=123")
room_id = st.text_input("🧩 Room ID", placeholder="host123")

col1, col2 = st.columns([1,1])
with col1:
    go = st.button("Fetch Video")

if go and url:
    with st.spinner("Looking for .mpd file..."):
        html, final_url = fetch_html(url)
        if html:
            candidates = find_mpd_links(html, final_url)
            if not candidates:
                st.warning("No .mpd links found.")
            else:
                best_mpd = candidates[0]
                st.success("Found .mpd stream!")

                st.markdown(f"**Stream URL**: `{best_mpd}`")

                st.markdown("""
                <script src="https://cdn.dashjs.org/latest/dash.all.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/peerjs@1.5.2/dist/peerjs.min.js"></script>

                <video id="videoPlayer" controls autoplay></video>
                <div style="margin-top:20px;">
                    <input id="msgInput" placeholder="Type message..." style="width:80%; padding:5px;">
                    <button onclick="sendMsg()">Send</button>
                    <div id="chat" class="chat-box"></div>
                </div>

                <script>
                    const mpdUrl = """ + f'"{best_mpd}"' + ";
                    const roomId = """ + f'"{room_id}"' + ";
                    const player = dashjs.MediaPlayer().create();
                    player.initialize(document.querySelector("#videoPlayer"), mpdUrl, false);

                    let peer = new Peer(roomId);
                    let conn;

                    peer.on('open', function(id) {
                        console.log("Peer ready:", id);
                    });

                    peer.on('connection', function(c) {
                        conn = c;
                        setupConn();
                    });

                    function connectToHost() {
                        conn = peer.connect(roomId);
                        conn.on('open', setupConn);
                    }

                    function setupConn() {
                        conn.on('data', function(data) {
                            if (data.type === 'chat') {
                                document.getElementById('chat').innerHTML += `<div><b>Peer:</b> ${data.text}</div>`;
                            } else if (data.type === 'sync') {
                                const action = data.action;
                                if (action === 'play') video.play();
                                if (action === 'pause') video.pause();
                                if (action === 'seek') video.currentTime = data.time;
                            }
                        });
                    }

                    function sendMsg() {
                        const txt = document.getElementById('msgInput').value;
                        document.getElementById('chat').innerHTML += `<div><b>You:</b> ${txt}</div>`;
                        conn?.send({type:'chat', text:txt});
                        document.getElementById('msgInput').value = '';
                    }

                    const video = document.getElementById('videoPlayer');
                    video.addEventListener('play', () => conn?.send({type:'sync', action:'play'}));
                    video.addEventListener('pause', () => conn?.send({type:'sync', action:'pause'}));
                    video.addEventListener('seeked', () => conn?.send({type:'sync', action:'seek', time: video.currentTime}));
                </script>
                """, unsafe_allow_html=True)

                st.info("Share the same room ID with a friend and either 'host' or 'join' by refreshing.")
        else:
            st.error("Failed to load the page.")
