# Install dependencies
brew install tesseract tesseract-lang
pip install PyMuPDF pytesseract Pillow

# Process a PDF
python ocr_pdf_cli.py document.pdf
python ocr_pdf_cli.py document.pdf -o output.html

# Show setup instructions
python ocr_pdf_cli.py --setup
