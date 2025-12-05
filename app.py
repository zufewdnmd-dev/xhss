import streamlit as st
import base64
import time
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(硅基流动版)", page_icon="🎨", layout="wide")

# CSS 样式
st.markdown("""
<style>
    .stApp { background-color: #FAFAFA; }
    .stButton>button { 
        background-color: #FF6B6B; color: white !important; 
        border-radius: 12px; padding: 12px 28px;
        font-size: 18px; font-weight: bold; width: 100%;
        border: none;
    }
    .stButton>button:hover { background-color: #FF5252; }
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
    
    # C. 绘图：硅基流动 (SiliconFlow)
    IMG_KEY = st.secrets["SILICON_API_KEY"]
    IMG_BASE = "https://api.siliconflow.cn/v1"
    
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.info("请在 Secrets 中配置 DEEPSEEK_API_KEY, MOONSHOT_API_KEY, SILICON_API_KEY")
    st.stop()

# --- 4. 核心功能函数 ---

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def analyze_image_kimi(image_file):
    """【眼睛】Kimi 看图 (带重试机制)"""
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
                        {"type": "text", "text": "分析这张图的菜品、食材、色泽。只输出客观描述。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}
                    ]}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                st.toast(f"⏳ Kimi 服务器繁忙，正在第 {attempt+1} 次重试...", icon="🔄")
                time.sleep(3)
                continue
            elif attempt == max_retries - 1:
                return f"视觉识别失败: {str(e)}"

def generate_copy_deepseek(vision_res, user_topic):
    """【大脑】DeepSeek 写文"""
    client = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    prompt = f"""
    你是一名小红书爆款写手。请结合【视觉描述】和【商家信息】，写一篇外卖种草笔记。
    【视觉描述】：{vision_res}
    【商家信息】：{user_topic}
    要求：标题二极管，正文多Emoji，语气真诚。
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.3
    )
    return response.choices[0].message.content

def generate_image_silicon(vision_res, user_topic):
    """【画手】硅基流动 (调用 Kolors 可图)"""
    
    # 1. 先把描述优化成绘画 Prompt
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    prompt_res = client_text.chat.completions.create(
        model="deepseek-chat",
        messages=[{
            "role": "user", 
            "content": f"根据描述：'{vision_res}' 和卖点 '{user_topic}'，写一个简短的AI绘画提示词（中文）。包含：美食摄影、8k高清、特写、光泽感。直接输出提示词。"
        }]
    )
    draw_prompt = prompt_res.choices[0].message.content

    # 2. 调用画图 API
    client_img = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    
    try:
        response = client_img.images.generate(
            model="Kwai-Kolors/Kolors", # 指定使用可图 (效果最像可灵)
            # 如果想用 FLUX，可以改成: "black-forest-labs/FLUX.1-schnell"
            prompt=draw_prompt,
            size="1024x1024",
            n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {str(e)}"

# --- 5. 主界面 ---

st.title("🎨 外卖爆单神器 (硅基流动版)")
st.caption("Kimi 视觉 · DeepSeek 文案 · Kolors 绘图")

c1, c2 = st.columns([1, 1], gap="large")

with c1:
    st.markdown("#### 1. 上传实拍图")
    uploaded_file = st.file_uploader("", type=["jpg", "png"], label_visibility="collapsed")
    if uploaded_file:
        st.image(uploaded_file, caption="原图", use_container_width=True)

with c2:
    st.markdown("#### 2. 补充卖点")
    user_topic = st.text_area("", height=150, placeholder="例如：招牌红烧肉，肥而不腻...", label_visibility="collapsed")
    
    st.write("")
    if st.button("🚀 呼叫 AI 梦之队开始创作"):
        if not uploaded_file:
            st.warning("⚠️ 请先上传图片")
        else:
            with st.status("⚡ AI 全速运转中...", expanded=True):
                
                st.write("👁️ Kimi 正在识别图片细节...")
                vision_res = analyze_image_kimi(uploaded_file)
                if "失败" in vision_res: st.error(vision_res); st.stop()
                
                st.write("🧠 DeepSeek 正在撰写文案...")
                note_res = generate_copy_deepseek(vision_res, user_topic)
                
                st.write("🎨 可图 (Kolors) 正在绘制美食大片...")
                img_res = generate_image_silicon(vision_res, user_topic)
                
            st.success("✅ 完成！")
            
            r1, r2 = st.columns(2)
            with r1:
                st.markdown("### 🖼️ 精修生成图")
                if "http" in img_res:
                    st.image(img_res, use_container_width=True)
                else:
                    st.error(img_res)
            with r2:
                st.markdown("### 📝 爆款文案")
                with st.container(border=True, height=500):
                    st.markdown(note_res)
