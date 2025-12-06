import streamlit as st
import base64
import time
from openai import OpenAI
import google.generativeai as genai # 👈 新增：导入 Google 官方库

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(Gemini Pro版)", page_icon="✨", layout="wide")

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
    # A. 文本：DeepSeek
    TEXT_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TEXT_BASE = "https://api.deepseek.com"
    
    # B. 视觉：Kimi (Moonshot)
    VISION_KEY = st.secrets["MOONSHOT_API_KEY"]
    VISION_BASE = "https://api.moonshot.cn/v1"
    
    # C. 绘图：Google Gemini Pro (👈 新增配置)
    GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_KEY) # 配置 Google 库
    
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.info("请检查 Secrets 中是否配置了 DEEPSEEK_API_KEY, MOONSHOT_API_KEY 和 GOOGLE_API_KEY")
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

def generate_image_gemini_pro(vision_res):
    """
    【画手】调用 Google Gemini Pro (gemini-3-pro-image-preview)
    """
    # 1. 中文场景模板
    RAW_TEMPLATE = """
    请生成一张日常分享风格的plog图片，核心呈现一人食温馨用餐场景，画面整体采用暖色调。
    具体细节要求如下：
    1、桌面布置：铺有编织餐垫，餐垫旁摆放绿植、日式可爱摆件、牙签盒、餐巾纸盒；场景正前方放置1台iPad，屏幕需显示《蜡笔小新》播放画面。
    2、餐食与餐具：
    餐具统一为日式风格，符合一人食规律。餐食共五种 + 1杯饮品，以【{main_dish}】为C位，其余作为配菜围绕摆放：
    主餐（食物一）：【{main_dish}】，色泽诱人，细节丰富；
    配菜（食物二至六）：1盘色泽诱人、撒有芝麻和葱花的大虾，1碗鲜嫩蒸蛋，1碗蔬菜沙拉，1盘日式小菜；
    饮品：韩式烧酒1瓶。
    3、辅助细节：餐食右侧放置日式筷架，筷架上需摆放筷子和勺子；所有餐食、餐具、摆件的搭配需凸显“舒适惬意的一人食悠闲氛围”。
    """
    
    # 2. 填入菜名
    chinese_requirement = RAW_TEMPLATE.format(main_dish=vision_res)

    # 3. DeepSeek 翻译优化 (转为详细英文指令)
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    
    system_prompt_for_img = """
    You are an expert Prompt Engineer for Google Gemini Image Generation.
    Translate the user's description into a highly detailed English prompt.
    
    STYLE GUIDELINES:
    - Focus on "photorealism", "cinematic lighting", and "cozy atmosphere".
    - Include ALL specific items: iPad with Crayon Shin-chan, Soju, side dishes.
    - Specify "8k resolution", "highly detailed textures".
    
    Output ONLY the English prompt.
    """

    translation_resp = client_text.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt_for_img}, 
            {"role": "user", "content": f"Description: {chinese_requirement}"}
        ]
    )
    english_prompt = translation_resp.choices[0].message.content

    # 4. 调用 Google Gemini Pro 模型绘图
    try:
        # 👈 核心修改：使用 Google 官方 SDK调用
        model = genai.GenerativeModel("gemini-3-pro-image-preview")
        response = model.generate_content(english_prompt)
        
        # Gemini 返回的是图片对象，我们需要拿到它的 URL 或者 Base64
        # 注意：Google API 返回的图片 URL 有效期很短，可以直接展示
        if response.parts and response.parts[0].image:
             # Streamlit 可以直接显示 PIL Image 对象，但为了统一格式，这里还是建议确认返回值
             # 由于 Google API 的特殊性，我们直接返回图片对象，在主界面处理
             return response.parts[0].image
        else:
             return "Error: Gemini 未返回图片，可能被安全策略拦截。"

    except Exception as e:
        return f"Error: {str
