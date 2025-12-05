import streamlit as st
import base64
import time
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(FLUX画质版)", page_icon="🍱", layout="wide")

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
    IMG_BASE = "https://api.siliconflow.cn/v1"
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.stop()

# --- 4. 核心功能函数 ---

def encode_image(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def analyze_image_kimi(image_file):
    """【眼睛】Kimi 看图"""
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
    """【大脑】DeepSeek 写文"""
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

def generate_image_flux_pro(vision_res):
    """
    【画手升级版】调用 FLUX.1-dev (通过 DeepSeek 润色提示词)
    """
    # 1. 定义你的中文模板
    RAW_TEMPLATE = """
    请生成一张日常分享风格的plog图片，核心呈现一人食温馨用餐场景，画面整体采用暖色调。
    具体细节要求如下：
    1、桌面布置：铺有编织餐垫，餐垫旁摆放绿植、日式可爱摆件、牙签盒、餐巾纸盒；场景正前方放置1台iPad，屏幕需显示《蜡笔小新》播放画面。
    2、餐食与餐具：
    餐具统一为日式风格，符合一人食规律。餐食共五种 + 1杯饮品，以【{main_dish}】为C位，其余作为配菜围绕摆放：
    主餐（食物一）：【{main_dish}】，色泽诱人，细节丰富；
    配菜（食物二至六）：1盘色泽诱人、撒有芝麻和葱花的大虾，1碗鲜嫩蒸蛋，1碗蔬菜沙拉，1盘日式小菜；
    饮品：韩式烧酒1瓶。
    3、辅助细节：餐食右侧放置日式筷架，筷架上需摆放筷子和勺子；所有餐食、餐具、摆件的搭配需凸显“舒适惬意的一人食悠闲氛围”，光影柔和自然，8k高清分辨率。
    """
    
    # 2. 填入主菜
    chinese_prompt = RAW_TEMPLATE.format(main_dish=vision_res)

    # 3. 【关键步骤】让 DeepSeek 把这段中文“翻译”成 FLUX 最喜欢的英文摄影指令
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    translation_resp = client_text.chat.completions.create(
        model="deepseek-chat",
        messages=[{
            "role": "system", 
            "content": "You are an expert prompt engineer for AI image generation (Midjourney/FLUX). Convert the user's Chinese description into a highly detailed English prompt. Focus on lighting, texture, composition, and photorealism. Ensure all specific elements (iPad with Crayon Shin-chan, Soju, side dishes) are included."
        }, {
            "role": "user", 
            "content": chinese_prompt
        }]
    )
    english_prompt = translation_resp.choices[0].message.content

    # 4. 调用 FLUX.1-dev 进行绘图
    client_img = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    try:
        response = client_img.images.generate(
            model="black-forest-labs/FLUX.1-dev", # 👈 切换为最强画质模型
            prompt=english_prompt,
            size="1024x1024",
            n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {str(e)}"

# --- 5. 主界面 ---

st.title("🍱 外卖爆单神器 (FLUX 旗舰版)")
st.caption("Kimi 视觉 -> DeepSeek 润色 -> FLUX.1 极致绘图")

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
        start_btn = st.button("🚀 启动旗舰级生成")

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
                status_text.markdown(f"### ⚡ 正在精修第 {current_idx}/{total_files} 张 (FLUX画质模式)...")
                
                with st.spinner(f"🤖 正在进行光影重绘与细节渲染 (图 {current_idx})..."):
                    # 1. Kimi 识别
                    vision_res = analyze_image_kimi(file)
                    if "Error" in vision_res: raise Exception(f"识别失败: {vision_res}")

                    # 2. DeepSeek 写文
                    note_res = generate_copy_deepseek(vision_res, user_topic)

                    # 3. FLUX 画图 (经过 DeepSeek 翻译优化)
                    img_res = generate_image_flux_pro(vision_res)
                    if "Error" in img_res: raise Exception(f"生成失败: {img_res}")
                    
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
                st.markdown("### 🎉 旗舰级精修结果")
                for res in final_results:
                    with st.expander(f"🖼️ 第 {res['id']} 组结果 (点击展开)", expanded=(res['id']==1)):
                        rc1, rc2 = st.columns([2, 3], gap="medium")
                        with rc1:
                            st.markdown("**对比视图**")
                            col_orig, col_gen = st.columns(2)
                            with col_orig:
                                st.image(res["original"], caption="原图", use_container_width=True)
                            with col_gen:
                                st.image(res["generated_img"], caption="FLUX 精修图", use_container_width=True)
                        with rc2:
                            st.markdown("**爆款文案**")
                            with st.container(border=True, height=400):
                                st.markdown(res["note"])
        
        except Exception as e:
            status_text.error(f"任务中断: {str(e)}")
            progress_bar.empty()
