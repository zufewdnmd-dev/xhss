import streamlit as st
import base64
from openai import OpenAI

# --- 1. 页面配置 (极简全屏) ---
st.set_page_config(page_title="外卖爆单神器", page_icon="🥢", layout="wide")

# 注入 CSS (隐藏菜单，优化按钮)
st.markdown("""
<style>
    .stApp { background-color: #FAFAFA; }
    h1, h2, h3 { color: #333 !important; font-family: sans-serif; }
    /* 按钮样式：大红色，显眼 */
    .stButton>button { 
        background-color: #FF4757; color: white !important; 
        border-radius: 12px; border: none; padding: 15px 32px;
        font-size: 20px; font-weight: bold; width: 100%;
    }
    .stButton>button:hover { background-color: #FF6B81; }
    /* 隐藏 Streamlit 自带的汉堡菜单和页脚 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 身份验证 (后台密码锁) ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("## 🔒 内部系统登录")
        pwd = st.text_input("请输入访问密码", type="password", label_visibility="collapsed")
        if st.button("解锁应用"):
            # 默认密码 123456，建议在 Secrets 修改
            if pwd == st.secrets.get("APP_PASSWORD", "123456"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("❌ 密码错误")
    st.stop()

# --- 3. 后台加载配置 (核心：DeepSeek + Kimi + Kolors) ---
try:
    # A. 文本模型：DeepSeek (写文案)
    TEXT_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TEXT_BASE = "https://api.deepseek.com"
    TEXT_MODEL = "deepseek-chat"

    # B. 视觉模型：Kimi (看图)
    VISION_KEY = st.secrets["MOONSHOT_API_KEY"]
    VISION_BASE = "https://api.moonshot.cn/v1"
    VISION_MODEL = "moonshot-v1-8k-vision-preview"

    # C. 绘图模型：可图 Kolors (画图) - 使用 SiliconFlow 调用
    IMG_KEY = st.secrets["SILICON_API_KEY"]
    IMG_BASE = "https://api.siliconflow.cn/v1"
    
except Exception as e:
    st.error(f"❌ 后台配置缺失: {e}")
    st.info("请检查 Secrets 中是否配置了 DEEPSEEK_API_KEY, MOONSHOT_API_KEY 和 SILICON_API_KEY")
    st.stop()

# --- 4. 智能功能函数 ---

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def analyze_image(image_file):
    """【眼睛】Kimi 看图"""
    base64_image = encode_image(image_file)
    client = OpenAI(api_key=VISION_KEY, base_url=VISION_BASE)
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": "你是专业的美食摄影师。"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "分析这张图的菜品、食材、色泽和构图。只输出描述，不要废话。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"视觉识别失败: {str(e)}"

def generate_copy(vision_analysis, user_topic):
    """【大脑】DeepSeek 写文"""
    client = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    
    system_prompt = """
    你是一名小红书爆款运营。请结合【视觉描述】和【商家信息】，写一篇外卖种草笔记。
    要求：
    1. 标题吸引眼球（二极管/感叹号）。
    2. 正文分段清晰，包含痛点钩子、真实体验、引导下单。
    3. 多使用Emoji 🔥✨😋。
    """
    
    user_prompt = f"【视觉描述】：{vision_analysis}\n【商家信息】：{user_topic}"
    
    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=1.3 # DeepSeek 稍微调高温度更活泼
    )
    return response.choices[0].message.content

def refine_image(vision_analysis, user_topic):
    """【画手】可图 (Kolors) 重绘"""
    
    # 1. 先让 DeepSeek 把描述变成绘画提示词
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    prompt_res = client_text.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{
            "role": "user", 
            "content": f"根据描述：'{vision_analysis}' 和卖点 '{user_topic}'，写一个简短的AI绘画提示词（中文）。包含：美食摄影、8k高清、特写、光泽感。"
        }]
    )
    draw_prompt = prompt_res.choices[0].message.content
    
    # 2. 调用 Kolors 画图
    client_img = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    try:
        response = client_img.images.generate(
            model="Kwai-Kolors/Kolors", # 指定使用可图
            prompt=draw_prompt,
            size="1024x1024",
            n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {str(e)}"

# --- 5. 主界面布局 ---

st.title("🥢 外卖爆单神器")
st.caption("DeepSeek 文案 + Kimi 视觉 + 可图精修")

c1, c2 = st.columns([1, 1], gap="large")

with c1:
    st.markdown("#### 1. 上传实拍图")
    uploaded_file = st.file_uploader("", type=["jpg", "png"], label_visibility="collapsed")
    if uploaded_file:
        st.image(uploaded_file, caption="原图", use_container_width=True)

with c2:
    st.markdown("#### 2. 补充卖点")
    user_topic = st.text_area("", height=150, placeholder="例如：新品牛肉面，肉超多，只要18元...", label_visibility="collapsed")
    
    st.write("")
    if st.button("🚀 一键生成爆款 (DeepSeek + 可图)"):
        if not uploaded_file:
            st.warning("⚠️ 请先上传图片")
        else:
            with st.status("⚡ AI 梦之队正在协作...", expanded=True):
                
                st.write("👁️ Kimi 正在看图...")
                vision_res = analyze_image(uploaded_file)
                
                st.write("🧠 DeepSeek 正在写文案...")
                note_res = generate_copy(vision_res, user_topic)
                
                st.write("🎨 可图 (Kolors) 正在修图...")
                img_res = refine_image(vision_res, user_topic)
                
            st.success("✅ 完成！")
            
            # 展示结果
            res_c1, res_c2 = st.columns(2)
            with res_c1:
                st.markdown("### 🖼️ 精修效果")
                if "http" in img_res:
                    st.image(img_res, use_container_width=True)
                else:
                    st.error(img_res)
            with res_c2:
                st.markdown("### 📝 爆款文案")
                with st.container(border=True, height=500):
                    st.markdown(note_res)
