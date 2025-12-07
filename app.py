import streamlit as st
from openai import OpenAI

# --- 页面基础配置 ---
st.set_page_config(
    page_title="外卖爆单文案生成器",
    page_icon="✍️",
    layout="centered"
)

# --- 1. 配置加载 (只读 DeepSeek Key) ---
def load_config():
    try:
        # 只需要读取 deepseek 的配置
        # 兼容之前的 secrets.toml 格式
        return st.secrets["deepseek"]["api_key"]
    except Exception as e:
        st.error(f"❌ 配置文件读取失败: {e}")
        st.info("请检查 .streamlit/secrets.toml 中是否包含 [deepseek] 配置。")
        st.stop()

API_KEY = load_config()

# --- 2. 核心功能函数 ---
def generate_xiaohongshu_copy(dish_name, selling_point):
    """DeepSeek 文案生成核心逻辑"""
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
    
    prompt = f"""
    你是一个拥有百万粉丝的小红书爆款美食博主。
    请为我的外卖菜品写一篇笔记。
    
    菜品名称：{dish_name}
    核心卖点：{selling_point}
    
    写作要求：
    1. 标题：必须包含Emoji，使用夸张、惊叹的语气（如：好吃到哭！绝绝子！排队两小时！）。
    2. 正文：分段落，多用Emoji 😋🔥✨，语气亲切热情，强调【分量足】、【性价比】、【现做现发】、【学生党/打工人必吃】。
    3. 结尾：必须包含 5-8 个热门标签 #外卖 #宝藏店铺 #干饭人 #xx美食(填入具体地名) 等。
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 生成失败，请检查 API Key 或网络: {e}"

# --- 3. 极简 UI 界面 ---

st.title("✍️ 外卖爆单 · 文案生成器")
st.caption("纯享版 - 专注搞钱文案，无需等待绘图")

# 使用表单 (Form) 避免每输入一个字就刷新
with st.form("copy_form"):
    st.markdown("### 📋 输入菜品信息")
    dish_name = st.text_input("菜品名称", placeholder="例如：脆皮炸鸡腿饭")
    selling_point = st.text_area("核心卖点 (选填)", placeholder="例如：外酥里嫩，送冰阔落，满20减5...", height=100)
    
    # 提交按钮
    submitted = st.form_submit_button("🚀 生成爆款文案", type="primary", use_container_width=True)

# --- 4. 结果展示 ---
if submitted:
    if not dish_name:
        st.warning("⚠️ 请至少输入一个菜名！")
    else:
        with st.spinner("🤖 DeepSeek 正在疯狂码字中..."):
            copy_text = generate_xiaohongshu_copy(dish_name, selling_point)
            
        st.success("✅ 生成完成！")
        st.markdown("---")
        st.subheader("📝 你的爆款笔记")
        
        # 显示文案框，方便复制
        st.text_area("点击右下角按钮一键复制", value=copy_text, height=450)
