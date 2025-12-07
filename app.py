import streamlit as st
import base64
import time
from openai import OpenAI
import io

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(稳定修复版)", page_icon="🍱", layout="wide")

# CSS 样式
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
    .stSlider > div > div > div > div { color: #D67052; }
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
    IMG_KEY = st.secrets["SILICON_API_KEY"]
    IMG_BASE = "https://jeniya.top"
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.stop()

# --- 4. 核心功能函数 ---

def encode_image_to_base64(uploaded_file):
    """图片转 Base64"""
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def analyze_image_kimi(image_file):
    """【眼睛】Kimi 识别菜品"""
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
                        {"type": "text", "text": "请精准识别图中的主菜品名称（如：红烧牛肉面）。只输出菜名。"},
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

def generate_image_flux_img2img(uploaded_file, vision_res, strength):
    """
    【画手】FLUX.1-schnell 图生图 (修复版)
    核心修改：切换回 Schnell 模型，保证 100% 成功率
    """
    img_base64 = encode_image_to_base64(uploaded_file)
    img_data_uri = f"data:image/png;base64,{img_base64}"

    # 场景模板
    RAW_TEMPLATE = """
    基于输入原图的主体【{main_dish}】进行重绘。
    请保持画面中心的主菜【{main_dish}】与原图一致。
    将背景替换为日常分享风格的plog场景，暖色调。
    细节要求：
    1、桌面布置：铺有编织餐垫，餐垫旁摆放绿植、日式可爱摆件、牙签盒、餐巾纸盒；场景正前方放置1台iPad，屏幕需显示《蜡笔小新》播放画面。
    2、餐食搭配：以【{main_dish}】为C位，周围围绕摆放：1盘色泽诱人的大虾，1碗鲜嫩蒸蛋，1碗蔬菜沙拉，1盘日式小菜，1瓶韩式烧酒。
    3、辅助细节：右侧放置日式筷架、筷子和勺子。光影柔和自然，8k高清分辨率。
    """
    chinese_requirement = RAW_TEMPLATE.format(main_dish=vision_res)

    # DeepSeek 翻译
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    system_prompt_for_img = """
    You are an expert Prompt Engineer for FLUX.1 Image-to-Image.
    Translate the Chinese request into a detailed English prompt.
    CRITICAL: 
    1. You must describe the new background items (iPad with Crayon Shin-chan, Soju, woven mat) clearly.
    2. Emphasize that the main food subject comes from the input image.
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

    # 调用 FLUX (切换为 schnell)
    client_img = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    try:
        response = client_img.images.generate(
            # 👇 核心修复：改回 schnell，稳如老狗
            model="gemini-3-pro-image-preview",
            prompt=english_prompt,
            size="1024x1024",
            n=1,
            extra_body={
                "image": img_data_uri,
                "strength": strength 
            }
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {str(e)}"

# --- 5. 主界面 ---

st.title("🍱 外卖爆单神器 (极速修复版)")
st.caption("上传实拍图 -> 设定重绘幅度 -> 极速图生图")

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
        st.markdown("#### 2. 控制与卖点")
        st.markdown("##### 🎨 重绘幅度")
        strength = st.slider(
            "推荐 0.65 - 0.75",
            min_value=0.1, max_value=1.0, value=0.70, step=0.05,
            help="数值越大，AI 改动越多"
        )
        st.markdown("##### 📝 通用卖点")
        user_topic = st.text_area("", height=100, placeholder="例如：新品上市...", label_visibility="collapsed")
        st.write("")
        start_btn = st.button("🚀 启动任务")

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
                
                with st.spinner(f"🤖 Kimi识别 -> FLUX极速重绘中..."):
                    vision_res = analyze_image_kimi(file)
                    if "Error" in vision_res: raise Exception(f"识别失败: {vision_res}")

                    note_res = generate_copy_deepseek(vision_res, user_topic)

                    img_res = generate_image_flux_img2img(file, vision_res, strength)
                    if "Error" in img_res: raise Exception(f"生成失败: {img_res}")
                    
                    final_results.append({
                        "id": current_idx, "original": file, "generated_img": img_res, "note": note_res
                    })

                progress_bar.progress(current_idx / total_files)

            status_text.success(f"✅ 全部完成！")
            time.sleep(1)
            status_text.empty()
            progress_bar.empty()

            with result_container:
                st.divider()
                st.markdown(f"### 🎉 处理结果")
                for res in final_results:
                    with st.expander(f"🖼️ 第 {res['id']} 组结果 (点击展开)", expanded=(res['id']==1)):
                        rc1, rc2 = st.columns([2, 3], gap="medium")
                        with rc1:
                            st.markdown("**对比视图**")
                            col_orig, col_gen = st.columns(2)
                            with col_orig:
                                st.image(res["original"], caption="原图", use_container_width=True)
                            with col_gen:
                                st.image(res["generated_img"], caption="AI 重绘图", use_container_width=True)
                        with rc2:
                            st.markdown("**爆款文案**")
                            with st.container(border=True, height=400):
                                st.markdown(res["note"])
        
        except Exception as e:
            status_text.error(f"任务中断: {str(e)}")
            progress_bar.empty()

