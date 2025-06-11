import streamlit as st
import re
from typing import List
from docx import Document
from pdfminer.high_level import extract_text as pdfminer_extract_text # type: ignore
import pytesseract # type: ignore
from PIL import Image
import io
import camelot # type: ignore
import tempfile
import os

# --------- Text Extraction Functions ---------
def extract_text_from_pdf(file) -> str:
    text = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    try:
        # Use pdfminer for better layout-aware text extraction
        text = pdfminer_extract_text(tmp_path)

        # Try to extract tables using camelot
        tables = camelot.read_pdf(tmp_path, pages='all', flavor='lattice')
        for table in tables:
            text += "\n" + table.df.to_string(index=False, header=True)
    except Exception as e:
        text += f"\n[Error extracting tables: {e}]"
    finally:
        os.unlink(tmp_path)

    return text

def extract_text_from_docx(file) -> str:
    doc = Document(file)
    text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip() != ""])
    return text

def extract_text_from_image(file) -> str:
    image = Image.open(file)
    return pytesseract.image_to_string(image)

# --------- Cleaning Functions ---------
def preprocess_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_resume_text(raw_text: str) -> str:
    cleaned_lines = []
    lines = raw_text.split('\n')

    for line in lines:
        original_line = line
        line = preprocess_text(line)

        if re.fullmatch(r'\d+', line.strip()) or re.fullmatch(r'page \d+ of \d+', line.strip()):
            continue
        if any(keyword in line for keyword in ['confidential', 'all rights reserved', 'template by']):
            continue
        if re.fullmatch(r'[-_]+\s*|={3,}\s*', line.strip()):
            continue
        if len(line.strip()) < 5 and not re.search(r'[a-z0-9]', line):
            continue

        cleaned_lines.append(original_line.strip())

    cleaned_text = '\n'.join([line for line in cleaned_lines if line.strip()])
    cleaned_text = re.sub(r'\n{2,}', '\n\n', cleaned_text).strip()
    return cleaned_text

# --------- Streamlit UI ---------
st.title("Resume Cleaner App")
st.write("Upload PDF, DOCX, or Image resumes to get cleaned and complete text versions.")

uploaded_files = st.file_uploader("Upload Resume Files", type=["pdf", "docx", "png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.subheader(f"\u2705 {uploaded_file.name}")
        try:
            file_ext = uploaded_file.name.lower().split('.')[-1]

            if file_ext == "pdf":
                raw_text = extract_text_from_pdf(uploaded_file)
            elif file_ext == "docx":
                raw_text = extract_text_from_docx(uploaded_file)
            elif file_ext in ["png", "jpg", "jpeg"]:
                raw_text = extract_text_from_image(uploaded_file)
            else:
                st.error("Unsupported file type.")
                continue

            cleaned_text = clean_resume_text(raw_text)

            with st.expander("Raw Extracted Text"):
                st.text_area("Raw Text", raw_text[:], height=200)

            with st.expander("Cleaned Resume Text"):
                st.text_area("Cleaned Text", cleaned_text[:], height=200)

            cleaned_bytes = io.BytesIO(cleaned_text.encode("utf-8"))
            st.download_button(
                label="Download Cleaned Text",
                data=cleaned_bytes,
                file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_cleaned.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"Error processing file: {e}")
