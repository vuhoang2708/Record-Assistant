import streamlit as st
import google.generativeai as genai
from docx import Document
import tempfile
import os
import time

st.set_page_config(page_title="AI Meeting Assistant", page_icon="🎙️", layout="wide")

# --- HÀM CẤU HÌNH ---
def get_available_models(api_key):
    """Hỏi Google xem Key này dùng được những model nào"""
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        valid_models = []
        for m in models:
            # Chỉ lấy những model biết tạo nội dung (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                # Lọc lấy các bản Flash và Pro
                if 'flash' in m.name or 'pro' in m.name:
                    valid_models.append(m.name)
        return valid_models
    except Exception as e:
        return []

def upload_to_gemini(path, mime_type="audio/mp3"):
    file = genai.upload_file(path, mime_type=mime_type)
    while file.state.name == "PROCESSING":
        time.sleep(1)
        file = genai.get_file(file.name)
    return file

def create_docx(content):
    doc = Document()
    doc.add_heading('MEETING REPORT', 0)
    for line in content.split('\n'):
        if line.startswith('# '): doc.add_heading(line.replace('# ', ''), level=1)
        elif line.startswith('## '): doc.add_heading(line.replace('## ', ''), level=2)
        elif line.startswith('### '): doc.add_heading(line.replace('### ', ''), level=3)
        else: doc.add_paragraph(line)
    return doc

# --- MAIN APP ---
def main():
    st.title("🎙️ AI Meeting Assistant (Auto-Detect)")

    # 1. Lấy API Key
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        st.error("🚨 Chưa nhập API Key trong Secrets!")
        return

    # 2. Tự động dò tìm Model (KHÔNG ĐOÁN TÊN NỮA)
    with st.spinner("Đang kết nối Google để lấy danh sách Model..."):
        available_models = get_available_models(api_key)
    
    if not available_models:
        st.error("❌ Lỗi: API Key không kết nối được hoặc không tìm thấy model nào. Vui lòng kiểm tra lại Key!")
        return

    # 3. Giao diện
    with st.sidebar:
        st.header("⚙️ Cấu hình")
        # Cho người dùng chọn trong danh sách THẬT vừa lấy về
        selected_model = st.selectbox("Chọn Model (Đã kiểm tra):", available_models)
        
        st.divider()
        st.subheader("Tùy chọn đầu ra")
        opt_transcript = st.checkbox("Gỡ băng (Transcript)", False)
        opt_summary = st.checkbox("Tóm tắt & Action Items", True)
        opt_minutes = st.checkbox("Biên bản (Formal)", True)
        opt_prosody = st.checkbox("Phân tích thái độ", False)
        opt_gossip = st.checkbox("Chế độ Bà tám", False)
        opt_slide = st.checkbox("Dữ liệu tạo Slide", False)

    uploaded_file = st.file_uploader("Upload file ghi âm", type=['mp3', 'wav', 'm4a'])

    if uploaded_file and st.button("🚀 XỬ LÝ NGAY"):
        with st.spinner(f"Đang xử lý bằng model {selected_model}..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                gemini_file = upload_to_gemini(tmp_path)

                prompt = "Bạn là thư ký chuyên nghiệp. Hãy xử lý file âm thanh này:\n"
                if opt_transcript: prompt += "- Gỡ băng chi tiết.\n"
                if opt_summary: prompt += "- Tóm tắt ý chính & Action Items.\n"
                if opt_minutes: prompt += "- Viết biên bản trang trọng.\n"
                if opt_prosody: prompt += "- Phân tích thái độ/ngữ điệu.\n"
                if opt_gossip: prompt += "- Kể lại hài hước (Gossip).\n"
                if opt_slide: prompt += "- Trích xuất JSON làm Slide.\n"

                # Gọi đúng cái model đã chọn
                model = genai.GenerativeModel(selected_model)
                response = model.generate_content([prompt, gemini_file])

                st.success("✅ Xử lý thành công!")
                st.markdown(response.text)

                doc = create_docx(response.text)
                doc_io = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                doc.save(doc_io.name)
                with open(doc_io.name, "rb") as f:
                    st.download_button("📥 Tải báo cáo Word", f, "Meeting_Report.docx")
                
                try:
                    genai.delete_file(gemini_file.name)
                    os.remove(tmp_path)
                    os.remove(doc_io.name)
                except: pass

            except Exception as e:
                st.error(f"Lỗi: {e}")

if __name__ == "__main__":
    main()
