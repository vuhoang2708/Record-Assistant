import streamlit as st
import google.generativeai as genai
from docx import Document
import tempfile
import os
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Meeting Assistant", page_icon="🎙️", layout="wide")

st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 8px; height: 3em; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- HÀM XỬ LÝ ---
def configure_genai():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except KeyError:
        st.error("🚨 Thiếu API Key trong Secrets!")
        return False

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
    st.title("🎙️ AI Meeting Assistant (Auto-Switch)")
    
    if not configure_genai(): return

    with st.sidebar:
        st.header("⚙️ Cấu hình")
        # DANH SÁCH MODEL (Bao gồm cả tương lai)
        model_version = st.selectbox(
            "Chọn Model:",
            ("gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-3.0-flash")
        )
        
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
        with st.spinner("Đang xử lý... (Vui lòng đợi)"):
            try:
                # 1. Lưu file tạm
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                # 2. Upload lên Google
                gemini_file = upload_to_gemini(tmp_path)

                # 3. Tạo Prompt
                prompt = "Bạn là thư ký chuyên nghiệp. Hãy xử lý file âm thanh này theo yêu cầu:\n"
                if opt_transcript: prompt += "- Gỡ băng chi tiết từng lời.\n"
                if opt_summary: prompt += "- Tóm tắt ý chính và lập bảng Action Items.\n"
                if opt_minutes: prompt += "- Viết biên bản cuộc họp trang trọng.\n"
                if opt_prosody: prompt += "- Phân tích thái độ, ngữ điệu người nói.\n"
                if opt_gossip: prompt += "- Kể lại theo phong cách hài hước (Gossip).\n"
                if opt_slide: prompt += "- Trích xuất nội dung để làm Slide (JSON).\n"

                # 4. GỌI AI VỚI CƠ CHẾ SMART FALLBACK (QUAN TRỌNG)
                try:
                    # Thử dùng model người dùng chọn (Ví dụ 3.0)
                    model = genai.GenerativeModel(model_name=model_version)
                    response = model.generate_content([prompt, gemini_file])
                except Exception as e:
                    # Nếu lỗi (do 3.0 chưa ra mắt), tự động chuyển về 1.5
                    st.warning(f"⚠️ Model {model_version} chưa sẵn sàng hoặc gặp lỗi. Hệ thống tự động chuyển sang 'gemini-1.5-flash' để xử lý ngay.")
                    backup_model = genai.GenerativeModel(model_name="gemini-1.5-flash")
                    response = backup_model.generate_content([prompt, gemini_file])

                # 5. Hiển thị kết quả
                st.success("✅ Xử lý thành công!")
                st.markdown(response.text)

                # 6. Tải về
                doc = create_docx(response.text)
                doc_io = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                doc.save(doc_io.name)
                with open(doc_io.name, "rb") as f:
                    st.download_button("📥 Tải báo cáo Word", f, "Meeting_Report.docx")

                # Dọn dẹp
                genai.delete_file(gemini_file.name)
                os.remove(tmp_path)
                os.remove(doc_io.name)

            except Exception as e:
                st.error(f"Lỗi không mong muốn: {e}")

if __name__ == "__main__":
    main()
