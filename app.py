import os
import base64
from flask import Flask, request, render_template_string, send_file, jsonify
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 50MB max

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# HTML template for the upload page
UPLOAD_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>OCR PDF Processor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .upload-area {
            border: 3px dashed #ccc;
            padding: 40px;
            text-align: center;
            margin: 20px 0;
            cursor: pointer;
            transition: border-color 0.3s;
        }
        .upload-area:hover {
            border-color: #4CAF50;
        }
        .upload-area.dragover {
            border-color: #4CAF50;
            background-color: #f0f8f0;
        }
        input[type="file"] {
            display: none;
        }
        .file-info {
            margin: 10px 0;
            color: #666;
        }
        .button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
            transition: background-color 0.3s;
        }
        .button:hover {
            background-color: #45a049;
        }
        .button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .progress {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background-color: #e8f5e9;
            border-radius: 5px;
            text-align: center;
        }
        .error {
            color: #f44336;
            margin-top: 10px;
            display: none;
        }
        .success {
            color: #4CAF50;
            margin-top: 10px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 OCR PDF Processor</h1>
        <p style="text-align: center; color: #666;">Upload a scanned PDF to extract text and create an HTML version</p>
        
        <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
            <div style="font-size: 48px; margin-bottom: 10px;">📁</div>
            <div><strong>Click to upload</strong> or drag and drop</div>
            <div style="color: #999; margin-top: 5px;">PDF files only</div>
        </div>
        
        <input type="file" id="fileInput" accept=".pdf" />
        <div class="file-info" id="fileInfo"></div>
        
        <button class="button" id="processBtn" onclick="processFile()" disabled>Process PDF</button>
        
        <div class="progress" id="progress">
            <div>⏳ Processing... This may take a few minutes</div>
        </div>
        
        <div class="success" id="success"></div>
        <div class="error" id="error"></div>
    </div>

    <script>
        let selectedFile = null;
        
        // Drag and drop functionality
        const uploadArea = document.getElementById('uploadArea');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
        
        document.getElementById('fileInput').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
        
        function handleFile(file) {
            if (file.type !== 'application/pdf') {
                showError('Please upload a PDF file');
                return;
            }
            
            selectedFile = file;
            document.getElementById('fileInfo').innerHTML = 
                `<strong>Selected file:</strong> ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
            document.getElementById('processBtn').disabled = false;
            document.getElementById('error').style.display = 'none';
            document.getElementById('success').style.display = 'none';
        }
        
        function processFile() {
            if (!selectedFile) return;
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            document.getElementById('processBtn').disabled = true;
            document.getElementById('progress').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('success').style.display = 'none';
            
            fetch('/process', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('progress').style.display = 'none';
                if (data.success) {
                    document.getElementById('success').style.display = 'block';
                    document.getElementById('success').innerHTML = 
                        `✅ Processing complete! <a href="/download/${data.filename}" target="_blank">Download HTML file</a>`;
                    document.getElementById('processBtn').disabled = false;
                } else {
                    showError(data.error || 'An error occurred');
                    document.getElementById('processBtn').disabled = false;
                }
            })
            .catch(error => {
                document.getElementById('progress').style.display = 'none';
                showError('Network error: ' + error.message);
                document.getElementById('processBtn').disabled = false;
            });
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.innerHTML = '❌ ' + message;
            errorDiv.style.display = 'block';
        }
    </script>
</body>
</html>
'''

def generate_ocr_html(pdf_path):
    """Generate HTML with OCR'd text positioned absolutely on each page"""
    
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
    
    # Process each page
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        
        # Get page dimensions
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Convert page to image for OCR
        # Scale factor for better OCR quality
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
        current_word = []
        current_word_bbox = None
        
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = float(ocr_data['conf'][i])
            
            if conf > 30:  # Filter out low confidence detections
                if text:
                    # Get bounding box coordinates (scaled back to PDF coordinates)
                    x = ocr_data['left'][i] / zoom
                    y = ocr_data['top'][i] / zoom
                    max_font_size = 8.5
                    #y = int(y/max_font_size)*max_font_size
                    width = ocr_data['width'][i] / zoom
                    height = ocr_data['height'][i] / zoom
                    
                    # Get font size from OCR data
                    font_size = ocr_data['height'][i] / zoom
                    if font_size > max_font_size:
                        font_size = max_font_size
                    
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
    
    return html_content

@app.route('/')
def index():
    return render_template_string(UPLOAD_PAGE)

@app.route('/process', methods=['POST'])
def process_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Please upload a PDF file'})
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        # Generate OCR HTML
        html_content = generate_ocr_html(pdf_path)
        
        # Save HTML file
        html_filename = filename.rsplit('.', 1)[0] + '_ocr.html'
        html_path = os.path.join(app.config['OUTPUT_FOLDER'], html_filename)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Clean up uploaded PDF (optional)
        os.remove(pdf_path)
        
        return jsonify({
            'success': True,
            'filename': html_filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(app.config['OUTPUT_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5036)
