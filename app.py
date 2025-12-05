import streamlit as st
import base64
import time
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(深度定制版)", page_icon="🍱", layout="wide")

# CSS 样式 (保持暖米色风格)
st.markdown("""
<style>
    .stApp { background-color: #F3F0E9; }
    .stButton>button { 
        background-color: #D67052; color: white !important; 
        border-radius: 12px; padding: 12px 28px;
        font-size: 18px; font-weight: bold; width: 100%; border: none;
    }
    .stButton>button:hover { background-color: #C0583E; }
    h1, h2, h3, p, div, span { color: #1F3556 !important; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #FFFFFF; color: #333; border-radius: 8px;
    }
    .streamlit-expanderHeader {
        background-color: #ECE8DF; border-radius: 8px;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 身份验证 (沿用) ---
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

# --- 3. 后台配置加载 (沿用) ---
try:
    TEXT_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TEXT_BASE = "https://api.deepseek.com"
    VISION_KEY = st.secrets["MOONSHOT_API_KEY"]
    VISION_BASE = "https://api.moonshot.cn/v1"
    IMG_KEY = st.secrets["SILICON_API_KEY"]
    IMG_BASE = "https://api.siliconflow.cn/v1"
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.stop()

# --- 4. 核心功能函数 ---

def encode_image(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def analyze_image_kimi(image_file):
    """【眼睛】Kimi 看图"""
    encoded_string = encode_image(image_file)
    client = OpenAI(api_key=VISION_KEY, base_url=VISION_BASE)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="moonshot-v1-8k-vision-preview",
                messages=[
                    {"role": "system", "content": "你是专业美食摄影师。"},
                    {"role": "user", "content": [
                        {"type": "text", "text": "分析这张图的主菜品、食材、色泽。只输出最核心的菜品名称和特点描述（例如：色泽红亮的红烧肉）。不要废话。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}
                    ]}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(3)
                continue
            elif attempt == max_retries - 1:
                return f"Error: 视觉识别失败 {str(e)}"
    return "Error: 未知错误"

def generate_copy_deepseek(vision_res, user_topic):
    """【大脑】DeepSeek 写文"""
    client = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    prompt = f"""
    你是一名小红书爆款写手。请结合【视觉描述】和【商家信息】，写一篇外卖种草笔记。
    【视觉描述】：{vision_res}
    【商家信息】：{user_topic}
    要求：标题二极管，正文多Emoji，语气真诚，突出一人食的精致感。
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.3
    )
    return response.choices[0].message.content

def generate_image_silicon(vision_res, user_topic):
    """
    【画手】硅基流动 (调用 Kolors)
    核心修改：使用用户提供的超详细提示词模板
    """
    # 定义详细的提示词模板
    DETAILED_PROMPT_TEMPLATE = """
    请生成一张日常分享风格的plog图片，核心呈现一人食温馨用餐场景，画面整体采用暖色调。
    具体细节要求如下：
    1、桌面布置：铺有编织餐垫，餐垫旁摆放绿植、日式可爱摆件、牙签盒、餐巾纸盒；场景正前方放置1台iPad，屏幕需显示《蜡笔小新》播放画面。
    2、餐食与餐具：
    餐具统一为日式风格，符合一人食规律。餐食
