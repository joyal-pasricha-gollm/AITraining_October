# Exercise 1 — PyMuPDF
# Install: python -m pip install pymupdf
# Use EY_Digital_PDF_Practice.pdf .
# Tasks: 1-8
# Starter:
#
# import fitz
# doc = fitz.open("EY_Digital_PDF_Practice.pdf")
# print("Pages:", len(doc))
# for page in doc:
# print(page.get_text())

import fitz

# 1. Open the PDF
doc = fitz.open("EY_Digital_PDF_Practice.pdf")

# 2. Print the number of pages
total_pages = len(doc)
print("Total Pages:", total_pages)

# 3. Extract and print text from page 1 (Index 0)-get_text()
page1_text = doc[0].get_text()
print("Page 1 Text starts here: ")
print(page1_text)
print("Page 1 Text ends here")

# 4. Extract text from all pages
all_text = ""
for page in doc:
    all_text += page.get_text() + "\n"

# 5. Search whether the word maintenance appears- nornmalise the text by lowering it first
if "maintenance" in all_text.lower():
    print(" 'maintenance' appears in the document")
else:
    print(" 'maintenance' does not appear")

# 6. Count how many times V303 appears-count("the word")
v303_count = all_text.lower().count("v303")
print("Occurrences of 'V303'", v303_count)

# 7. Extract only page 2 text (Index 1)
if total_pages >= 2:
    page2_text = doc[1].get_text()
    print(" Page 2 Text starts...")
    print(page2_text)
    print(" Page 2 Text ends...")
else:
    print("Page 2 does not exist.")

# 8. Save all extracted text into digital_pdf_text.txt
with open("digital_pdf_text.txt", "w", encoding="utf-8") as f:
    f.write(all_text)
doc.close()
