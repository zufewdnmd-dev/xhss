import streamlit as st
import base64
import time
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="外卖爆单神器(多图批处理版)", page_icon="🍱", layout="wide")

# CSS 样式 (保持暖米色风格)
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
    /* 调整 expander 样式使其更清晰 */
    .streamlit-expanderHeader {
        background-color: #ECE8DF;
        border-radius: 8px;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 身份验证 (沿用) ---
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

# --- 3. 后台配置加载 (沿用) ---
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

# --- 4. 核心功能函数 (沿用，无修改) ---

def encode_image(uploaded_file):
    # 重要：读取文件内容后需要 seek(0) 重置指针，否则后续无法再次读取
    bytes_data = uploaded_file.getvalue()
    # uploaded_file.seek(0) # Streamlit 的上传对象通常不需要手动 reset，但为了保险起见可以加上
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
                        {"type": "text", "text": "分析这张图的菜品、食材、色泽。只输出客观描述。"},
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
    要求：标题二极管，正文多Emoji，语气真诚。
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.3
    )
    return response.choices[0].message.content

def generate_image_silicon(vision_res, user_topic):
    """【画手】硅基流动 (调用 Kolors)"""
    client_text = OpenAI(api_key=TEXT_KEY, base_url=TEXT_BASE)
    prompt_res = client_text.chat.completions.create(
        model="deepseek-chat",
        messages=[{
            "role": "user", 
            "content": f"根据描述：'{vision_res}' 和卖点 '{user_topic}'，写一个简短的AI绘画提示词（中文）。包含：美食摄影、8k高清、特写、光泽感。直接输出提示词。"
        }]
    )
    draw_prompt = prompt_res.choices[0].message.content
    client_img = OpenAI(api_key=IMG_KEY, base_url=IMG_BASE)
    try:
        response = client_img.images.generate(
            model="Kwai-Kolors/Kolors",
            prompt=draw_prompt,
            size="1024x1024", n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {str(e)}"

# --- 5. 主界面 (核心修改区域) ---

st.title("🍱 外卖爆单神器 (多图批处理版)")
st.caption("支持最多 5 张图片顺序处理：Kimi 视觉 -> DeepSeek 文案 -> Kolors 绘图")

# --- 输入区 ---
with st.container(border=True):
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("#### 1. 批量上传实拍图 (最多5张)")
        # 【修改点1】accept_multiple_files=True 允许过多选
        uploaded_files = st.file_uploader("", type=["jpg", "png"], accept_multiple_files=True, label_visibility="collapsed")
        
        # 【修改点2】限制数量并展示预览
        valid_files = []
        if uploaded_files:
            if len(uploaded_files) > 5:
                st.warning("⚠️ 您上传了超过 5 张图片，系统将仅处理前 5 张。")
                valid_files = uploaded_files[:5]
            else:
                valid_files = uploaded_files
            
            # 预览小图
            cols = st.columns(len(valid_files))
            for i, file in enumerate(valid_files):
                cols[i].image(file, caption=f"图 {i+1}", use_container_width=True)

    with c2:
        st.markdown("#### 2. 通用卖点 (应用于所有图片)")
        user_topic = st.text_area("", height=150, placeholder="例如：这批都是夏季新品，全场8折...", label_visibility="collapsed")
        st.write("")
        start_btn = st.button("🚀 启动批量生成任务")

# --- 处理与结果展示区 ---
if start_btn:
    if not valid_files:
        st.warning("⚠️ 请先上传至少一张图片！")
    elif not user_topic:
         st.warning("⚠️ 请输入通用的卖点信息！")
    else:
        # 用于存储处理结果的列表
        final_results = []
        
        # 【修改点3】引入进度条和状态容器
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_container = st.container()

        total_files = len(valid_files)
        
        try:
            # 【修改点4】核心循环逻辑
            for i, file in enumerate(valid_files):
                current_idx = i + 1
                status_text.markdown(f"### ⚡ 正在处理第 {current_idx}/{total_files} 张图片...")
                
                with st.spinner(f"🤖 AI流水线运作中 (图 {current_idx})..."):
                    # 1. Kimi 看图
                    vision_res = analyze_image_kimi(file)
                    if "Error" in vision_res: raise Exception(f"第{current_idx}张图视觉识别失败: {vision_res}")

                    # 2. DeepSeek 写文
                    note_res = generate_copy_deepseek(vision_res, user_topic)

                    # 3. Kolors 画图
                    img_res = generate_image_silicon(vision_res, user_topic)
                    if "Error" in img_res: raise Exception(f"第{current_idx}张图生成失败: {img_res}")
                    
                    # 保存结果
                    final_results.append({
                        "id": current_idx,
                        "original": file,
                        "generated_img": img_res,
                        "note": note_res
                    })

                # 更新进度条
                progress_bar.progress(current_idx / total_files)

            status_text.success(f"✅ 全部 {total_files} 张图片处理完成！")
            time.sleep(1)
            status_text.empty()
            progress_bar.empty()

            # 【修改点5】动态展示结果
            with result_container:
                st.divider()
                st.markdown("### 🎉 批量生成结果")
                for res in final_results:
                    # 使用 expander 折叠显示每一组结果，保持页面整洁
                    with st.expander(f"🖼️ 第 {res['id']} 组结果 (点击展开)", expanded=(res['id']==1)):
                        rc1, rc2 = st.columns([2, 3], gap="medium")
                        with rc1:
                            st.markdown("**对比视图**")
                            col_orig, col_gen = st.columns(2)
                            with col_orig:
                                st.image(res["original"], caption="原图", use_container_width=True)
                            with col_gen:
                                st.image(res["generated_img"], caption="AI精修图", use_container_width=True)
                        with rc2:
                            st.markdown("**爆款文案**")
                            with st.container(border=True, height=400):
                                st.markdown(res["note"])
        
        except Exception as e:
            status_text.error(f"任务中断: {str(e)}")
            progress_bar.empty()
