import streamlit as st
import pdfplumber
import tempfile
import csv
from PyPDF2 import PdfReader, PdfWriter, PdfMerger

# HELPER: Detect table headers
def is_header(row):
    text_cells = 0
    for cell in row:
        if cell and any(c.isalpha() for c in cell):
            text_cells += 1
    return text_cells >= len(row) / 2

# FEATURE 1: TABLE EXTRACTION
def extract_tables(pdf_path, csv_output):
    with pdfplumber.open(pdf_path) as pdf:
        all_rows = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    all_rows.append(row)
                all_rows.append([])

    with open(csv_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(all_rows)

# FEATURE 2: IMAGE EXTRACTION
def extract_images(pdf_path, output_folder):
    reader = PdfReader(pdf_path)
    count = 1
    saved_files = []

    for page_number, page in enumerate(reader.pages, start=1):
        if "/Resources" not in page:
            continue
        resources = page["/Resources"]

        if "/XObject" not in resources:
            continue

        xobjects = resources["/XObject"].get_object()

        for obj_name in xobjects:
            xobj = xobjects[obj_name]
            if xobj.get("/Subtype") == "/Image":
                data = xobj.get_data()

                if xobj.get("/Filter") == "/DCTDecode":
                    ext = "jpg"
                elif xobj.get("/Filter") == "/JPXDecode":
                    ext = "jp2"
                else:
                    ext = "png"

                filename = f"{output_folder}/image_{count}.{ext}"
                with open(filename, "wb") as f:
                    f.write(data)

                saved_files.append(filename)
                count += 1

    return saved_files

# FEATURE 3: SPLIT PDF
def split_pdf(pdf_path, folder):
    reader = PdfReader(pdf_path)
    output_files = []

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        output_path = f"{folder}/page_{i+1}.pdf"

        with open(output_path, "wb") as f:
            writer.write(f)

        output_files.append(output_path)

    return output_files

# FEATURE 4: MERGE PDF
def merge_pdfs(files, output_path):
    merger = PdfMerger()
    for f in files:
        merger.append(f)

    merger.write(output_path)
    merger.close()

# FEATURE 5: PASSWORD PROTECT PDF
def encrypt_pdf(input_path, output_path, password):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password)

    with open(output_path, "wb") as f:
        writer.write(f)

# FEATURE 6: REMOVE PASSWORD 
def decrypt_pdf(input_path, output_path, password):
    reader = PdfReader(input_path)
    if reader.is_encrypted:
        try:
            reader.decrypt(password)
        except:
            return False

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return True

# STREAMLIT UI — MULTI PAGE MENU
st.title("📄 PDF TOOLKIT")

page = st.sidebar.radio(
    "Choose a feature:",
    [
        "Extract Tables",
        "Extract Images",
        "Split PDF",
        "Merge PDFs",
        "Password Protect PDF",
        "Remove Password"
    ]
)

# PAGE: TABLE EXTRACTION
if page == "Extract Tables":
    st.header("📊 Extract Tables to CSV")

    uploaded = st.file_uploader("Upload a PDF", type=["pdf"])

    if uploaded:
        if st.button("Extract Tables"):
            with st.spinner("Extracting…"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(uploaded.read())
                    pdf_path = tmp_pdf.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
                    csv_path = tmp_csv.name

                extract_tables(pdf_path, csv_path)

            with open(csv_path, "rb") as f:
                st.download_button(
                    "⬇️ Download CSV",
                    f,
                    "extracted_tables.csv",
                    "text/csv"
                )
# PAGE: IMAGE EXTRACTION
elif page == "Extract Images":
    st.header("🖼 Extract Images from PDF")

    uploaded = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded:
        if st.button("Extract Images"):
            with st.spinner("Extracting images…"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(uploaded.read())
                    pdf_path = tmp_pdf.name

                tmp_dir = tempfile.mkdtemp()
                extracted_files = extract_images(pdf_path, tmp_dir)

            if extracted_files:
                st.success(f"Extracted {len(extracted_files)} images!")

                for path in extracted_files:
                    with open(path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Download {path.split('/')[-1]}",
                            data=f,
                            file_name=path.split("/")[-1]
                        )
            else:
                st.warning("No images found in this PDF.")

# PAGE: SPLIT PDF
elif page == "Split PDF":
    st.header("✂️ Split PDF into Pages")

    uploaded = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded:
        if st.button("Split PDF"):
            with st.spinner("Splitting pages…"):
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(uploaded.read())
                    pdf_path = tmp.name

                tmp_folder = tempfile.mkdtemp()
                pages = split_pdf(pdf_path, tmp_folder)

            st.success("PDF split successfully!")

            for p in pages:
                with open(p, "rb") as f:
                    st.download_button(
                        f"⬇️ Download {p.split('/')[-1]}",
                        f,
                        p.split("/")[-1]
                    )

# PAGE: MERGE PDFs
elif page == "Merge PDFs":
    st.header("📎 Merge Multiple PDFs")

    uploads = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

    if uploads:
        if st.button("Merge"):
            with st.spinner("Merging…"):
                tmp_paths = []
                for u in uploads:
                    t = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    t.write(u.read())
                    tmp_paths.append(t.name)

                out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
                merge_pdfs(tmp_paths, out_file)

            with open(out_file, "rb") as f:
                st.download_button(
                    "⬇️ Download Merged PDF",
                    f,
                    "merged.pdf"
                )

# PAGE: PASSWORD PROTECTION

elif page == "Password Protect PDF":
    st.header("🔐 Protect PDF")

    uploaded = st.file_uploader("Upload PDF", type=["pdf"])
    password = st.text_input("Password", type="password")

    if uploaded and password:
        if st.button("Protect"):
            with st.spinner("Protecting…"):
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(uploaded.read())
                    input_path = tmp.name

                output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
                encrypt_pdf(input_path, output_path, password)

            with open(output_path, "rb") as f:
                st.download_button("⬇️ Download Password Protected PDF", f, "protected.pdf")

# PAGE: REMOVE PASSWORD
elif page == "Remove Password":
    st.header("🔓 Remove Password")

    uploaded = st.file_uploader("Upload PDF", type=["pdf"])
    password = st.text_input("Password", type="password")

    if uploaded and password:
        if st.button("Remove Password"):
            with st.spinner("Removing Password…"):
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(uploaded.read())
                    input_path = tmp.name

                output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
                ok = decrypt_pdf(input_path, output_path, password)

            if ok:
                with open(output_path, "rb") as f:
                    st.download_button("⬇️ Download PDF after removing password", f, "removed-password.pdf")
            else:
                st.error("Wrong password! Unable to remove password.")
