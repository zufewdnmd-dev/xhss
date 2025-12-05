import streamlit as st
import base64
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(极简版)", page_icon="🔥", layout="wide")

# 注入 CSS 样式 (隐藏掉 Streamlit 自带的菜单，让界面像原生 App)
st.markdown("""
<style>
    .stApp { background-color: #F8F5F2; }
    h1, h2, h3 { color: #2C3E50 !important; }
    .stButton>button { 
        background-color: #FF6B6B; color: white !important; 
        border-radius: 12px; border: none; padding: 12px 28px;
        font-size: 18px; font-weight: bold;
    }
    .stButton>button:hover { background-color: #FF4757; transform: scale(1.02); }
    /* 隐藏右上角汉堡菜单和页脚 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 身份验证 (只保留密码锁) ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("## 🔒 内部系统登录")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("解锁"):
        # 从后台获取密码，默认 123456
        if pwd == st.secrets.get("APP_PASSWORD", "123456"):
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("❌ 密码错误")
    st.stop()

# --- 3. 后台静默加载配置 (核心修改) ---
# 这里不再让用户选，而是直接读取 Secrets 并指定最佳模型
try:
    # 1. 视觉配置 (GPT-4o)
    VISION_KEY = st.secrets["VISION_API_KEY"]
    VISION_BASE = "https://api.openai.com/v1"
    VISION_MODEL = "gpt-4o"

    # 2. 文本配置 (DeepSeek)
    TEXT_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TEXT_BASE = "https://api.deepseek.com"
    TEXT_MODEL = "deepseek-chat"

    # 3. 绘图配置 (SiliconFlow FLUX)
    IMG_KEY = st.secrets["SILICON_API_KEY"]
    IMG_BASE = "https://api.siliconflow.cn/v1"
    
except Exception as e:
    st.error(f"❌ 系统配置缺失: {e}")
    st.info("请在 Streamlit Cloud 的 Secrets 中配置 VISION_API_KEY, DEEPSEEK_API_KEY 和 SILICON_API_KEY")
    st.stop()

# --- 4. 核心功能函数 ---

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def analyze_image(image_file):
    """【眼睛】调用 GPT-4o 看图"""
    base64_image = encode_image(image_file)
    client = OpenAI(api_key=VISION_KEY, base_url=VISION_BASE)
    
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请以专业美食摄影师的视角描述这张图。包含：菜品名、食材细节、色泽、光影缺陷。只输出描述，不要废话。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"视觉识别失败: {str(e)}"

def generate_copy(vision_analysis, user_topic):
    """【大脑】调用 DeepSeek 写文"""
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
        temperature=0.85
    )
    return response.choices[0].message.content

def refine_image(vision_analysis):
    """【画手】调用 FLUX 重绘"""
    # 构造专业提示词
    magic_prompt = f"Professional food photography, 8k, masterpiece, {vision_analysis}, cinematic lighting, appetizing, high resolution, soft focus background"
    
    client = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    try:
        response = client.images.generate(
            model="black-forest-labs/FLUX.1-schnell",
            prompt=magic_prompt,
            size="1024x1024",
            n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {str(e)}"

# --- 5. 主界面 (极简风格) ---

st.title("🔥 爆款笔记生成器")
st.caption("AI 全自动工作流：看图 -> 写文 -> 修图")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("#### 1️⃣ 上传实拍图")
    uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if uploaded_file:
        st.image(uploaded_file, caption="原图预览", use_container_width=True)

with col_right:
    st.markdown("#### 2️⃣ 补充卖点")
    user_topic = st.text_area("", height=120, placeholder="例如：新品打8折，满20起送，适合加班党...", label_visibility="collapsed")
    
    st.write("") # 占位
    start_btn = st.button("🚀 开始生成 (自动消耗后台 Key)", type="primary", use_container_width=True)

st.divider()

# --- 6. 执行与展示 ---
if start_btn:
    if not uploaded_file:
        st.warning("⚠️ 请先上传图片，AI 需要“看见”菜品才能工作！")
    else:
        # 进度状态机
        with st.status("⚡ AI 正在全速运转中...", expanded=True) as status:
            
            st.write("👁️ GPT-4o 正在识别图片细节...")
            vision_res = analyze_image(uploaded_file)
            if "失败" in vision_res:
                st.error(vision_res)
                st.stop()
            
            st.write("🧠 DeepSeek 正在撰写种草文案...")
            note_res = generate_copy(vision_res, user_topic)
            
            st.write("🎨 FLUX 正在重绘 4K 级美食大片...")
            img_res = refine_image(vision_res)
            
            status.update(label="✅ 生成完毕！", state="complete", expanded=False)

        # 结果展示
        st.balloons()
        
        # 两列布局展示结果
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            st.markdown("### 🖼️ AI 精修图")
            if "http" in img_res:
                st.image(img_res, use_container_width=True)
            else:
                st.error(img_res)
        
        with r_col2:
            st.markdown("### 📝 爆款文案")
            with st.container(border=True, height=500):
                st.markdown(note_res)
