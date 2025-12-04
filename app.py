import streamlit as st
import base64
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="爆款笔记生成器", page_icon="✍️", layout="centered")

# 自定义样式 (你的暖米色风格)
st.markdown("""
<style>
    .stApp { background-color: #F3F0E9; }
    h1, h2, h3, p, div { color: #1F3556 !important; }
    div.stButton > button { background-color: #D67052; color: white !important; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏：配置区 ---
with st.sidebar:
    st.header("⚙️ 核心配置")
    # 默认选 DeepSeek
    api_source = st.selectbox("选择模型服务商", ["DeepSeek", "Moonshot (Kimi)", "OpenAI (官方)"])
    api_key = st.text_input("请输入 API Key", type="password")
    
    # 自动配置 DeepSeek
    if api_source == "DeepSeek":
        base_url = "https://api.deepseek.com"
        model_name = "deepseek-chat"
        st.info("💡 注意：DeepSeek 目前主要支持文字生成，图片识别功能可能不可用。")
    elif api_source == "Moonshot (Kimi)":
        base_url = "https://api.moonshot.cn/v1"
        model_name = "moonshot-v1-8k"
    elif api_source == "OpenAI (官方)":
        base_url = "https://api.openai.com/v1"
        model_name = "gpt-4o"

# --- 3. 主界面 ---
st.title("✍️ 爆款笔记生成器 (DeepSeek版)")
st.caption("Warm Academic Humanism Style")

st.divider()

col1, col2 = st.columns([1, 1])
with col1:
    uploaded_file = st.file_uploader("Step 1: 上传参考图 (DeepSeek模式下仅作展示)", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="已上传素材", use_container_width=True)

with col2:
    # 增加文字输入的权重，因为DeepSeek主要靠这个
    topic = st.text_area("Step 2: 笔记主题 & 细节", height=150, 
                        placeholder="🔥 必填！因为DeepSeek看不到图，请详细描述产品。\n例如：这是一个红色的戴森吹风机，适合送女友...")
    generate_btn = st.button("✨ 开始创作", use_container_width=True)

# --- 4. 辅助函数：处理图片 ---
def encode_image(file):
    return base64.b64encode(file.getvalue()).decode('utf-8')

# --- 5. 核心逻辑 ---
if generate_btn:
    if not api_key:
        st.error("⚠️ 请先在左侧侧边栏填入 API Key")
    elif not topic:
        st.warning("⚠️ 使用 DeepSeek 时，必须输入【笔记主题】来告诉 AI 写什么！")
    else:
        try:
            with st.status("🤖 AI 正在疯狂创作中...", expanded=True):
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # --- 核心修改：针对 DeepSeek 的特殊处理 ---
                system_prompt = """
                你是一个资深的小红书博主。请根据用户的主题，写一篇爆款笔记。
                风格要求：
                1. 标题20字以内，二极管风格（如“绝了、哭死”）。
                2. 正文分段，大量使用Emoji(🌟🔥✨)。
                3. 语气真诚、激动，像闺蜜安利。
                4. 结尾加5-8个标签。
                """

                # 准备消息
                messages = [{"role": "system", "content": system_prompt}]

                # 这里的逻辑变了：只有 OpenAI 才发图片，DeepSeek 只发文字
                if api_source == "DeepSeek":
                    # DeepSeek 模式：只发送文字
                    user_content = f"请写一篇关于这个主题的小红书笔记：{topic}"
                    if uploaded_file:
                        st.info("⚠️ 提示：已忽略图片（DeepSeek 暂不支持看图），仅根据文字生成。")
                    
                    messages.append({"role": "user", "content": user_content})
                
                else:
                    # 其他模式（OpenAI）：发送图片 + 文字
                    content_payload = [{"type": "text", "text": f"主题：{topic}"}]
                    if uploaded_file:
                        base64_img = encode_image(uploaded_file)
                        content_payload.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                        })
                    messages.append({"role": "user", "content": content_payload})

                # 发起请求
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=1.3 # DeepSeek 稍微调高创造性
                )
                
                result_text = response.choices[0].message.content
                
            st.success("🎉 生成成功！")
            st.markdown(result_text)
            
        except Exception as e:
            st.error(f"❌ 还是报错了：{str(e)}")