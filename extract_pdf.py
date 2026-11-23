import pdfplumber

with pdfplumber.open('sample_reports.pdf') as pdf:
    text = '\n'.join((page.extract_text() or '') for page in pdf.pages)

print(text)
