import streamlit as st
import base64
import time
import jwt  # 需在 requirements.txt 安装 PyJWT
import requests
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(稳定版)", page_icon="🍱", layout="wide")

# CSS 样式 (黑金风格适配可灵)
st.markdown("""
<style>
    .stApp { background-color: #1A1A1A; color: #E0E0E0; }
    h1, h2, h3, p, div, span { color: #E0E0E0 !important; }
    .stButton>button { 
        background-color: #D4AF37; color: black !important; 
        border-radius: 8px; border: none; padding: 12px 28px;
        font-size: 18px; font-weight: bold; width: 100%;
    }
    .stButton>button:hover { background-color: #F1C40F; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #333; color: white; border-color: #555;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 身份验证 ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("## 🔒 内部系统登录")
        pwd = st.text_input("密码", type="password", label_visibility="collapsed")
        if st.button("解锁"):
            if pwd == st.secrets.get("APP_PASSWORD", "123456"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("❌ 密码错误")
    st.stop()

# --- 3. 后台配置加载 ---
try:
    # A. 文本：DeepSeek
    TEXT_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TEXT_BASE = "https://api.deepseek.com"
    
    # B. 视觉：Kimi (Moonshot)
    VISION_KEY = st.secrets["MOONSHOT_API_KEY"]
    VISION_BASE = "https://api.moonshot.cn/v1"
    
    # C. 绘图：Kling (可灵)
    KLING_AK = st.secrets["KLING_ACCESS_KEY"]
    KLING_SK = st.secrets["KLING_SECRET_KEY"]
    
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.info("请在 Secrets 中配置 DEEPSEEK_API_KEY, MOONSHOT_API_KEY, KLING_ACCESS_KEY, KLING_SECRET_KEY")
    st.stop()

# --- 4. 核心功能函数 ---

def get_kling_token(ak, sk):
    """
    【修复版】生成可灵 API 的 JWT 令牌
    修复点：显式指定 HS256 算法，增加时间戳容错
    """
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    payload = {
        "iss": ak,
        "exp": int(time.time()) + 1800, # 30分钟有效
        "nbf": int(time.time()) - 5     # 提前5秒生效，防止服务器时间误差
    }
    # 核心修复：明确指定 algorithm="HS256"
    token = jwt.encode(payload, sk, algorithm="HS256", headers=headers)
    return token

def generate_image_kling(prompt):
    """调用可灵官方文生图接口 (带轮询等待)"""
    token = get_kling_token(KLING_AK, KLING_SK)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # 1. 提交任务
    url_submit = "https://api.klingai.com/v1/images/generations"
    payload = {
        "model": "kling-v1", 
        "prompt": f"Delicious food photography, 8k resolution, cinematic lighting, {prompt}",
        "n": 1,
        "aspect_ratio": "1:1"
    }
    
    try:
        res = requests.post(url_submit, json=payload, headers=headers)
        if res.status_code != 200:
            return f"Error: 提交失败 {res.text}"
        
        data = res.json()
        if data["code"] != 0:
            return f"Error: 可灵报错 {data['message']} (Code: {data['code']})"
            
        task_id = data["data"]["task_id"]
        
        # 2. 轮询等待结果
        url_query = f"https://api.klingai.com/v1/images/generations/{task_id}"
        
        # 增加等待时间提示
        progress_text = "🎨 可灵 (Kling) 正在绘制中... 请耐心等待约 15-20 秒"
        my_bar = st.progress(0, text=progress_text)

        for i in range(40): # 最多等待 40 * 2 = 80秒
            time.sleep(2)
            my_bar.progress((i + 1) * 2, text=progress_text)
            
            res_q = requests.get(url
