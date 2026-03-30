#!/usr/bin/env python3
"""
Serveur Flask pour traiter les images avec CTA et conversion WebP
Consomme très peu de crédits Make (utilise HTTP Module au lieu de JavaScript)
"""

from flask import Flask, request, jsonify
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.environ.get('PORT', 5000))

def get_cta_from_keyword(keyword):
    """
    Détermine le CTA selon le keyword
    """
    keyword_lower = keyword.lower()
    
    # Condition 1 : GUIDE INSIDE
    if any(word in keyword_lower for word in ['princess', 'formal', 'gown']):
        return 'GUIDE INSIDE'
    
    # Condition 2 : STYLE TIPS
    if any(word in keyword_lower for word in ['casual', 'everyday', 'simple']):
        return 'STYLE TIPS'
    
    # Condition 3 : STYLING TIPS INSIDE
    if any(word in keyword_lower for word in ['summer', 'spring', 'seasonal']):
        return 'STYLING TIPS INSIDE'
    
    # Condition 4 : COMPLETE DRESS GUIDE
    if any(word in keyword_lower for word in ['elegant', 'luxury', 'premium']):
        return 'COMPLETE DRESS GUIDE'
    
    # CTA par défaut
    return 'SHOP NOW'


def add_cta_to_image(image_data, keyword, cta_text=None):
    """
    Ajoute le CTA et keyword sur l'image
    """
    
    # Déterminer le CTA si non fourni
    if cta_text is None:
        cta_text = get_cta_from_keyword(keyword)
    
    # Convertir base64 en bytes si nécessaire
    if isinstance(image_data, str):
        try:
            image_data = base64.b64decode(image_data)
        except Exception as e:
            logger.error(f"Erreur décodage base64: {e}")
            raise
    
    # Ouvrir l'image
    img = Image.open(io.BytesIO(image_data)).convert('RGBA')
    width, height = img.size
    
    # Créer une copie pour le dessin
    img_with_text = img.copy()
    draw = ImageDraw.Draw(img_with_text, 'RGBA')
    
    # Charger les polices
    try:
        font_keyword = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        font_cta = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except:
        font_keyword = ImageFont.load_default()
        font_cta = ImageFont.load_default()
    
    # Formater le texte
    keyword_text = keyword.upper()
    cta_text = cta_text.upper()
    
    # Calculer les positions (haut à droite)
    # Position: NorthEast = haut à droite
    # +30+30 = 30px à droite, 30px du haut
    
    bbox_keyword = draw.textbbox((0, 0), keyword_text, font=font_keyword)
    keyword_width = bbox_keyword[2] - bbox_keyword[0]
    
    bbox_cta = draw.textbbox((0, 0), cta_text, font=font_cta)
    cta_width = bbox_cta[2] - bbox_cta[0]
    
    max_text_width = max(keyword_width, cta_width)
    text_x = width - max_text_width - 30
    text_y = 30
    
    # Dessiner le keyword
    draw.text((text_x, text_y), keyword_text, font=font_keyword, fill=(0, 0, 0, 255))
    
    # Dessiner le CTA (plus bas)
    cta_y = text_y + 65
    draw.text((text_x, cta_y), cta_text, font=font_cta, fill=(0, 0, 0, 255))
    
    # Convertir en RGB pour WebP
    background = Image.new('RGB', img_with_text.size, (255, 255, 255))
    background.paste(img_with_text, mask=img_with_text.split()[3])
    img_with_text = background
    
    # Sauvegarder en bytes
    output = io.BytesIO()
    img_with_text.save(output, format='WEBP', quality=85)
    output.seek(0)
    
    return output.getvalue()


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de santé"""
    return jsonify({
        'status': 'ok',
        'service': 'CTA WebP Image Processor',
        'version': '1.0'
    })


@app.route('/process-image', methods=['POST'])
def process_image():
    """
    Endpoint pour traiter une image
    
    Payload JSON:
    {
        "image": "base64_encoded_image",
        "keyword": "Pink Princess Dress",
        "cta_text": "GUIDE INSIDE" (optionnel - déterminé automatiquement si non fourni)
    }
    
    Response:
    {
        "success": true,
        "image": "base64_encoded_webp_image",
        "fileName": "Pink Princess Dress.webp",
        "keyword": "Pink Princess Dress",
        "cta_text": "GUIDE INSIDE"
    }
    """
    
    try:
        data = request.get_json()
        
        # Valider les données requises
        if not data or 'image' not in data or 'keyword' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: image, keyword'
            }), 400
        
        # Extraire les paramètres
        image_data = data['image']
        keyword = data['keyword']
        cta_text = data.get('cta_text', None)  # Optionnel
        
        logger.info(f"Processing image for keyword: {keyword}")
        
        # Traiter l'image
        result_image = add_cta_to_image(image_data, keyword, cta_text)
        
        # Déterminer le CTA final
        final_cta = cta_text if cta_text else get_cta_from_keyword(keyword)
        
        # Encoder en base64
        result_base64 = base64.b64encode(result_image).decode('utf-8')
        
        logger.info(f"Image processed successfully for keyword: {keyword}")
        
        return jsonify({
            'success': True,
            'image': result_base64,
            'fileName': keyword + '.webp',
            'keyword': keyword,
            'cta_text': final_cta,
            'message': 'Image processed successfully'
        })
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/process-image-url', methods=['POST'])
def process_image_url():
    """
    Endpoint pour traiter une image depuis une URL
    
    Payload JSON:
    {
        "image_url": "https://...",
        "keyword": "Pink Princess Dress",
        "cta_text": "GUIDE INSIDE" (optionnel)
    }
    """
    
    try:
        import requests
        
        data = request.get_json()
        
        if not data or 'image_url' not in data or 'keyword' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: image_url, keyword'
            }), 400
        
        image_url = data['image_url']
        keyword = data['keyword']
        cta_text = data.get('cta_text', None)
        
        logger.info(f"Downloading image from: {image_url}")
        
        # Télécharger l'image
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Failed to download image: {response.status_code}'
            }), 400
        
        image_data = response.content
        
        # Traiter l'image
        result_image = add_cta_to_image(image_data, keyword, cta_text)
        
        # Déterminer le CTA final
        final_cta = cta_text if cta_text else get_cta_from_keyword(keyword)
        
        result_base64 = base64.b64encode(result_image).decode('utf-8')
        
        logger.info(f"Image processed successfully from URL for keyword: {keyword}")
        
        return jsonify({
            'success': True,
            'image': result_base64,
            'fileName': keyword + '.webp',
            'keyword': keyword,
            'cta_text': final_cta,
            'message': 'Image processed successfully'
        })
    
    except Exception as e:
        logger.error(f"Error processing image from URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
