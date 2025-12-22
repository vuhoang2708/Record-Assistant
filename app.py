import streamlit as st
import google.generativeai as genai
from docx import Document
import tempfile
import os
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Meeting Assistant", page_icon="🎙️", layout="wide")
st.markdown("""<style>.stButton>button {width: 100%; border-radius: 8px; height: 3em; font-weight: bold;}</style>""", unsafe_allow_html=True)

# --- HÀM XỬ LÝ ---
def configure_genai():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except KeyError:
        st.error("🚨 Lỗi: Chưa nhập API Key trong Secrets!")
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
    st.title("🎙️ AI Meeting Assistant (Final Fix)")
    
    if not configure_genai(): return

    with st.sidebar:
        st.header("⚙️ Cấu hình")
        # Người dùng chọn model mong muốn
        user_choice = st.selectbox(
            "Chọn Model ưu tiên:",
            ("gemini-1.5-flash-latest", "gemini-2.0-flash-exp", "gemini-1.5-pro-latest")
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
        with st.spinner("Đang xử lý..."):
            try:
                # 1. Lưu file tạm
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                # 2. Upload lên Google
                gemini_file = upload_to_gemini(tmp_path)

                # 3. Tạo Prompt
                prompt = "Bạn là thư ký chuyên nghiệp. Hãy xử lý file âm thanh này:\n"
                if opt_transcript: prompt += "- Gỡ băng chi tiết.\n"
                if opt_summary: prompt += "- Tóm tắt ý chính & Action Items.\n"
                if opt_minutes: prompt += "- Viết biên bản trang trọng.\n"
                if opt_prosody: prompt += "- Phân tích thái độ/ngữ điệu.\n"
                if opt_gossip: prompt += "- Kể lại hài hước (Gossip).\n"
                if opt_slide: prompt += "- Trích xuất JSON làm Slide.\n"

                # 4. CƠ CHẾ THỬ SAI LIÊN HOÀN (FIX LỖI 404)
                # Danh sách các model sẽ thử lần lượt nếu cái trước bị lỗi
                backup_models = [
                    user_choice,              # Thử cái người dùng chọn trước
                    "gemini-1.5-flash",       # Thử bản flash thường
                    "gemini-1.5-flash-001",   # Thử bản flash v001 (ổn định nhất)
                    "gemini-1.5-flash-latest",# Thử bản flash mới nhất
                    "gemini-1.5-pro"          # Cuối cùng thử bản Pro
                ]
                
                # Lọc trùng lặp
                backup_models = list(dict.fromkeys(backup_models))
                
                response = None
                last_error = None
                success_model = ""

                for model_name in backup_models:
                    try:
                        # Thử gọi model
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content([prompt, gemini_file])
                        success_model = model_name
                        break # Nếu thành công thì thoát vòng lặp ngay
                    except Exception as e:
                        last_error = e
                        continue # Nếu lỗi thì thử cái tiếp theo trong danh sách

                # 5. Kiểm tra kết quả cuối cùng
                if response:
                    st.success(f"✅ Xử lý thành công! (Đã dùng model: {success_model})")
                    st.markdown(response.text)
                    
                    # Tải về
                    doc = create_docx(response.text)
                    doc_io = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                    doc.save(doc_io.name)
                    with open(doc_io.name, "rb") as f:
                        st.download_button("📥 Tải báo cáo Word", f, "Meeting_Report.docx")
                    os.remove(doc_io.name)
                else:
                    st.error(f"❌ Tất cả các model đều thất bại. Lỗi cuối cùng: {last_error}")

                # Dọn dẹp
                try:
                    genai.delete_file(gemini_file.name)
                    os.remove(tmp_path)
                except: pass

            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    main()
