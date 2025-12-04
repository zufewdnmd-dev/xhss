import streamlit as st
import base64
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单笔记生成器", page_icon="🛵", layout="centered")

# 自定义样式 (你的暖米色风格 + 隐藏水印)
st.markdown("""
<style>
    .stApp { background-color: #F3F0E9; }
    h1, h2, h3, p, div { color: #1F3556 !important; }
    div.stButton > button { background-color: #D67052; color: white !important; border-radius: 8px; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 核心功能：密码验证机制 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown("### 🔒 请输入访问密码")
    password_input = st.text_input("Access Password", type="password", label_visibility="collapsed")
    
    if st.button("解锁应用"):
        # 生产环境建议使用 st.secrets，这里保留默认值防止报错
        correct_password = st.secrets.get("APP_PASSWORD", "123456") 
        if password_input == correct_password:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ 密码错误")
    return False

if not check_password():
    st.stop()

# --- 3. 侧边栏：万能模型配置 ---
with st.sidebar:
    st.header("🧠 模型大脑配置")
    provider = st.selectbox(
        "选择模型厂商",
        ["DeepSeek (深度求索)", "Moonshot (Kimi)", "OpenAI (GPT-4o)", "Aliyun (通义千问)", "自定义"]
    )
    
    # 预设配置
    if provider == "DeepSeek (深度求索)":
        default_base_url = "https://api.deepseek.com"
        default_model = "deepseek-chat"
        st.info("💡 DeepSeek 性价比高，暂不支持识图")
    elif provider == "Moonshot (Kimi)":
        default_base_url = "https://api.moonshot.cn/v1"
        default_model = "moonshot-v1-8k"
    elif provider == "OpenAI (GPT-4o)":
        default_base_url = "https://api.openai.com/v1"
        default_model = "gpt-4o"
    elif provider == "Aliyun (通义千问)":
        default_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        default_model = "qwen-plus"
    else:
        default_base_url = "https://api.example.com/v1"
        default_model = "my-model"

    base_url = st.text_input("Base URL", value=default_base_url)
    model_name = st.text_input("Model Name", value=default_model)
    api_key = st.text_input("API Key", type="password")

# --- 4. 主界面逻辑 ---
st.title("🛵 外卖商家爆款笔记生成器")
st.caption("基于本地生活赛道SOP · 专写高转化外卖软文")

st.divider()

col1, col2 = st.columns([1, 1])
with col1:
    uploaded_file = st.file_uploader("Step 1: 上传菜品图 (可选)", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="已上传素材", use_container_width=True)

with col2:
    # 这里的提示语修改了，引导用户输入具体的商家信息
    topic = st.text_area(
        "Step 2: 输入商家/菜品信息 (必填)", 
        height=200, 
        placeholder="请提供关键信息，例如：\n1. 店名：张三疯麻辣烫\n2. 位置：杭州下沙大学城附近\n3. 招牌菜：老油条、炸蛋、微辣汤底\n4. 价格：人均20元，量大\n5. 亮点：包装严实，送得快..."
    )
    generate_btn = st.button("✨ 生成外卖种草文", use_container_width=True)

# --- 5. 辅助函数 ---
def encode_image(file):
    return base64.b64encode(file.getvalue()).decode('utf-8')

# --- 6. 生成逻辑 ---
if generate_btn:
    if not api_key:
        st.error("⚠️ 请先在侧边栏填入 API Key")
    elif not topic:
        st.warning("⚠️ 请输入商家信息，否则 AI
