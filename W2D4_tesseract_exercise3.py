import fitz
import pytesseract
from PIL import Image

# for verification: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 1. Open the scanned PDF using PyMuPDF
doc = fitz.open("EY_Scanned_PDF_OCR_Practice.pdf")

# 2. Convert the PDF page into an image (Using page 1/index 0)
page = doc[0]
pix = page.get_pixmap()
pix.save("scanned_page.png")

# 3. Run Tesseract OCR on the image
image = Image.open("scanned_page.png")
ocr_text = pytesseract.image_to_string(image)

# 4. Print the extracted text
print("Extracted OCR Text starts....")
print(ocr_text)
print("Extracted OCR Text starts....")
print("Extracted OCR Text ends....")

# Tokenize lines for targeting specific rules
lines = ocr_text.splitlines()

# 5. Check whether Forklift FL-17 was detected
if "forklift fl-17" in ocr_text.lower():
    print("'Forklift FL-17' detected.")
else:
    print("'Forklift FL-17' not detected.")

# 6. Search for the word injuries
if "injuries" in ocr_text.lower():
    print("Result: 'injuries' detected.")
else:
    print("Result: 'injuries' not detected.")

# 7. Extract lines mentioning inspection
print(" Lines mentioning 'inspection' are: ")
for line in lines:
    if "inspection" in line.lower():
        print(line.strip())

# 8. Save the OCR output into ocr_result.txt
with open("ocr_result.txt", "w", encoding="utf-8") as f:
    f.write(ocr_text)

# 9. Count the number of times inspection appears
inspection_count = ocr_text.lower().count("inspection")
print("Total occurrences of 'inspection':",inspection_count)

# 10. Print all lines containing Loading Bay
print(" Lines containing 'Loading Bay'....-")
for line in lines:
    if "loading bay" in line.lower():
        print(line.strip())

doc.close()
