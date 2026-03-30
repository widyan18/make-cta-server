#!/usr/bin/env python3
from flask import Flask, request, jsonify
import base64
import subprocess
import os
import tempfile

app = Flask(__name__ )

def get_cta_from_keyword(keyword):
    keyword_lower = keyword.lower()
    if any(word in keyword_lower for word in ['princess', 'formal', 'gown']):
        return 'GUIDE INSIDE'
    if any(word in keyword_lower for word in ['casual', 'everyday', 'simple']):
        return 'STYLE TIPS'
    if any(word in keyword_lower for word in ['summer', 'spring', 'seasonal']):
        return 'STYLING TIPS INSIDE'
    if any(word in keyword_lower for word in ['elegant', 'luxury', 'premium']):
        return 'COMPLETE DRESS GUIDE'
    return 'SHOP NOW'

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'CTA WebP Image Processor', 'version': '1.0'})

@app.route('/process-image', methods=['POST'])
def process_image():
    try:
        data = request.get_json()
        if not data or 'image' not in data or 'keyword' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        image_data = data['image']
        keyword = data['keyword']
        cta_text = get_cta_from_keyword(keyword)
        
        # Créer des fichiers temporaires
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as input_file:
            input_path = input_file.name
            input_file.write(base64.b64decode(image_data))
        
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Utiliser ImageMagick pour ajouter le texte
            cmd = [
                'convert', input_path,
                '-gravity', 'NorthEast',
                '-pointsize', '56',
                '-font', 'DejaVu-Sans-Bold',
                '-fill', 'black',
                '-annotate', '+30+30', keyword.upper(),
                '-pointsize', '36',
                '-annotate', '+30+95', cta_text,
                '-quality', '85',
                output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Lire le résultat
            with open(output_path, 'rb') as f:
                result_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            return jsonify({
                'success': True,
                'image': result_base64,
                'fileName': keyword + '.webp',
                'keyword': keyword,
                'cta_text': cta_text
            })
        finally:
            os.unlink(input_path)
            os.unlink(output_path)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
