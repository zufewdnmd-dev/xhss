import streamlit as st
import os
import requests
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI

# --- 页面基础配置 ---
st.set_page_config(
    page_title="外卖爆单神器 V3.1",
    page_icon="⚡",
    layout="centered"
)

# --- 1. 配置加载 ---
def load_config():
    try:
        # 尝试读取配置
        ds_key = st.secrets["deepseek"]["api_key"]
        img_key = st.secrets["image_gen"]["api_key"]
        img_url = st.secrets["image_gen"]["base_url"]
        return ds_key, img_key, img_url
    except Exception as e:
        # 如果配置没读到，直接在页面报错，方便你排查
        st.error(f"❌ 配置文件读取失败: {e}")
        st.info("请检查 .streamlit/secrets.toml 是否存在且格式正确。")
        st.stop()

DEEPSEEK_API_KEY, IMAGE_API_KEY, IMAGE_API_URL = load_config()

# --- 2. 核心功能函数 ---

def compress_image(image):
    """压缩图片，防止API报错"""
    img = Image.open(image).convert('RGB')
    max_size = 1024
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def generate_xiaohongshu_copy(dish_name, selling_point):
    """文案生成"""
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

def generate_food_image(uploaded_file, prompt_style):
    """绘图核心逻辑 (Flux-Schnell)"""
    base64_img = compress_image(uploaded_file)
    
    # 构造请求头和Payload
    headers = {
        "Authorization": f"Bearer {IMAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 🚨 关键：使用 flux-schnell 模型，重绘幅度 strength 设为 0.45
    payload = {
        "model": "flux-schnell", 
        "prompt": f"{prompt_style}, real food, 8k, best quality, appetizing",
        "image": f"data:image/jpeg;base64,{base64_img}",
        "strength": 0.45,
        "size": "1024x1024"
    }
    
    try:
        # 使用 requests 发送请求
        response = requests.post(IMAGE_API_URL, json=payload, headers=headers, timeout=60)
        
        # 🐛 调试打印：如果 API 报错，我们能看到具体原因
        if response.status_code != 200:
            st.error(f"绘图 API 报错 (状态码 {response.status_code}):")
            st.code(response.text) # 打印错误详情
            return None
            
        result = response.json()
        # 尝试解析 URL
        if 'data' in result and len(result['data']) > 0:
            return result['data'][0]['url']
        else:
            st.error("API 返回了 200 成功，但没有图片 URL，返回数据如下：")
            st.code(result)
            return None
            
    except Exception as e:
        st.error(f"网络请求发送失败: {e}")
        return None

# --- 3. 界面逻辑 ---

st.title("⚡ 外卖爆单神器 V3.1 (调试版)")
st.caption("如果看到这个标题，说明代码更新成功了！")

# 侧边栏风格选择
with st.sidebar:
    st.header("🎨 设置")
    style_option = st.radio("滤镜风格", ["温馨居家", "高端日料", "清新野餐", "赛博朋克"])
    # 简单的 Prompt 映射
    prompts = {
        "温馨居家": "warm sunlight, wooden table, cozy home vibe",
        "高端日料": "dark background, dramatic lighting, michelin star",
        "清新野餐": "outdoor, natural sunlight, picnic vibe",
        "赛博朋克": "neon lights, night city, vibrant colors"
    }

# 布局
col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ 上传")
    uploaded_file = st.file_uploader("上传菜品图", type=["jpg", "png"])
    dish_name = st.text_input("菜名", "炒饭")
    selling_point = st.text_area("卖点", "量大好吃")
    
    # 按钮
    start_btn = st.button("🚀 开始生成", type="primary")

with col2:
    st.subheader("2️⃣ 结果")
    
    if start_btn and uploaded_file:
        status = st.status("正在处理中...", expanded=True)
        
        # 1. 文案
        status.write("📝 正在写文案...")
        copy = generate_xiaohongshu_copy(dish_name, selling_point)
        st.session_state['v3_copy'] = copy
        
        # 2. 图片
        status.write("🖼️ 正在画图 (Flux-Schnell)...")
        # 🚨 这里的代码保证了 generate_food_image 绝对会被调用
        img_url = generate_food_image(uploaded_file, prompts[style_option])
        
        if img_url:
            st.session_state['v3_img'] = img_url
            status.update(label="✅ 生成成功！", state="complete", expanded=False)
        else:
            status.update(label="❌ 生成失败", state="error")

    # --- 展示区域 ---
    if 'v3_img' in st.session_state:
        st.image(st.session_state['v3_img'], caption="AI 处理结果")
        # 👇 调试链接：如果图片显示不出来，点击这个链接试试
        st.markdown(f"**🔗 [图片打不开？点我直接看原图]({st.session_state['v3_img']})**")
        
    if 'v3_copy' in st.session_state:
        st.text_area("文案内容", st.session_state['v3_copy'], height=200)
