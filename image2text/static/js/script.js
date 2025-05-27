const form = document.getElementById('upload-form');
const imageInput = document.getElementById('imageInput');
const submitButton = document.getElementById('submit-button');
const spinner = document.getElementById('spinner');
const resultDiv = document.getElementById('result');
const descriptionP = document.getElementById('description');
const errorDiv = document.getElementById('error');
const errorMessageP = document.getElementById('error-message');
const previewImg = document.getElementById('preview');

// Ajout : Afficher l'aperçu de l'image sélectionnée
imageInput.addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            previewImg.style.display = 'block'; // Afficher l'aperçu
        }
        reader.readAsDataURL(file);
        resultDiv.style.display = 'none'; // Cacher ancien résultat
        errorDiv.style.display = 'none';  // Cacher ancienne erreur
    } else {
         previewImg.style.display = 'none'; // Cacher si aucun fichier
    }
});


form.addEventListener('submit', async (event) => {
    event.preventDefault(); // Empêche la soumission standard du formulaire

    const file = imageInput.files[0];
    if (!file) {
        errorMessageP.textContent = 'Veuillez sélectionner un fichier image.';
        errorDiv.style.display = 'block';
        resultDiv.style.display = 'none';
        return;
    }

    // Prépare l'UI pour le traitement
    spinner.style.display = 'inline-block'; // Afficher le spinner
    submitButton.disabled = true; // Désactiver le bouton
    resultDiv.style.display = 'none'; // Cacher l'ancien résultat
    errorDiv.style.display = 'none'; // Cacher l'ancienne erreur

    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch('/process', { // Appel à la route Flask
            method: 'POST',
            body: formData,
        });

        const data = await response.json(); // Attend la réponse JSON

        if (!response.ok) {
             // Si le serveur renvoie une erreur (4xx, 5xx)
             throw new Error(data.error || `Erreur serveur ${response.status}`);
        }

        // Succès ! Afficher la description
        descriptionP.textContent = data.description_fr;
        resultDiv.style.display = 'block'; // Afficher la zone de résultat

    } catch (error) {
        console.error('Erreur lors du traitement:', error);
        errorMessageP.textContent = error.message || 'Une erreur inconnue est survenue.';
        errorDiv.style.display = 'block'; // Afficher la zone d'erreur
    } finally {
        // Quoi qu'il arrive (succès ou erreur), réactiver l'UI
        spinner.style.display = 'none'; // Cacher le spinner
        submitButton.disabled = false; // Réactiver le bouton
    }
});