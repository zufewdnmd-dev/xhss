import streamlit as st
import base64
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(国风版)", page_icon="🥢", layout="wide")

# 注入 CSS 样式
st.markdown("""
<style>
    .stApp { background-color: #F8F5F2; }
    h1, h2, h3 { color: #2C3E50 !important; }
    .stButton>button { 
        background-color: #E17055; color: white !important; /* 藕荷色改砖红 */
        border-radius: 12px; border: none; padding: 12px 28px;
        font-size: 18px; font-weight: bold;
    }
    .stButton>button:hover { background-color: #D35400; transform: scale(1.02); }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 身份验证 ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("## 🔒 内部系统登录")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("解锁"):
        if pwd == st.secrets.get("APP_PASSWORD", "123456"):
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("❌ 密码错误")
    st.stop()

# --- 3. 后台加载配置 ---
try:
    # 1. 视觉配置 (建议 GPT-4o 或 Kimi)
    # 如果你用 Kimi，这里 VISION_MODEL 需要填 moonshot-v1-8k-vision-preview
    VISION_KEY = st.secrets["MOONSHOT_API_KEY"] 
    VISION_BASE = "https://api.moonshot.cn/v1"
    VISION_MODEL = "moonshot-v1-8k-vision-preview"

    # 2. 文本配置 (Kimi)
    TEXT_KEY = st.secrets["MOONSHOT_API_KEY"]
    TEXT_BASE = "https://api.moonshot.cn/v1"
    TEXT_MODEL = "moonshot-v1-8k"

    # 3. 绘图配置 (切换为：可图 Kolors)
    # 使用 SiliconFlow 平台，模型换成 Kwai-Kolors/Kolors
    IMG_KEY = st.secrets["SILICON_API_KEY"]
    IMG_BASE = "https://api.siliconflow.cn/v1"
    
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.info("请检查 Secrets 配置")
    st.stop()

# --- 4. 核心功能函数 ---

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def analyze_image(image_file):
    """【眼睛】视觉识别"""
    base64_image = encode_image(image_file)
    client = OpenAI(api_key=VISION_KEY, base_url=VISION_BASE)
    
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请仔细观察这张美食图片。描述它的菜品名称、食材细节、色泽、光线和构图缺点。只输出客观描述，不要废话。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"视觉识别失败: {str(e)}"

def generate_copy(vision_analysis, user_topic):
    """【大脑】撰写文案"""
    client = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    
    system_prompt = """
    你是一名小红书金牌运营。请结合【视觉描述】和【商家信息】，写一篇外卖爆单笔记。
    结构：标题(二极管风格)、正文(痛点+场景+诱人描述)、下单引导、标签。
    要求：分段清晰，多Emoji，语气真诚激动。
    """
    
    user_prompt = f"【视觉描述】：{vision_analysis}\n【商家信息】：{user_topic}"
    
    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.9
    )
    return response.choices[0].message.content

def refine_image(vision_analysis, user_topic):
    """【画手】调用 Kolors (可图) 重绘"""
    
    # 🌟 针对国产模型的优化：直接使用中文 Prompt
    # 我们可以让 Kimi 帮我们把视觉描述优化成一句“可图”听得懂的指令
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    prompt_optimizer = client_text.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{
            "role": "user", 
            "content": f"请根据这个菜品描述：'{vision_analysis}' 和 '{user_topic}'，写一个用于AI绘画的中文提示词。\n要求：包含'专业美食摄影'、'8k超高清'、'色泽诱人'、'电影级光效'等关键词。直接输出提示词，不要解释。"
        }]
    )
    chinese_prompt = prompt_optimizer.choices[0].message.content
    
    # 调用 SiliconFlow 上的 Kolors 模型
    client_img = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    try:
        response = client_img.images.generate(
            model="Kwai-Kolors/Kolors", # 👈 核心修改：这里换成了可图
            prompt=chinese_prompt,
            size="1024x1024",
            n=1
        )
        return response.data[0].url, chinese_prompt
    except Exception as e:
        return f"Error: {str(e)}", ""

# --- 5. 主界面 ---

st.title("🥢 爆款笔记生成器 (可图内核)")
st.caption("Kimi 视觉 + Kimi 写作 + 可图(Kolors) 绘图")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("#### 1️⃣ 上传实拍图")
    uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if uploaded_file:
        st.image(uploaded_file, caption="原图预览", use_container_width=True)

with col_right:
    st.markdown("#### 2️⃣ 补充卖点")
    user_topic = st.text_area("", height=120, placeholder="例如：新品打8折，满20起送，适合加班党...", label_visibility="collapsed")
    
    st.write("") 
    start_btn = st.button("🚀 开始生成 (消耗后台Key)", type="primary", use_container_width=True)

st.divider()

# --- 6. 执行与展示 ---
if start_btn:
    if not uploaded_file:
        st.warning("⚠️ 请先上传图片")
    else:
        with st.status("⚡ AI 全速运转中...", expanded=True) as status:
            
            st.write("👁️ Kimi 正在识别图片...")
            vision_res = analyze_image(uploaded_file)
            if "失败" in vision_res:
                st.error(vision_res)
                st.stop()
            
            st.write("🧠 Kimi 正在写文案...")
            note_res = generate_copy(vision_res, user_topic)
            
            st.write("🎨 可图(Kolors) 正在绘制中式美食大片...")
            # 传入 user_topic 确保画出来的图符合商家卖点
            img_res, prompt_used = refine_image(vision_res, user_topic)
            
            status.update(label="✅ 完成！", state="complete", expanded=False)

        st.balloons()
        
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            st.markdown("### 🖼️ AI 精修图 (Kolors)")
            if "http" in img_res:
                st.image(img_res, use_container_width=True)
                with st.expander("查看绘画提示词"):
                    st.write(prompt_used)
            else:
                st.error(img_res)
        
        with r_col2:
            st.markdown("### 📝 爆款文案")
            with st.container(border=True, height=500):
                st.markdown(note_res)
