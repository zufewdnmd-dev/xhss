import streamlit as st
import base64
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单笔记生成器", page_icon="🛵", layout="centered")

# 自定义样式
st.markdown("""
<style>
    .stApp { background-color: #F3F0E9; }
    h1, h2, h3, p, div { color: #1F3556 !important; }
    div.stButton > button { background-color: #D67052; color: white !important; border-radius: 8px; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 密码验证 (必须保留，否则你的余额会被刷光) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown("### 🔒 内部应用，请输入访问密码")
    password_input = st.text_input("Access Password", type="password", label_visibility="collapsed")
    
    if st.button("解锁应用"):
        # 从后台获取密码，如果没有设置则默认 123456
        correct_password = st.secrets.get("APP_PASSWORD", "123456")
        if password_input == correct_password:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ 密码错误")
    return False

if not check_password():
    st.stop()

# --- 3. 侧边栏：模型选择 (Key 已隐藏) ---
with st.sidebar:
    st.header("🧠 模型配置")
    
    # 这里只保留你是真的有 Key 的模型
    provider = st.selectbox(
        "选择生成引擎",
        ["DeepSeek (深度求索)", "Moonshot (Kimi)", "OpenAI (GPT-4o)"]
    )
    
    # --- 核心修改：自动从后台 Secrets 获取 Key ---
    api_key = None
    base_url = None
    model_name = None

    try:
        if provider == "DeepSeek (深度求索)":
            api_key = st.secrets["DEEPSEEK_API_KEY"]
            base_url = "https://api.deepseek.com"
            model_name = "deepseek-chat"
            st.caption("✅ 已接入 DeepSeek Pro")
            
        elif provider == "Moonshot (Kimi)":
            api_key = st.secrets["MOONSHOT_API_KEY"]
            base_url = "https://api.moonshot.cn/v1"
            model_name = "moonshot-v1-8k"
            st.caption("✅ 已接入 Kimi")
            
        elif provider == "OpenAI (GPT-4o)":
            api_key = st.secrets["OPENAI_API_KEY"]
            base_url = "https://api.openai.com/v1"
            model_name = "gpt-4o"
            
    except Exception:
        st.error(f"❌ 后台未配置 {provider} 的 API Key，请联系管理员。")
        st.stop()

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
    topic = st.text_area(
        "Step 2: 输入商家/菜品信息 (必填)", 
        height=200, 
        placeholder="请提供关键信息：\n1. 店名：\n2. 位置：\n3. 招牌菜：\n4. 价格：\n5. 亮点：..."
    )
    generate_btn = st.button("✨ 生成外卖种草文", use_container_width=True)

# --- 5. 辅助函数 ---
def encode_image(file):
    return base64.b64encode(file.getvalue()).decode('utf-8')

# --- 6. 生成逻辑 ---
if generate_btn:
    if not topic:
        st.warning("⚠️ 请输入商家信息")
    else:
        try:
            with st.status("🤖 AI 正在撰写文案...", expanded=True):
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                system_prompt = """
                你是一名深耕本地生活赛道的小红书运营操盘手。
                目标：为外卖商家写高转化笔记。
                人设：爱点外卖的打工人/大学生，语气亲切真实。
                
                【结构要求】
                A. 爆款标题区 (5-10个备选)
                B. 正文笔记区 (600-1000字，包含痛点钩子、场景、菜品亮点、真实体验、下单引导)
                C. 推荐标签区
                
                【输出格式】请清晰分段，不要一次性输出一大坨。
                """
                
                messages = [{"role": "system", "content": system_prompt}]
                
                # DeepSeek/Kimi 纯文本处理
                is_text_only = "deepseek" in model_name.lower() or "moonshot" in model_name.lower()
                
                if is_text_only:
                    user_content = f"商家信息：\n{topic}"
                    if uploaded_file:
                        st.info("ℹ️ 当前模型仅基于文字生成。")
                    messages.append({"role": "user", "content": user_content})
                else:
                    content = [{"type": "text", "text": f"商家信息：{topic}"}]
                    if uploaded_file:
                        base64_img = encode_image(uploaded_file)
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                        })
                    messages.append({"role": "user", "content": content})

                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.85
                )
                result_text = response.choices[0].message.content
                
            st.success("🎉 生成成功！")
            st.markdown(result_text)
            
        except Exception as e:
            st.error(f"❌ 生成失败: {str(e)}")
