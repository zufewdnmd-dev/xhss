import streamlit as st
import os
import requests
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI

# --- 页面配置 ---
st.set_page_config(
    page_title="外卖爆单神器 V4.0 (Plog特供版)",
    page_icon="🍱",
    layout="centered"
)

# --- 1. 配置加载 ---
def load_config():
    try:
        ds_key = st.secrets["deepseek"]["api_key"]
        img_key = st.secrets["image_gen"]["api_key"]
        img_url = st.secrets["image_gen"]["base_url"]
        return ds_key, img_key, img_url
    except Exception as e:
        st.error(f"❌ 配置文件读取失败: {e}")
        st.info("请检查 .streamlit/secrets.toml 是否存在。")
        st.stop()

DEEPSEEK_API_KEY, IMAGE_API_KEY, IMAGE_API_URL = load_config()

# --- 2. 核心功能函数 ---

def compress_image(image):
    """压缩图片并转Base64"""
    img = Image.open(image).convert('RGB')
    max_size = 1024
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def generate_xiaohongshu_copy(dish_name, selling_point):
    """生成小红书文案"""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    prompt = f"我的菜品是：{dish_name}。卖点：{selling_point}。请写一篇小红书笔记，标题要夸张带emoji，正文强调分量足和好吃，文末带标签。"
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 文案报错: {e}"

def generate_food_image(uploaded_file, dish_name):
    """
    Flux-Schnell 图生图：一人食 Plog 风格模式
    """
    base64_img = compress_image(uploaded_file)
    
    # 🔥 核心修改：使用你定制的 Prompt 模板
    # 我们把 dish_name 嵌入进去，让 AI 知道主菜是什么
    full_prompt = f"""
    POV shot, high angle view of a cozy solo dining setup. 
    Center focus: A delicious {dish_name} placed right in the center, steaming hot, glossy appetizing texture, rich details. 
    Foreground prop: An iPad propped up on the table playing the anime "Crayon Shin-chan" (cartoon style screen), clearly visible. 
    Surroundings: A green bottle of Korean Soju, and small side dishes containing boiled prawns, steamed egg custard, fresh salad, and pickles arranged around the main dish. 
    Environment: Warm wooden table, woven placemat, cozy home atmosphere. 
    Lighting: Soft natural window light, warm sun rays, soft shadows. 
    Style: iPhone 15 Pro photography, photorealistic, 8k resolution, slight depth of field, social media aesthetics.
    """
    
    headers = {
        "Authorization": f"Bearer {IMAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gemini-3-pro-image-preview", 
        "prompt": full_prompt,
        "image": f"data:image/jpeg;base64,{base64_img}",
        # ⚠️ 关键调整：Strength 设为 0.60
        # 因为我们要加 iPad 和配菜，需要给 AI 更多修改原图背景的权限
        "strength": 0.60, 
        "size": "1024x1024"
    }
    
    try:
        response = requests.post(IMAGE_API_URL, json=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            st.error(f"绘图 API 报错: {response.text}")
            return None
            
        result = response.json()
        if 'data' in result and len(result['data']) > 0:
            return result['data'][0]['url']
        else:
            st.error("API 返回成功但没有图片URL")
            st.code(result)
            return None
            
    except Exception as e:
        st.error(f"网络请求失败: {e}")
        return None

# --- 3. 界面逻辑 ---

st.title("🍱 外卖爆单神器 (Plog特供版)")
st.caption("自动生成：iPad追剧 + 丰富配菜 + 温馨一人食场景")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ 上传素材")
    uploaded_file = st.file_uploader("上传菜品实拍图", type=["jpg", "png", "jpeg"])
    dish_name = st.text_input("菜品名称", "麻辣烫") # 默认值方便测试
    selling_point = st.text_area("卖点描述", "汤底浓郁，食材新鲜")
    
    start_btn = st.button("🚀 生成 Plog 大片", type="primary", use_container_width=True)

with col2:
    st.subheader("2️⃣ 结果预览")
    
    if start_btn and uploaded_file:
        status = st.status("AI 正在干活...", expanded=True)
        
        # 1. 文案
        status.write("📝 DeepSeek 正在写文案...")
        copy = generate_xiaohongshu_copy(dish_name, selling_point)
        st.session_state['plog_copy'] = copy
        
        # 2. 图片
        status.write("🖼️ Flux 正在布置餐桌 (摆放iPad和烧酒)...")
        # 传入 dish_name 而不是 style
        img_url = generate_food_image(uploaded_file, dish_name)
        
        if img_url:
            st.session_state['plog_img'] = img_url
            status.update(label="✅ 大片生成成功！", state="complete", expanded=False)
        else:
            status.update(label="❌ 生成失败", state="error")

    # --- 展示区域 ---
    if 'plog_img' in st.session_state:
        st.image(st.session_state['plog_img'], caption="AI 装修后的效果")
        st.markdown(f"**🔗 [点击查看高清原图]({st.session_state['plog_img']})**")
        
    if 'plog_copy' in st.session_state:
        st.divider()
        st.subheader("📝 爆款文案")
        st.text_area("文案内容", st.session_state['plog_copy'], height=200)

