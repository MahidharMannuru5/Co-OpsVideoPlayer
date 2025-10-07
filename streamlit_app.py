""import streamlit as st
import streamlit.components.v1 as components
import uuid

st.set_page_config(page_title="🎬 Watch Together", layout="wide")

st.title("🎬 Watch Together")
st.caption("Sync video and chat in real-time using one shared room")

room_id = st.text_input("Enter Room ID", value=str(uuid.uuid4())[:8])
role = st.radio("Choose your role", ["Host", "Guest"], horizontal=True)
video_url = st.text_input("Enter video URL (supports .mpd / .m3u8 / direct)", "")

if st.button("Start Session"):
    st.success(f"Connected to room: `{room_id}` as `{role}`")
    
    html_code = f"""
    <style>
      body {{ background-color: #111; color: #eee; font-family: sans-serif; }}
      #videoWrapper {{ text-align: center; margin-top: 10px; }}
      video {{ max-width: 100%; border-radius: 12px; }}
      #chatBox {{ margin-top: 20px; padding: 10px; background: #222; border-radius: 10px; max-height: 200px; overflow-y: auto; }}
      #msgInput {{ width: 80%; padding: 8px; }}
      #sendBtn {{ padding: 8px; background: #00e1ff; border: none; border-radius: 5px; }}
    </style>

    <div id="videoWrapper">
      <video id="videoPlayer" controls autoplay style="width: 90%;">
        <source src="{video_url}" type="application/dash+xml">
        Your browser does not support video playback.
      </video>
    </div>

    <div style="margin-top: 20px; text-align: center;">
      <strong>Chat</strong>
      <div id="chatBox"></div>
      <input id="msgInput" placeholder="Type message..." />
      <button id="sendBtn">Send</button>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/peerjs@1.5.2/dist/peerjs.min.js"></script>
    <script>
      const roomId = "{room_id}";
      const isHost = {"true" if role == "Host" else "false"};
      const peerId = isHost ? `${{roomId}}-host` : undefined;
      const connectTo = `${{roomId}}-host`;
      const peer = new Peer(peerId);
      let conn = null;

      const log = (msg) => {{
        const box = document.getElementById("chatBox");
        box.innerHTML += `<div>${{msg}}</div>`;
        box.scrollTop = box.scrollHeight;
      }}

      peer.on('open', id => {{
        log(`<i>Connected as ${{id}}</i>`);
        if (!isHost) {{
          conn = peer.connect(connectTo);
          conn.on('open', () => log("Connected to host"));
          setupConnection();
        }}
      }});

      peer.on('connection', connection => {{
        conn = connection;
        setupConnection();
      }});

      function setupConnection() {{
        conn.on('data', data => {{
          if (data.type === 'chat') log(`<b>Peer:</b> ${{data.msg}}`);
          if (data.type === 'sync') handleSync(data);
        }});
      }}

      document.getElementById('sendBtn').onclick = () => {{
        const input = document.getElementById('msgInput');
        const msg = input.value;
        if (!msg) return;
        log(`<b>You:</b> ${{msg}}`);
        conn?.send({{ type: 'chat', msg }});
        input.value = '';
      }};

      const video = document.getElementById('videoPlayer');

      function sendSync(action) {{
        if (!conn) return;
        conn.send({{ type: 'sync', action, time: video.currentTime }});
      }}

      video.onplay = () => {{ if (isHost) sendSync('play'); }};
      video.onpause = () => {{ if (isHost) sendSync('pause'); }};
      video.onseeked = () => {{ if (isHost) sendSync('seek'); }};

      function handleSync(data) {{
        if (Math.abs(video.currentTime - data.time) > 0.5) video.currentTime = data.time;
        if (data.action === 'play') video.play();
        if (data.action === 'pause') video.pause();
      }}
    </script>
    """

    components.html(html_code, height=720)

st.markdown("""
---
**How to Use**
- 👥 One user selects **Host**, another selects **Guest**.
- 🔗 Share the same **Room ID**.
- 🎥 Paste a direct link to your video (.mpd or .m3u8 supported).
- 📡 Watch and chat together in sync!
""")
