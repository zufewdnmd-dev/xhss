import streamlit as st
import base64
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(多模态终极版)", page_icon="🔥", layout="wide")

# 注入高定 CSS 样式
st.markdown("""
<style>
    .stApp { background-color: #F8F5F2; } /* 柔和米白 */
    h1, h2, h3 { color: #2C3E50 !important; font-family: 'Helvetica Neue', sans-serif; }
    .stButton>button { 
        background-color: #FF6B6B; 
        color: white !important; 
        border-radius: 12px; 
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #FF4757; transform: scale(1.02); }
    .reportview-container .main .block-container { max-width: 1200px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 安全验证与配置 ---
def check_auth():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    
    # 侧边栏配置区
    with st.sidebar:
        st.title("⚙️ 控制台")
        
        # 1. 访问密码
        if not st.session_state.auth:
            pwd = st.text_input("请输入访问密码", type="password")
            if pwd == st.secrets.get("APP_PASSWORD", "123456"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.warning("🔒 未解锁")
                st.stop()
        
        st.success("✅ 已解锁")
        st.divider()
        
        # 2. 模型配置 (支持分别配置，追求最佳效果)
        st.markdown("### 🧠 模型配置")
        
        # A. 视觉模型 (眼睛) - 建议 GPT-4o 或 Qwen-VL
        vision_provider = st.selectbox("👁️ 视觉模型 (负责看图)", ["OpenAI (GPT-4o)", "Aliyun (通义千问VL)", "自定义"])
        vision_key = st.text_input("Vision API Key", type="password", value=st.secrets.get("VISION_API_KEY", ""))
        
        # B. 文本模型 (大脑) - 建议 DeepSeek
        text_provider = st.selectbox("📝 文本模型 (负责写文)", ["DeepSeek-V3", "Moonshot (Kimi)", "OpenAI"])
        text_key = st.text_input("Text API Key", type="password", value=st.secrets.get("DEEPSEEK_API_KEY", ""))
        
        # C. 绘图模型 (手) - 建议 SiliconFlow FLUX
        img_provider = st.selectbox("🎨 绘图模型 (负责修图)", ["SiliconFlow (FLUX.1)"])
        img_key = st.text_input("Image API Key", type="password", value=st.secrets.get("SILICON_API_KEY", ""))

        return {
            "vision": (vision_provider, vision_key),
            "text": (text_provider, text_key),
            "img": (img_provider, img_key)
        }

config = check_auth()

# --- 3. 核心功能函数 ---

def encode_image(uploaded_file):
    """将图片转为 Base64 供 AI 观看"""
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def analyze_image(image_file, provider_config):
    """【眼睛】视觉分析：调用多模态模型看图"""
    provider, key = provider_config
    if not key: return "Error: 未配置视觉 API Key"
    
    base64_image = encode_image(image_file)
    
    # 设置 API 端点 (根据选择调整)
    if "OpenAI" in provider:
        base_url, model = "https://api.openai.com/v1", "gpt-4o"
    elif "Aliyun" in provider:
        base_url, model = "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-vl-max"
    else:
        base_url, model = "https://api.openai.com/v1", "gpt-4o" # 默认回退

    client = OpenAI(api_key=key, base_url=base_url)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请用专业的摄影师视角详细描述这张美食图片。包含：菜品名称、主要食材、色泽、摆盘构图、光线氛围。如果你觉得图片不够好，请指出需要改进的地方（如光线太暗、构图杂乱）。只输出描述，不要废话。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"视觉识别失败: {str(e)}"

def generate_copy(vision_analysis, user_topic, provider_config):
    """【大脑】文案生成：DeepSeek 结合视觉信息写文"""
    provider, key = provider_config
    if not key: return "Error: 未配置文本 API Key"
    
    if "DeepSeek" in provider:
        base_url, model = "https://api.deepseek.com", "deepseek-chat"
    elif "Moonshot" in provider:
        base_url, model = "https://api.moonshot.cn/v1", "moonshot-v1-8k"
    else:
        base_url, model = "https://api.openai.com/v1", "gpt-4o"

    client = OpenAI(api_key=key, base_url=base_url)
    
    system_prompt = """
    你是一名小红书金牌运营。请结合【视觉描述】和【商家补充信息】，写一篇极具诱惑力的外卖种草笔记。
    要求：标题二极管，正文多Emoji，痛点场景化，引导下单。
    """
    
    user_prompt = f"""
    【AI视觉描述（图片内容）】：{vision_analysis}
    【商家补充信息（价格/活动）】：{user_topic}
    
    请据此生成笔记。
    """
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content

def refine_image(vision_analysis, provider_config):
    """【画手】图片精修：基于视觉描述重绘"""
    _, key = provider_config
    if not key: return "Error: 未配置绘图 API Key"
    
    # 1. 先把视觉描述翻译成英文 Prompt (简易版直接用DeepSeek翻译，这里为了代码简洁直接构造)
    # 在实际最佳实践中，应该先让 LLM 优化 prompt，这里直接使用增强模板
    magic_prompt = f"Professional food photography, 8k, masterpiece, {vision_analysis}, cinematic lighting, appetizing, high resolution, soft focus background"
    
    client = OpenAI(api_key=key, base_url="https://api.siliconflow.cn/v1")
    
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

# --- 4. 主界面布局 ---

st.title("🔥 爆款笔记生成器 (AI多模态版)")
st.caption("视觉识别 + 深度写作 + 仿真重绘")

col_left, col_right = st.columns([1, 1.2], gap="large")

with col_left:
    st.markdown("### 📸 素材上传")
    uploaded_file = st.file_uploader("上传商家实拍图", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="原始图片", use_container_width=True)

with col_right:
    st.markdown("### 📝 补充信息")
    user_topic = st.text_area("补充细节 (必填)", height=100, placeholder="例如：新店开业打8折，满20起送，适合加班党...")
    
    start_btn = st.button("🚀 开始多模态全自动生成", type="primary", use_container_width=True)

st.divider()

# --- 5. 执行逻辑 ---
if start_btn:
    if not uploaded_file:
        st.warning("⚠️ 请先上传一张图片，让 AI '看' 一下！")
    else:
        # 1. 视觉分析阶段
        with st.status("👁️ AI 正在观察图片细节...", expanded=True) as status:
            st.write("正在识别菜品、构图与光影...")
            vision_result = analyze_image(uploaded_file, config["vision"])
            
            if "Error" in vision_result or "失败" in vision_result:
                st.error(vision_result)
                status.update(label="❌ 视觉识别失败", state="error")
                st.stop()
            else:
                st.info(f"✅ 视觉识别完成：{vision_result[:50]}...")
            
            # 2. 文案生成阶段
            st.write("🧠 正在根据视觉信息撰写爆款文案...")
            note_result = generate_copy(vision_result, user_topic, config["text"])
            
            # 3. 图片精修阶段
            st.write("🎨 FLUX 正在根据视觉理解重绘大片...")
            refined_img_url = refine_image(vision_result, config["img"])
            
            status.update(label="✅ 全流程完成！", state="complete", expanded=False)

        # --- 6. 结果展示 ---
        st.success("🎉 生成成功！")
        
        res_col1, res_col2 = st.columns(2)
        
        with res_col1:
            st.markdown("#### 🖼️ AI 精修大片")
            if "http" in refined_img_url:
                st.image(refined_img_url, use_container_width=True)
                st.caption("💡 提示：这是 AI 基于原图构图重绘的 4K 图")
            else:
                st.error(refined_img_url)
                
        with res_col2:
            st.markdown("#### 📝 爆款小红书文案")
            with st.container(border=True, height=500):
                st.markdown(note_result)
