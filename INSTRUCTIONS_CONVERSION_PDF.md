# Instructions pour Convertir le Mémoire Technique en PDF

## Méthode 1 : Pandoc (Recommandée)

### Installation de Pandoc

**Windows :**
```powershell
# Télécharger depuis https://pandoc.org/installing.html
# Ou via Chocolatey
choco install pandoc

# Installer LaTeX (pour PDF de qualité)
choco install miktex
```

**Linux :**
```bash
sudo apt-get install pandoc
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**macOS :**
```bash
brew install pandoc
brew install basictex
```

### Conversion Markdown → PDF

**Commande de base :**
```bash
pandoc MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md -o MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.pdf
```

**Commande avec options avancées (recommandée) :**
```bash
pandoc MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md \
  -o MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.pdf \
  --pdf-engine=xelatex \
  --toc \
  --toc-depth=3 \
  --number-sections \
  -V geometry:margin=2.5cm \
  -V fontsize=11pt \
  -V documentclass=report \
  -V lang=fr \
  --highlight-style=tango
```

**Explication des options :**
- `--pdf-engine=xelatex` : Moteur PDF moderne (support Unicode)
- `--toc` : Génère une table des matières
- `--toc-depth=3` : Profondeur de la table des matières (3 niveaux)
- `--number-sections` : Numérotation automatique des sections
- `-V geometry:margin=2.5cm` : Marges de 2.5cm
- `-V fontsize=11pt` : Taille de police 11pt
- `-V documentclass=report` : Format rapport (avec chapitres)
- `-V lang=fr` : Langue française
- `--highlight-style=tango` : Coloration syntaxique pour le code

---

## Méthode 2 : Markdown to PDF (VS Code Extension)

### Installation

1. Ouvrir VS Code
2. Aller dans Extensions (Ctrl+Shift+X)
3. Chercher "Markdown PDF"
4. Installer l'extension de **yzane**

### Conversion

1. Ouvrir `MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md` dans VS Code
2. Appuyer sur `Ctrl+Shift+P`
3. Taper "Markdown PDF: Export (pdf)"
4. Le PDF sera généré dans le même dossier

### Configuration (optionnelle)

Créer `.vscode/settings.json` :
```json
{
  "markdown-pdf.format": "A4",
  "markdown-pdf.margin.top": "2cm",
  "markdown-pdf.margin.bottom": "2cm",
  "markdown-pdf.margin.left": "2cm",
  "markdown-pdf.margin.right": "2cm",
  "markdown-pdf.displayHeaderFooter": true,
  "markdown-pdf.headerTemplate": "<div style='font-size:9px; margin-left:1cm;'>Mémoire Technique - Architecture SMA</div>",
  "markdown-pdf.footerTemplate": "<div style='font-size:9px; margin:0 auto;'><span class='pageNumber'></span> / <span class='totalPages'></span></div>"
}
```

---

## Méthode 3 : Typora (Interface Graphique)

### Installation

1. Télécharger Typora depuis https://typora.io/
2. Installer l'application

### Conversion

1. Ouvrir `MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md` dans Typora
2. Menu : `File` → `Export` → `PDF`
3. Choisir le dossier de destination
4. Cliquer sur `Save`

**Avantages :**
- Interface WYSIWYG (What You See Is What You Get)
- Prévisualisation en temps réel
- Personnalisation du thème

---

## Méthode 4 : Markdown to PDF en Ligne

### Sites recommandés

1. **Markdown to PDF** : https://www.markdowntopdf.com/
   - Glisser-déposer le fichier .md
   - Télécharger le PDF généré

2. **CloudConvert** : https://cloudconvert.com/md-to-pdf
   - Upload du fichier .md
   - Conversion automatique
   - Téléchargement du PDF

**Avantages :**
- Pas d'installation nécessaire
- Rapide et simple

**Inconvénients :**
- Moins de contrôle sur le formatage
- Nécessite une connexion internet

---

## Méthode 5 : Python (Script Automatisé)

### Installation des dépendances

```bash
pip install markdown2 pdfkit
```

**Windows uniquement :** Installer wkhtmltopdf
```powershell
choco install wkhtmltopdf
```

### Script de conversion

Créer `convert_to_pdf.py` :

```python
import markdown2
import pdfkit

# Lire le fichier Markdown
with open('MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

# Convertir Markdown → HTML
html_content = markdown2.markdown(md_content, extras=['tables', 'fenced-code-blocks', 'header-ids'])

# Template HTML avec style
html_template = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 5px;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""

# Options PDF
options = {
    'page-size': 'A4',
    'margin-top': '2cm',
    'margin-right': '2cm',
    'margin-bottom': '2cm',
    'margin-left': '2cm',
    'encoding': 'UTF-8',
    'enable-local-file-access': None
}

# Convertir HTML → PDF
pdfkit.from_string(html_template, 'MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.pdf', options=options)

print("✅ PDF généré avec succès : MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.pdf")
```

### Exécution

```bash
python convert_to_pdf.py
```

---

## Recommandation Finale

**Pour la meilleure qualité :** Utilisez **Pandoc avec LaTeX** (Méthode 1)

**Commande complète recommandée :**

```bash
pandoc MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md \
  -o MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.pdf \
  --pdf-engine=xelatex \
  --toc \
  --toc-depth=3 \
  --number-sections \
  -V geometry:margin=2.5cm \
  -V fontsize=11pt \
  -V documentclass=report \
  -V lang=fr \
  -V mainfont="DejaVu Sans" \
  --highlight-style=tango \
  --metadata title="Mémoire Technique - Architecture SMA" \
  --metadata author="Projet Traffic SMA" \
  --metadata date="Février 2026"
```

Cette commande génère un PDF professionnel avec :
- ✅ Table des matières cliquable
- ✅ Numérotation des sections
- ✅ Coloration syntaxique du code
- ✅ Formatage des tableaux
- ✅ Marges optimales pour l'impression
- ✅ Métadonnées (titre, auteur, date)

---

## Vérification du PDF Généré

Après génération, vérifiez que le PDF contient :

- [ ] Page de titre avec métadonnées
- [ ] Table des matières complète (11 sections)
- [ ] Toutes les sections numérotées
- [ ] Tableaux correctement formatés
- [ ] Blocs de code avec coloration syntaxique
- [ ] Diagrammes ASCII préservés
- [ ] Annexes (A, B, C)
- [ ] Numéros de page

---

**Bon courage pour la conversion !** 📄➡️📕
