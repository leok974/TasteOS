from app.core.text import clean_md

def test_clean_md_headers():
    assert clean_md("# Title") == "Title"
    assert clean_md("## Subtitle") == "Subtitle"
    assert clean_md("### Section") == "Section"
    assert clean_md("#   Spaced Title  ") == "Spaced Title"

def test_clean_md_bold():
    assert clean_md("**Bold** text") == "Bold text"
    assert clean_md("Text with **bold** word") == "Text with bold word"
    assert clean_md("__Mixed__ bold") == "Mixed bold"
    # Ensure it doesn't strip if not closed or weirdly formatted (regex dependent)
    # The current regex is r"(\*\*|__)(.*?)\1"
    assert clean_md("**Open") == "**Open" 

def test_clean_md_bullets():
    assert clean_md("- Item") == "Item"
    assert clean_md("* Item") == "Item"
    assert clean_md("  -  Indented") == "Indented"
    
def test_clean_md_mixed():
    assert clean_md("# **Title**") == "Title"
    assert clean_md("- **Bold Item**") == "Bold Item"

def test_clean_md_preservation():
    # Should not strip internal hyphens
    assert clean_md("use 1/2-inch cubes") == "use 1/2-inch cubes"
    # Should not strip bullets in middle of text (not leading)
    assert clean_md("Title: - subtitle") == "Title: - subtitle"
