import streamlit as st
import base64
import time
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(Jeniya Flux版)", page_icon="🍱", layout="wide")

# CSS 样式 (保持暖米色)
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
    TEXT_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TEXT_BASE = "https://api.deepseek.com"
    
    VISION_KEY = st.secrets["MOONSHOT_API_KEY"]
    VISION_BASE = "https://api.moonshot.cn/v1"
    
    # Jeniya 中转配置
    IMG_KEY = st.secrets["JENIYA_API_KEY"]
    IMG_BASE = "https://jeniya.top/v1" 
    
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.info("请检查 Secrets 是否包含 JENIYA_API_KEY, DEEPSEEK_API_KEY, MOONSHOT_API_KEY")
    st.stop()

# --- 4. 核心功能函数 ---

def encode_image_to_base64(uploaded_file):
    """图片转 Base64"""
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def analyze_image_kimi(image_file):
    """【眼睛】Kimi 识别菜品名称"""
    encoded_string = encode_image_to_base64(image_file)
    client = OpenAI(api_key=VISION_KEY, base_url=VISION_BASE)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="moonshot-v1-8k-vision-preview",
                messages=[
                    {"role": "system", "content": "你是专业美食摄影师。"},
                    {"role": "user", "content": [
                        {"type": "text", "text": "请精准识别图中的主菜品名称（如：红烧牛肉面）。只输出菜名，不要任何修饰语。"},
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
    """【大脑】DeepSeek 写文案"""
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

def generate_image_jeniya_flux(vision_res):
    """
    【画手】通过 Jeniya 中转调用 FLUX
    模式：文生图 (Text-to-Image)
    """
    # 1. 场景模板 (因为是重绘，必须描述得非常详细)
    RAW_TEMPLATE = """
    请生成一张超写实的美食摄影图片。
    主菜是：【{main_dish}】，请将其放置在画面正中央，色泽诱人，热气腾腾，展现食物的纹理。
    
    环境布置要求（温馨一人食Plog风格）：
    1. 背景：暖色调的家庭餐桌，铺着编织餐垫，有生活气息。
    2. 核心道具：正前方放置一个iPad，屏幕上清晰显示《蜡笔小新》动画片。
    3. 配菜：主菜周围摆放一盘大虾、一碗蒸蛋、一碗沙拉、一碟小菜。
    4. 饮品：旁边放一瓶绿色的韩式烧酒。
    5. 氛围：自然窗光，景深效果（背景微虚），4k分辨率，极致细节，看起来像iPhone实拍。
    """
    
    chinese_requirement = RAW_TEMPLATE.format(main_dish=vision_res)

    # 2. DeepSeek 翻译为英文 (Flux 对英文 Prompt 支持最好)
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    system_prompt_for_img = """
    You are an expert Prompt Engineer for FLUX.1.
    Translate the user's description into a highly detailed English prompt.
    CRITICAL: Ensure the "iPad with Crayon Shin-chan" and "Soju bottle" are included.
    Style: Photorealistic, cinematic lighting, 8k, shot on iPhone style.
    Output ONLY the English prompt.
    """
    translation_resp = client_text.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt_for_img}, 
            {"role": "user", "content": chinese_requirement}
        ]
    )
    english_prompt = translation_resp.choices[0].message.content

    # 3. 调用中转 API (OpenAI 兼容模式)
    client_img = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    
    try:
        # 使用标准的 OpenAI 绘图接口
        response = client_img.images.generate(
            model="gemini-2.5-flash-image", # 👈 如果报错，请尝试改成 'flux-pro' 或 'flux-schnell'
            prompt=english_prompt,
            size="1024x1024",
            n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {str(e)}"

# --- 5. 主界面 ---

st.title("🍱 外卖爆单神器 (Jeniya Flux版)")
st.caption("Kimi 视觉 -> DeepSeek 润色 -> FLUX (via Jeniya)")

# --- 输入区 ---
with st.container(border=True):
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("#### 1. 批量上传实拍图 (最多5张)")
        uploaded_files = st.file_uploader("", type=["jpg", "png"], accept_multiple_files=True, label_visibility="collapsed")
        valid_files = []
        if uploaded_files:
            if len(uploaded_files) > 5:
                st.warning("⚠️ 超过5张，仅处理前5张。")
                valid_files = uploaded_files[:5]
            else:
                valid_files = uploaded_files
            cols = st.columns(len(valid_files))
            for i, file in enumerate(valid_files):
                cols[i].image(file, caption=f"图 {i+1}", use_container_width=True)

    with c2:
        st.markdown("#### 2. 通用卖点")
        user_topic = st.text_area("", height=150, placeholder="例如：新品上市...", label_visibility="collapsed")
        st.write("")
        start_btn = st.button("🚀 启动中转生成")

# --- 处理区 ---
if start_btn:
    if not valid_files:
        st.warning("⚠️ 请先上传图片")
    elif not user_topic:
         st.warning("⚠️ 请输入卖点")
    else:
        final_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_container = st.container()
        total_files = len(valid_files)
        
        try:
            for i, file in enumerate(valid_files):
                current_idx = i + 1
                status_text.markdown(f"### ⚡ 正在处理第 {current_idx}/{total_files} 张...")
                
                with st.spinner(f"🤖 正在调用中转 Flux 生成中..."):
                    # 1. Kimi 识别
                    vision_res = analyze_image_kimi(file)
                    if "Error" in vision_res: raise Exception(f"识别失败: {vision_res}")

                    # 2. DeepSeek 写文
                    note_res = generate_copy_deepseek(vision_res, user_topic)

                    # 3. Flux 中转绘图
                    img_res = generate_image_jeniya_flux(vision_res)
                    
                    if "Error" in img_res: 
                        st.error(f"第 {current_idx} 张图生成失败: {img_res}")
                        img_res = None
                    
                    final_results.append({
                        "id": current_idx, "original": file, "generated_img": img_res, "note": note_res
                    })

                progress_bar.progress(current_idx / total_files)

            status_text.success(f"✅ 全部 {total_files} 张图片处理完成！")
            time.sleep(1)
            status_text.empty()
            progress_bar.empty()

            with result_container:
                st.divider()
                st.markdown("### 🎉 Flux 生成结果")
                for res in final_results:
                    with st.expander(f"🖼️ 第 {res['id']} 组结果 (点击展开)", expanded=(res['id']==1)):
                        rc1, rc2 = st.columns([2, 3], gap="medium")
                        with rc1:
                            st.markdown("**对比视图**")
                            col_orig, col_gen = st.columns(2)
                            with col_orig:
                                st.image(res["original"], caption="原图", use_container_width=True)
                            with col_gen:
                                if res["generated_img"]:
                                    st.image(res["generated_img"], caption="Flux 重绘", use_container_width=True)
                                else:
                                    st.warning("生成失败")
                        with rc2:
                            st.markdown("**爆款文案**")
                            with st.container(border=True, height=400):
                                st.markdown(res["note"])
        
        except Exception as e:
            status_text.error(f"任务中断: {str(e)}")
            progress_bar.empty()

