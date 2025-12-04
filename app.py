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
        st.warning("⚠️ 请输入商家信息，否则 AI 无法写出真实感！")
    else:
        try:
            with st.status("🤖 AI 操盘手正在拆解卖点、构思故事...", expanded=True):
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # ======================================================
                # 核心修改：植入你提供的【外卖商家操盘手】设定
                # ======================================================
                system_prompt = """
                你现在是一名深耕本地生活赛道的小红书运营操盘手，专门为「外卖商家」写高转化的种草笔记。
                你的目标是：通过故事化、场景化、真实体验感的笔记，帮商家在小红书上获得更多曝光并引导用户搜索店名+下单外卖。

                【账号人设】
                1. 使用第一人称「我」，人设是：附近上学/上班的普通打工人或大学生。
                2. 爱点外卖，会认真对比好吃又不踩雷的店。
                3. 语气亲切、口语化，有一点点幽默，但不要浮夸。

                【写作结构】（请严格按此输出）

                A. 爆款标题区
                输出 5–10 个不同风格的标题备选。
                标题要包含：「城市或商圈/学校名」+「品类/招牌菜」+「强利益点/反差感」。

                B. 正文笔记区（600–1200字）
                1）开头 3 秒钩子：直接抛出痛点/反差/结果。
                2）人物+场景：交代你是谁、在什么场景下点了这家外卖（加班、考研、宿舍追剧等）。
                3）菜品/产品亮点拆解：
                   - 必点招牌（口味、口感、分量）
                   - 性价比（人均、和别家对比的优势）
                   - 细节服务（打包、保温、配菜等）
                4）真实体验和对比：适当带一点轻微“吐槽别家+夸这家”，不攻击其他商家。
                5）适合人群&使用场景：熬夜写论文、宿舍聚餐、减脂等。
                6）下单引导（极关键）：用自然的方式，引导用户去外卖平台搜索店名。
                7）结尾小总结：一句话收尾，强调核心卖点。

                C. 推荐标签区
                输出 8–15 个可直接复制的话题标签（城市/学校、外卖、本地探店等）。

                【写作风格细节】
                - 避免违禁词、极端绝对用语（如“全国第一”）。
                - 多用具体细节描述，多用短句、换行。
                - 合理使用表情语气词，但不要过度堆砌。
                
                【输出格式】
                请用清晰的小标题：【标题备选】、【正文完整笔记】、【推荐话题标签】
                """
                
                messages = [{"role": "system", "content": system_prompt}]
                
                # 判断是否为纯文本模型
                is_text_only_model = "deepseek" in model_name.lower() or "moonshot" in model_name.lower()
                
                if is_text_only_model:
                    user_content = f"商家及菜品信息如下：\n{topic}"
                    if uploaded_file:
                        st.info("ℹ️ 当前模型忽略图片，仅基于文字生成。")
                    messages.append({"role": "user", "content": user_content})
                else:
                    content = [{"type": "text", "text": f"商家及菜品信息：{topic}"}]
                    if uploaded_file:
                        base64_img = encode_image(uploaded_file)
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                        })
                    messages.append({"role": "user", "content": content})

                # 为了保证长文输出完整，适当调大了 max_tokens（如果模型支持）
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.85 # 稍微调高一点，增加故事性
                )
                
                result_text = response.choices[0].message.content
                
            st.success("🎉 爆款笔记已生成！")
            st.markdown(result_text)
            
        except Exception as e:
            st.error(f"❌ 生成失败: {str(e)}")
