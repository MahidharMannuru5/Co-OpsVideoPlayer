import streamlit as st
import streamlit.components.v1 as components
from playwright.sync_api import sync_playwright

st.set_page_config(layout="wide")
st.markdown("<h2 style='text-align: center;'>🎬 WatchTogether</h2>", unsafe_allow_html=True)

# Room Connection UI
if "connected" not in st.session_state:
    st.session_state.connected = False

if not st.session_state.connected:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔵 Create Room"):
            st.session_state.is_host = True
            st.session_state.connected = True
    with col2:
        room_id = st.text_input("Enter Room ID to Join")
    with col3:
        if st.button("🔗 Join Room") and room_id:
            st.session_state.is_host = False
            st.session_state.connected = True

# Function to extract direct video URL from xHamster-like sites using Playwright
def extract_video_url(page_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(page_url)
        page.wait_for_timeout(5000)  # wait for elements
        video_tags = page.query_selector_all("video source")
        for tag in video_tags:
            src = tag.get_attribute("src")
            if src and (".mp4" in src or ".m3u8" in src):
                browser.close()
                return src
        browser.close()
    return None

if st.session_state.connected:
    st.markdown("---")

    # Layout: Video on top, chat on bottom
    url = st.text_input("Paste video page URL here:")
    load_btn = st.button("▶️ Load & Sync Video")
    placeholder = st.empty()

    if load_btn and url:
        with st.spinner("🔍 Extracting video URL..."):
            video_src = extract_video_url(url)
            if video_src:
                st.success("Video URL loaded successfully!")
                # Load player
                components.html(f"""
                    <video id="syncVideo" width="100%" height="450" controls>
                      <source src="{video_src}" type="video/mp4">
                    </video>
                    <script>
                        const video = document.getElementById('syncVideo');
                        // You can add PeerJS sync here later
                    </script>
                """, height=480)
            else:
                st.error("⚠️ Unable to extract video stream. Try a different link.")

    st.markdown("### 💬 Chat")
    chat = st.text_input("Type a message:")
    if chat:
        st.write(f"**You:** {chat}")
