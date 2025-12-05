import streamlit as st
import base64
import time
import jwt  # 需在 requirements.txt 安装 PyJWT
import requests
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(稳定版)", page_icon="🍱", layout="wide")

# CSS 样式 (黑金风格适配可灵)
st.markdown("""
<style>
    .stApp { background-color: #1A1A1A; color: #E0E0E0; }
    h1, h2, h3, p, div, span { color: #E0E0E0 !important; }
    .stButton>button { 
        background-color: #D4AF37; color: black !important; 
        border-radius: 8px; border: none; padding: 12px 28px;
        font-size: 18px; font-weight: bold; width: 100%;
    }
    .stButton>button:hover { background-color: #F1C40F; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #333; color: white; border-color: #555;
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
    
    # C. 绘图：Kling (可灵)
    KLING_AK = st.secrets["KLING_ACCESS_KEY"]
    KLING_SK = st.secrets["KLING_SECRET_KEY"]
    
except Exception as e:
    st.error(f"❌ 配置缺失: {e}")
    st.info("请在 Secrets 中配置 DEEPSEEK_API_KEY, MOONSHOT_API_KEY, KLING_ACCESS_KEY, KLING_SECRET_KEY")
    st.stop()

# --- 4. 核心功能函数 ---

def get_kling_token(ak, sk):
    """
    【修复版】生成可灵 API 的 JWT 令牌
    修复点：显式指定 HS256 算法，增加时间戳容错
    """
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    payload = {
        "iss": ak,
        "exp": int(time.time()) + 1800, # 30分钟有效
        "nbf": int(time.time()) - 5     # 提前5秒生效，防止服务器时间误差
    }
    # 核心修复：明确指定 algorithm="HS256"
    token = jwt.encode(payload, sk, algorithm="HS256", headers=headers)
    return token

def generate_image_kling(prompt):
    """调用可灵官方文生图接口 (带轮询等待)"""
    token = get_kling_token(KLING_AK, KLING_SK)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # 1. 提交任务
    url_submit = "https://api.klingai.com/v1/images/generations"
    payload = {
        "model": "kling-v1", 
        "prompt": f"Delicious food photography, 8k resolution, cinematic lighting, {prompt}",
        "n": 1,
        "aspect_ratio": "1:1"
    }
    
    try:
        res = requests.post(url_submit, json=payload, headers=headers)
        if res.status_code != 200:
            return f"Error: 提交失败 {res.text}"
        
        data = res.json()
        if data["code"] != 0:
            return f"Error: 可灵报错 {data['message']} (Code: {data['code']})"
            
        task_id = data["data"]["task_id"]
        
        # 2. 轮询等待结果
        url_query = f"https://api.klingai.com/v1/images/generations/{task_id}"
        
        # 增加等待时间提示
        progress_text = "🎨 可灵 (Kling) 正在绘制中... 请耐心等待约 15-20 秒"
        my_bar = st.progress(0, text=progress_text)

        for i in range(40): # 最多等待 40 * 2 = 80秒
            time.sleep(2)
            my_bar.progress((i + 1) * 2, text=progress_text)
            
            res_q = requests.get(url_query, headers=headers)
            data_q = res_q.json()
            
            if data_q.get("code") != 0:
                return f"Error: 查询失败 {data_q.get('message')}"

            status = data_q["data"]["task_status"]
            
            if status == "succeed":
                my_bar.empty()
                return data_q["data"]["task_result"]["images"][0]["url"]
            elif status == "failed":
                my_bar.empty()
                return f"Error: 生成任务被拒绝或失败 - {data_q['data'].get('task_status_msg', '未知原因')}"
        
        my_bar.empty()            
        return "Error: 生成超时，请重试"
        
    except Exception as e:
        return f"Error: 请求异常 {str(e)}"

def analyze_image_kimi(image_file):
    """
    【修复版】Kimi 看图
    修复点：增加 429 错误自动重试机制
    """
    encoded_string = base64.b64encode(image_file.getvalue()).decode('utf-8')
    client = OpenAI(api_key=VISION_KEY, base_url=VISION_BASE)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="moonshot-v1-8k-vision-preview",
                messages=[
                    {"role": "system", "content": "你是专业美食摄影师。"},
                    {"role": "user", "content": [
                        {"type": "text", "text": "请分析这张图的菜品、食材、色泽和构图。只输出客观描述，不要废话。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}
                    ]}
                ]
            )
            return response.choices[0].message.content
            
        except Exception as e:
            error_str = str(e)
            # 如果是 429 过载错误，且不是最后一次尝试
            if "429" in error_str and attempt < max_retries - 1:
                st.toast(f"⏳ Kimi 服务器拥堵，正在第 {attempt+1} 次自动重试...", icon="🔄")
                time.sleep(3) # 休息3秒
                continue
            elif attempt == max_retries - 1:
                return f"视觉识别失败: {error_str}"
            else:
                return f"视觉识别失败: {error_str}"

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

# --- 5. 主界面 ---

st.title("🎬 外卖爆单神器 (可灵内核稳定版)")
st.caption("Kimi 视觉 · DeepSeek 文案 · Kling 绘图")

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
    if st.button("🚀 呼叫可灵 (Kling) 开始创作"):
        if not uploaded_file:
            st.warning("⚠️ 请先上传图片")
        else:
            with st.status("⚡ AI 梦之队全速运转...", expanded=True):
                
                st.write("👁️ Kimi 正在识别图片细节...")
                vision_res = analyze_image_kimi(uploaded_file)
                if "失败" in vision_res: st.error(vision_res); st.stop()
                
                st.write("🧠 DeepSeek 正在撰写文案...")
                note_res = generate_copy_deepseek(vision_res, user_topic)
                
                st.write("🎨 可灵 (Kling) 正在生成 4K 美食大片 (需等待)...")
                # 提取关键词给可灵
                img_res = generate_image_kling(f"{vision_res}, {user_topic}")
                
            st.success("✅ 完成！")
            
            r1, r2 = st.columns(2)
            with r1:
                st.markdown("### 🖼️ 可灵生成图")
                if "http" in img_res:
                    st.image(img_res, use_container_width=True)
                else:
                    st.error(img_res)
            with r2:
                st.markdown("### 📝 爆款文案")
                with st.container(border=True, height=500):
                    st.markdown(note_res)
