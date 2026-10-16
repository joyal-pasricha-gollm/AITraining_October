# Exercise 2 — PyPDF
# Install: python -m pip install pypdf
# Use the same digital PDF.
#
# Tasks: 1-8
# Starter:
# from pypdf import PdfReader
# reader = PdfReader("EY_Digital_PDF_Practice.pdf")
# print("Pages:", len(reader.pages))
# for page in reader.pages:
# print(page.extract_text())

from pypdf import PdfReader

# 1. Open the PDF using PdfReader
reader = PdfReader("EY_Digital_PDF_Practice.pdf")

# 2. Print the number of pages-len
total_pages = len(reader.pages)
print("Total Pages:",total_pages)

# 3. Extract text from the first page (Index 0)-pages[].extract_text()
text_p1 = reader.pages[0].extract_text() or ""
print("First Page Text starts..")
print(text_p1)
print(".....First Page Text ends here")


# 4. Extract text from the second page (Index 1)
text_p2 = ""
if total_pages >= 2:
    text_p2 = reader.pages[1].extract_text() or ""
    print("Second Page Text starts...")
    print(text_p2)
    print("....Second Page Text ends here")

# 5. Combine text from both pages into one string
combined_text = text_p1 + "\n" + text_p2

# Extract full text from all pages for complete keyword searches
full_text = ""
for page in reader.pages:
    full_text += (page.extract_text() or "") + "\n"

# 6. Check whether NorthStar Maintenance exists in the PDF
if "northstar maintenance" in full_text.lower():
    print("'NorthStar Maintenance' exists.")
else:
    print("'NorthStar Maintenance' not found.")

# 7. Find the number of occurrences of the word vendor
vendor_count = full_text.lower().count("vendor")
print("Occurrences of 'vendor':",vendor_count)

# 8. Save the extracted content into pypdf_output.txt
with open("pypdf_output.txt", "w", encoding="utf-8") as f:
    f.write(full_text)


