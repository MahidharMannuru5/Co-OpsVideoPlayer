import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Watch Together", layout="wide")
st.title("🎬 Watch Together (No Backend)")

room_id = st.text_input("Enter Room ID", placeholder="e.g. room123")
role = st.radio("Choose your role", ["Host", "Guest"])
url = st.text_input("Paste video .mpd link", placeholder="https://.../file.mpd")

start = st.button("Start Session")

if start and room_id and url:
    st.success("Session started. Connecting...")

    components.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.dashjs.org/latest/dash.all.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/peerjs@1.5.2/dist/peerjs.min.js"></script>
        <style>
            body {{ background-color: #000; margin: 0; font-family: sans-serif; color: #eee; }}
            #layout {{ display: flex; flex-direction: column; height: 100vh; }}
            video {{ width: 100%; max-height: 70vh; background: #000; }}
            #chat {{ flex: 1; background: #111; padding: 10px; overflow-y: auto; }}
            #msgBox {{ display: flex; }}
            input[type=text] {{ flex: 1; padding: 10px; border: none; border-radius: 5px; }}
            button {{ padding: 10px; background: #00e1ff; border: none; border-radius: 5px; margin-left: 5px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div id="layout">
            <video id="video" controls autoplay></video>
            <div id="chat">
                <div id="messages"></div>
                <div id="msgBox">
                    <input id="msgInput" type="text" placeholder="Type a message...">
                    <button onclick="sendMsg()">Send</button>
                </div>
            </div>
        </div>
        <script>
            const mpdUrl = "{url}";
            const room = "{room_id}";
            const isHost = "{role}" === "Host";

            const peer = new Peer(isHost ? room + "-host" : room);
            let conn;

            const video = document.getElementById("video");
            const player = dashjs.MediaPlayer().create();
            player.initialize(video, mpdUrl, false);

            peer.on('open', id => {{
                if (!isHost) {{
                    conn = peer.connect(room + "-host");
                    conn.on('open', () => setup());
                }} else {{
                    peer.on('connection', c => {{
                        conn = c;
                        setup();
                    }});
                }}
            }});

            function setup() {{
                conn.on('data', data => {{
                    if (data.type === 'chat') {{
                        log("Peer: " + data.text);
                    }} else if (data.type === 'sync') {{
                        syncVideo(data);
                    }}
                }});
            }}

            function sendMsg() {{
                const txt = document.getElementById("msgInput").value;
                if (!txt) return;
                log("You: " + txt);
                conn.send({{ type: 'chat', text: txt }});
                document.getElementById("msgInput").value = "";
            }}

            function log(msg) {{
                const box = document.getElementById("messages");
                box.innerHTML += `<div>${{msg}}</div>`;
                box.scrollTop = box.scrollHeight;
            }}

            function sendSync(action) {{
                if (isHost && conn && conn.open) {{
                    conn.send({{ type: 'sync', action: action, time: video.currentTime }});
                }}
            }}

            function syncVideo(data) {{
                if (Math.abs(video.currentTime - data.time) > 0.5) video.currentTime = data.time;
                if (data.action === 'play') video.play();
                else if (data.action === 'pause') video.pause();
            }}

            video.onplay = () => sendSync('play');
            video.onpause = () => sendSync('pause');
            video.onseeked = () => sendSync('seek');
        </script>
    </body>
    </html>
    """, height=700)
else:
    st.info("Enter room ID and video URL to start.")
