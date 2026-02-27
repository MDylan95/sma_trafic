"""
Script de conversion Markdown → HTML stylisé
L'HTML peut ensuite être ouvert dans un navigateur et imprimé en PDF (Ctrl+P)
"""
import markdown2
import os

def convert_md_to_html():
    """Convertit le mémoire technique Markdown en HTML stylisé"""
    
    # Chemins des fichiers
    md_file = 'MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md'
    html_file = 'MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.html'
    
    print(f"📄 Lecture du fichier : {md_file}")
    
    # Lire le fichier Markdown
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé : {md_file}")
        return False
    
    print("🔄 Conversion Markdown → HTML...")
    
    # Convertir Markdown → HTML avec extensions
    html_body = markdown2.markdown(
        md_content,
        extras=[
            'tables',
            'fenced-code-blocks',
            'header-ids',
            'code-friendly',
            'break-on-newline',
            'toc'
        ]
    )
    
    # Template HTML complet avec styles CSS professionnels
    html_template = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mémoire Technique - Architecture SMA</title>
    <style>
        @media print {{
            @page {{
                size: A4;
                margin: 2cm;
            }}
            
            body {{
                font-size: 10pt;
            }}
            
            h1 {{
                page-break-before: always;
                font-size: 20pt;
            }}
            
            h1:first-of-type {{
                page-break-before: avoid;
            }}
            
            h2 {{
                page-break-after: avoid;
                font-size: 16pt;
            }}
            
            h3 {{
                page-break-after: avoid;
                font-size: 13pt;
            }}
            
            pre, table {{
                page-break-inside: avoid;
            }}
            
            .no-print {{
                display: none;
            }}
        }}
        
        @media screen {{
            body {{
                max-width: 900px;
                margin: 0 auto;
                padding: 40px 20px;
                background-color: #f5f5f5;
            }}
            
            .content {{
                background-color: white;
                padding: 40px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            
            .print-button {{
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 30px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                z-index: 1000;
            }}
            
            .print-button:hover {{
                background-color: #2980b9;
            }}
        }}
        
        /* Styles communs */
        body {{
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 4px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
            margin-bottom: 20px;
        }}
        
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 8px;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        h4 {{
            color: #95a5a6;
            margin-top: 15px;
            margin-bottom: 8px;
        }}
        
        p {{
            margin-bottom: 12px;
            text-align: justify;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #c7254e;
        }}
        
        pre {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 15px 0;
        }}
        
        pre code {{
            background-color: transparent;
            color: #ecf0f1;
            padding: 0;
            font-size: 0.85em;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            font-size: 0.95em;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
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
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        /* Style pour les diagrammes ASCII */
        pre.ascii-diagram {{
            background-color: #f8f8f8;
            color: #333;
            border: 1px solid #ddd;
            font-family: 'Courier New', monospace;
            font-size: 0.75em;
            line-height: 1.2;
        }}
    </style>
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">🖨️ Imprimer en PDF</button>
    
    <div class="content">
        {html_body}
    </div>
    
    <script>
        // Instructions pour l'utilisateur
        console.log("📄 Pour générer le PDF :");
        console.log("1. Cliquez sur le bouton 'Imprimer en PDF' en haut à droite");
        console.log("2. Ou appuyez sur Ctrl+P (Windows) / Cmd+P (Mac)");
        console.log("3. Sélectionnez 'Enregistrer au format PDF' comme imprimante");
        console.log("4. Cliquez sur 'Enregistrer'");
    </script>
</body>
</html>"""
    
    # Écrire le fichier HTML
    try:
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        print(f"✅ HTML généré avec succès : {html_file}")
        print(f"📊 Taille du fichier : {os.path.getsize(html_file) / 1024:.1f} KB")
        
        # Ouvrir automatiquement dans le navigateur
        import webbrowser
        abs_path = os.path.abspath(html_file)
        webbrowser.open('file://' + abs_path)
        
        print()
        print("🌐 Le fichier HTML a été ouvert dans votre navigateur.")
        print()
        print("📄 POUR GÉNÉRER LE PDF :")
        print("   1. Appuyez sur Ctrl+P (Windows) ou Cmd+P (Mac)")
        print("   2. Sélectionnez 'Enregistrer au format PDF' ou 'Microsoft Print to PDF'")
        print("   3. Cliquez sur 'Enregistrer'")
        print()
        print("💡 Ou cliquez sur le bouton bleu 'Imprimer en PDF' en haut à droite")
        
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la génération du HTML : {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("  CONVERSION MÉMOIRE TECHNIQUE → HTML (puis PDF via navigateur)")
    print("=" * 70)
    print()
    
    success = convert_md_to_html()
    
    if success:
        print()
        print("🎉 Conversion HTML terminée avec succès !")
        print("📄 Fichier : MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.html")
    else:
        print()
        print("⚠️  La conversion a échoué.")
