import streamlit as st
import os
import requests
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI

# 页面配置
st.set_page_config(page_title="外卖爆单神器", page_icon="🍱", layout="centered")

# --- 🔐 鉴权与配置加载 ---
def load_config():
    """尝试从 st.secrets 加载配置，如果失败则提示"""
    try:
        # 使用 .get() 方法避免直接报错，方便调试
        ds_key = st.secrets["deepseek"]["api_key"]
        img_key = st.secrets["image_gen"]["api_key"]
        img_url = st.secrets["image_gen"]["base_url"]
        return ds_key, img_key, img_url
    except FileNotFoundError:
        st.error("❌ 未检测到 secrets.toml 文件。请在 .streamlit/ 目录下创建配置。")
        st.stop()
    except KeyError as e:
        st.error(f"❌ 配置文件中缺失字段: {e}。请检查 secrets.toml 或 Streamlit Cloud 设置。")
        st.stop()

# 加载 API Key (商家用户无感知，直接使用)
DEEPSEEK_API_KEY, IMAGE_API_KEY, IMAGE_API_URL = load_config()

# --- 核心功能函数 (逻辑保持不变，只需直接使用全局变量) ---

def generate_xiaohongshu_copy(dish_name, selling_point):
    """调用 DeepSeek 生成小红书文案"""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    system_prompt = """
    你是一个拥有百万粉丝的小红书爆款文案专家。
    请遵循以下规则：
    1. 标题：必须包含emoji，极具吸引力，(如：'巨巨巨好吃'，'绝绝子')。
    2. 正文：分段落，多用emoji，语气亲切热情。
    3. 标签：文末带上5-8个热门话题标签。
    """
    
    user_prompt = f"我的菜品是：{dish_name}。主要卖点是：{selling_point}。请帮我写一篇小红书笔记。"
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"文案生成出错: {str(e)}"

# (process_image 函数逻辑同上，直接使用 IMAGE_API_KEY 和 IMAGE_API_URL 即可)
# 为了节省篇幅，这里省略重复的 process_image 代码
# ...

# --- 主界面 ---

st.title("🍱 外卖爆单 · 小红书笔记生成器")
st.caption("商家专用版 - 极速生成，无需配置")

# 侧边栏只保留业务相关的选项，不再暴露技术细节
with st.sidebar:
    st.header("🎨 风格设置")
    style_option = st.selectbox("选择图片优化风格", 
        ["温馨居家风", "高端日料风", "清新野餐风", "赛博朋克风"])
    st.info(f"当前系统状态：✅ 已连接 AI 服务")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ 上传素材")
    uploaded_file = st.file_uploader("上传菜品实拍图", type=["jpg", "png", "jpeg"])
    dish_name = st.text_input("菜品名称", placeholder="例如：秘制红烧肉便当")
    selling_point = st.text_area("核心卖点", placeholder="例如：肥而不腻，分量超大...")

with col2:
    st.subheader("2️⃣ 生成结果")
    if st.button("✨ 一键生成", type="primary"):
        if not uploaded_file:
            st.warning("请先上传一张图片！")
        else:
            with st.spinner("正在生成爆款内容..."):
                # 1. 生成文案
                copywriting = generate_xiaohongshu_copy(dish_name, selling_point)
                st.session_state['result_copy'] = copywriting
                st.success("生成完成！")

    if 'result_img' in st.session_state:
        st.subheader("🖼️ 图片预览")
        
        # 1. 尝试直接显示图片
        try:
            st.image(st.session_state['result_img'], caption="AI 精修效果图", use_container_width=True)
        except Exception:
            st.error("图片加载受阻，请点击下方链接查看")

        # 2. 【关键】强制显示链接，方便调试
        st.markdown(f"**图片链接(点击直接打开):** [点击这里查看大图]({st.session_state['result_img']})")
        # 把原始链接打印出来，方便检查是不是链接格式错了
        st.code(st.session_state['result_img'])
    if 'result_copy' in st.session_state:
        st.markdown("### 📝 预览")
        st.text_area("文案内容", value=st.session_state['result_copy'], height=300)

