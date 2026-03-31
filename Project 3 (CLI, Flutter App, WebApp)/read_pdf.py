import PyPDF2

with open('694300494-nsu.pdf', 'rb') as pdf_file:
    reader = PyPDF2.PdfReader(pdf_file)
    text = ''
    for page in reader.pages:
        text += page.extract_text()
    print(text)
