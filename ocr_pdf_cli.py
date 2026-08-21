# ocr_pdf_cli.py
import os
import argparse
import sys
import base64
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import json
from pathlib import Path
import subprocess

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fitz
        import pytesseract
        from PIL import Image
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages: pip install PyMuPDF pytesseract Pillow")
        return False

def generate_ocr_html(pdf_path, output_path):
    """Generate HTML with OCR'd text positioned absolutely on each page"""
    
    try:
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        html_content = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OCR PDF Result</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background-color: #f0f0f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .page-container {
            position: relative;
            background: white;
            margin: 20px auto;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            page-break-after: always;
        }
        .char {
            position: absolute;
            white-space: pre;
            pointer-events: none;
            user-select: none;
            line-height: 1;
        }
        .page-number {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin: 5px 0;
            font-family: Arial, sans-serif;
        }
        @media print {
            body {
                background: white;
                padding: 0;
            }
            .page-container {
                margin: 0;
                box-shadow: none;
            }
            .page-number {
                display: none;
            }
        }
    </style>
</head>
<body>
'''
        
        print(f"Processing PDF with {len(pdf_document)} pages...")
        
        # Process each page
        for page_num in range(len(pdf_document)):
            print(f"Processing page {page_num + 1}/{len(pdf_document)}")
            page = pdf_document[page_num]
            
            # Get page dimensions
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Convert page to image for OCR
            zoom = 2  # 2x zoom for better OCR
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Perform OCR with detailed output
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Add page container
            html_content += f'''
    <div class="page-number">Page {page_num + 1}</div>
    <div class="page-container" style="width: {page_width:.2f}pt; height: {page_height:.2f}pt;">
'''
            
            # Process OCR data
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                conf = float(ocr_data['conf'][i])
                
                if conf > 30:  # Filter out low confidence detections
                    if text:
                        # Get bounding box coordinates (scaled back to PDF coordinates)
                        x = ocr_data['left'][i] / zoom
                        y = ocr_data['top'][i] / zoom
                        #max_font_size = 11
                        width = ocr_data['width'][i] / zoom
                        height = ocr_data['height'][i] / zoom
                        
                        # Get font size from OCR data
                        font_size = ocr_data['height'][i] / zoom
                        #if font_size > max_font_size:
                            #font_size = max_font_size
                        
                        # Process each character in the text
                        char_width = width / len(text)
                        for j, char in enumerate(text):
                            char_x = x + (j * char_width)
                            
                            # HTML escape for special characters
                            char_html = char.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            
                            html_content += f'''
        <span class="char" style="left: {char_x:.2f}pt; top: {y:.2f}pt; font-size: {font_size:.2f}pt; width: {char_width:.2f}pt; height: {height:.2f}pt;">{char_html}</span>'''
            
            html_content += '''
    </div>
'''
        
        html_content += '''
</body>
</html>
'''
        
        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ OCR HTML generated: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return False

def process_pdf_cli(pdf_path, output_path=None):
    """Main CLI function to process PDF"""
    
    # Check if input file exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File '{pdf_path}' not found")
        return False
    
    if not pdf_path.lower().endswith('.pdf'):
        print("❌ Error: Input must be a PDF file")
        return False
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Set output path
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_dir = os.path.dirname(pdf_path)
        output_path = os.path.join(output_dir, f"{base_name}_ocr.html")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Generate OCR HTML
    print(f"📄 Processing: {pdf_path}")
    print(f"📁 Output: {output_path}")
    print("⏳ Running OCR... This may take a few minutes for large PDFs")
    
    success = generate_ocr_html(pdf_path, output_path)
    
    if success:
        print(f"✅ Processing complete!")
        print(f"📄 Output saved to: {output_path}")
    else:
        print("❌ Processing failed")
    
    return success

def setup_tesseract_macos():
    """Setup instructions for macOS"""
    print("🍎 Setting up Tesseract on macOS...")
    print("Please run: brew install tesseract tesseract-lang")
    print("Then: pip install pytesseract PyMuPDF Pillow")
    print("\nAfter installation, you can use the CLI tool")

def main():
    parser = argparse.ArgumentParser(
        description='OCR PDF and generate HTML with positioned text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python ocr_pdf_cli.py input.pdf
  python ocr_pdf_cli.py input.pdf -o output.html
  python ocr_pdf_cli.py input.pdf --setup  # Show setup instructions
        '''
    )
    
    parser.add_argument('pdf_file', nargs='?', help='Path to the PDF file to process')
    parser.add_argument('-o', '--output', help='Output HTML file path (default: input_ocr.html)')
    parser.add_argument('--setup', action='store_true', help='Show setup instructions')
    parser.add_argument('--version', action='version', version='OCR PDF CLI 1.0.0')
    
    args = parser.parse_args()
    
    if args.setup:
        setup_tesseract_macos()
        return
    
    if not args.pdf_file:
        parser.print_help()
        return
    
    # Run the OCR process
    process_pdf_cli(args.pdf_file, args.output)

if __name__ == '__main__':
    main()
