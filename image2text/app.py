from flask import Flask, request, render_template, jsonify
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration, MarianMTModel, MarianTokenizer
from PIL import Image
import io
import time # Pour mesurer le temps si besoin

# --- Configuration Flask ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Limite taille upload (ex: 16MB)

if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("Utilisation du backend MPS (Apple Silicon Metal).")
elif torch.cuda.is_available():
     device = torch.device("cuda")
     print("Utilisation du backend CUDA.")
else:
    device = torch.device("cpu")
    print("Utilisation du backend CPU.")

# --- Chargement des Modèles (une seule fois au démarrage !) ---
print("Chargement des modèles ML (cela peut prendre un moment)...")
try:
    # Modèle BLIP (Image-to-Text)
    print(" - Chargement BLIP...")
    # Utiliser 'base' pour commencer, moins gourmand que 'large'
    blip_model_name = "Salesforce/blip-image-captioning-base"
    img2text_processor = BlipProcessor.from_pretrained(blip_model_name)
    img2text_model = BlipForConditionalGeneration.from_pretrained(blip_model_name).to(device)
    img2text_model.eval() # Mettre en mode évaluation
    print("   BLIP chargé.")

    # Modèle de Traduction (En -> Fr)
    print(" - Chargement Traduction (Helsinki-NLP)...")
    translator_model_name = 'Helsinki-NLP/opus-mt-en-fr'
    translator_tokenizer = MarianTokenizer.from_pretrained(translator_model_name)
    translator_model = MarianMTModel.from_pretrained(translator_model_name).to(device)
    translator_model.eval() 
    print("   Traducteur chargé.")
    models_loaded = True
    print("Modèles chargés avec succès !")

except Exception as e:
    print(f"ERREUR CRITIQUE: Impossible de charger les modèles ML: {e}")
    models_loaded = False

# --- Routes Flask ---
@app.route('/')
def index():
    """Sert la page HTML principale."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_image():
    """Reçoit l'image, la traite et renvoie la description."""
    start_time = time.time()

    if not models_loaded:
        return jsonify({'error': 'Les modèles ML ne sont pas disponibles.'}), 503 # Service Unavailable

    if 'image' not in request.files:
        return jsonify({'error': 'Aucun fichier image fourni.'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné.'}), 400

    # Validation simple du type 
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
         return jsonify({'error': 'Type de fichier non autorisé (png, jpg, jpeg seulement).'}), 400

    try:
        # Lire les bytes de l'image
        image_bytes = file.read()
        raw_image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

        # --- Inférence BLIP ---
        print("Processing BLIP...")
        # Prépare l'image et l'envoie sur le device 
        inputs = img2text_processor(raw_image, return_tensors="pt").to(device)
        # Génère la légende
        with torch.no_grad(): # Important pour l'inférence
             out = img2text_model.generate(**inputs, max_new_tokens=50)
        english_caption = img2text_processor.decode(out[0], skip_special_tokens=True)
        print(f"  -> Légende EN: {english_caption}")

        # --- Inférence Traduction ---
        print("Processing Translation...")
        # Prépare le texte et l'envoie sur le device
        batch = translator_tokenizer([english_caption], return_tensors="pt", padding=True).to(device)
        # Génère la traduction
        with torch.no_grad(): # Important pour l'inférence
             translated_tokens = translator_model.generate(**batch)
        french_caption = translator_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
        print(f"  -> Légende FR: {french_caption}")

        end_time = time.time()
        print(f"Temps de traitement total: {end_time - start_time:.2f} secondes")

        # Renvoie le résultat au format JSON
        return jsonify({'description_fr': french_caption})

    except Exception as e:
        print(f"Erreur durant le traitement de l'image: {e}")
        # Loggez l'erreur complète côté serveur pour le débogage
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur interne du serveur: {e}'}), 500

# --- Démarrage de l'application ---
if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5001)
