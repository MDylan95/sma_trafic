"""
Script de conversion Markdown → PDF
Utilise markdown2 et weasyprint pour générer un PDF professionnel
"""
import os
import sys

def check_dependencies():
    """Vérifie que les dépendances sont installées"""
    try:
        import markdown2
        import weasyprint
        return True
    except ImportError as e:
        print(f"❌ Dépendance manquante : {e}")
        print("\n📦 Installation requise :")
        print("pip install markdown2 weasyprint")
        return False

def convert_md_to_pdf():
    """Convertit le mémoire technique Markdown en PDF"""
    
    if not check_dependencies():
        sys.exit(1)
    
    import markdown2
    from weasyprint import HTML, CSS
    
    # Chemins des fichiers
    md_file = 'MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md'
    pdf_file = 'MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.pdf'
    
    print(f"📄 Lecture du fichier : {md_file}")
    
    # Lire le fichier Markdown
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé : {md_file}")
        sys.exit(1)
    
    print("🔄 Conversion Markdown → HTML...")
    
    # Convertir Markdown → HTML avec extensions
    html_content = markdown2.markdown(
        md_content,
        extras=[
            'tables',
            'fenced-code-blocks',
            'header-ids',
            'code-friendly',
            'break-on-newline'
        ]
    )
    
    # Template HTML avec styles CSS professionnels
    html_template = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Mémoire Technique - Architecture SMA</title>
    <style>
        @page {{
            size: A4;
            margin: 2.5cm;
            @bottom-center {{
                content: "Page " counter(page) " / " counter(pages);
                font-size: 9pt;
                color: #666;
            }}
        }}
        
        body {{
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            font-size: 11pt;
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 4px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
            margin-bottom: 20px;
            page-break-after: avoid;
            font-size: 24pt;
        }}
        
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 8px;
            margin-top: 30px;
            margin-bottom: 15px;
            page-break-after: avoid;
            font-size: 18pt;
        }}
        
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
            margin-bottom: 10px;
            page-break-after: avoid;
            font-size: 14pt;
        }}
        
        h4 {{
            color: #95a5a6;
            margin-top: 15px;
            margin-bottom: 8px;
            font-size: 12pt;
        }}
        
        p {{
            margin-bottom: 10px;
            text-align: justify;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', 'Consolas', monospace;
            font-size: 10pt;
            color: #c7254e;
        }}
        
        pre {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            page-break-inside: avoid;
            font-family: 'Courier New', 'Consolas', monospace;
            font-size: 9pt;
            line-height: 1.4;
        }}
        
        pre code {{
            background-color: transparent;
            color: #ecf0f1;
            padding: 0;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            page-break-inside: avoid;
            font-size: 10pt;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        ul, ol {{
            margin-bottom: 15px;
            padding-left: 30px;
        }}
        
        li {{
            margin-bottom: 5px;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-left: 0;
            color: #555;
            font-style: italic;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }}
        
        /* Page de titre */
        .title-page {{
            text-align: center;
            padding-top: 100px;
            page-break-after: always;
        }}
        
        .title-page h1 {{
            font-size: 32pt;
            border: none;
            margin-bottom: 20px;
        }}
        
        .title-page h2 {{
            font-size: 20pt;
            border: none;
            color: #7f8c8d;
        }}
        
        .title-page h3 {{
            font-size: 16pt;
            color: #95a5a6;
        }}
        
        /* Éviter les coupures de page malheureuses */
        h1, h2, h3, h4, h5, h6 {{
            page-break-after: avoid;
        }}
        
        table, figure, img {{
            page-break-inside: avoid;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""
    
    print("📝 Génération du PDF...")
    
    # Convertir HTML → PDF avec WeasyPrint
    try:
        HTML(string=html_template).write_pdf(pdf_file)
        print(f"✅ PDF généré avec succès : {pdf_file}")
        print(f"📊 Taille du fichier : {os.path.getsize(pdf_file) / 1024:.1f} KB")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la génération du PDF : {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  CONVERSION MÉMOIRE TECHNIQUE → PDF")
    print("=" * 60)
    print()
    
    success = convert_md_to_pdf()
    
    if success:
        print()
        print("🎉 Conversion terminée avec succès !")
        print("📄 Fichier : MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.pdf")
    else:
        print()
        print("⚠️  La conversion a échoué.")
        print("💡 Essayez la méthode Pandoc (voir INSTRUCTIONS_CONVERSION_PDF.md)")
        sys.exit(1)
