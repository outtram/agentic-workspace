#!/usr/bin/env python3
"""
Document Polisher - Brand Style Application Tool

This script applies brand styling to DOCX documents using python-docx.
It reads the source document and creates a new styled version with the
selected brand's visual identity applied to all text and headings.

Usage:
    python apply_brand.py <input.docx> <brand_name> <output.docx>

Example:
    python apply_brand.py report.docx mckinsey polished_report.docx

Brands available:
    economist, mckinsey, deloitte, kpmg, stripe, apple, ibm, notion, linear, figma
"""

import json
import sys
import os
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("Error: python-docx is required. Install with: pip install python-docx")
    sys.exit(1)


def hex_to_rgb(hex_color: str) -> RGBColor:
    """Convert hex color (#RRGGBB) to RGBColor."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return RGBColor(r, g, b)


def set_font_name(run, font_name: str):
    """Set font name properly including the XML element for full compatibility."""
    run.font.name = font_name
    # Set the eastAsia and other font attributes via XML for proper rendering
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:cs'), font_name)


def set_style_font(style, font_name: str):
    """Set font name on a style element."""
    style.font.name = font_name
    # Access the underlying XML to set all font attributes
    element = style.element
    rPr = element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:cs'), font_name)


def load_brand_config(brand_name: str) -> dict:
    """Load brand configuration from the brand-mapping.json file."""
    script_dir = Path(__file__).parent.parent
    config_path = script_dir / 'templates' / 'brand-mapping.json'

    with open(config_path, 'r') as f:
        config = json.load(f)

    if brand_name not in config['brands']:
        available = ', '.join(config['brands'].keys())
        raise ValueError(f"Brand '{brand_name}' not found. Available: {available}")

    return config['brands'][brand_name]


def add_page_break(doc):
    """Add a page break to the document."""
    doc.add_page_break()


def apply_brand_to_docx(input_path: str, brand_name: str, output_path: str):
    """Apply brand styling to a DOCX file by recreating it with proper styles."""
    brand = load_brand_config(brand_name)

    # Load the source document
    source_doc = Document(input_path)

    # Create a new document
    doc = Document()

    # Extract brand settings
    heading_font = brand['typography']['headingFont']
    body_font = brand['typography']['bodyFont']

    h1_style = brand['styles']['h1']
    h2_style = brand['styles']['h2']
    h3_style = brand['styles']['h3']
    body_style = brand['styles']['body']

    primary_color = hex_to_rgb(brand['colors']['primary'])
    text_color = hex_to_rgb(brand['colors']['textPrimary'])
    secondary_color = hex_to_rgb(brand['colors']['textSecondary'])
    accent_color = hex_to_rgb(brand['colors']['accent'])

    # Apply styles to the new document
    styles = doc.styles

    # Normal style
    normal = styles['Normal']
    set_style_font(normal, body_font)
    normal.font.size = Pt(body_style['size'])
    normal.font.color.rgb = text_color
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(10)
    normal.paragraph_format.line_spacing = 1.15

    # Title style
    title_style = styles['Title']
    set_style_font(title_style, heading_font)
    title_style.font.size = Pt(h1_style['size'] + 8)
    title_style.font.bold = h1_style.get('bold', True)
    title_style.font.color.rgb = primary_color
    title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Heading 1 - chapter headings
    h1 = styles['Heading 1']
    set_style_font(h1, heading_font)
    h1.font.size = Pt(h1_style['size'])
    h1.font.bold = h1_style.get('bold', True)
    h1.font.color.rgb = hex_to_rgb(h1_style['color'])
    h1.paragraph_format.space_before = Pt(0)
    h1.paragraph_format.space_after = Pt(18)
    h1.paragraph_format.line_spacing = 1.0

    # Heading 2 - section headings
    h2 = styles['Heading 2']
    set_style_font(h2, heading_font)
    h2.font.size = Pt(h2_style['size'])
    h2.font.bold = h2_style.get('bold', True)
    h2.font.color.rgb = hex_to_rgb(h2_style['color'])
    h2.paragraph_format.space_before = Pt(18)
    h2.paragraph_format.space_after = Pt(8)
    h2.paragraph_format.line_spacing = 1.0

    # Heading 3 - sub-section headings
    h3 = styles['Heading 3']
    set_style_font(h3, heading_font)
    h3.font.size = Pt(h3_style['size'])
    h3.font.bold = h3_style.get('bold', True)
    h3.font.color.rgb = hex_to_rgb(h3_style['color'])
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(6)
    h3.paragraph_format.line_spacing = 1.0

    # List styles
    try:
        list_bullet = styles['List Bullet']
        set_style_font(list_bullet, body_font)
        list_bullet.font.size = Pt(body_style['size'])
        list_bullet.font.color.rgb = text_color
        list_bullet.paragraph_format.space_before = Pt(2)
        list_bullet.paragraph_format.space_after = Pt(2)
    except:
        pass

    try:
        list_number = styles['List Number']
        set_style_font(list_number, body_font)
        list_number.font.size = Pt(body_style['size'])
        list_number.font.color.rgb = text_color
        list_number.paragraph_format.space_before = Pt(2)
        list_number.paragraph_format.space_after = Pt(2)
    except:
        pass

    # Set margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)

    # Copy content from source to new document with styling
    for para in source_doc.paragraphs:
        style_name = para.style.name if para.style else 'Normal'
        para_text = para.text.strip()

        # Handle Heading 1 (chapters) - ALWAYS add page break before
        if style_name.startswith('Heading 1') or style_name == 'Heading 1':
            doc.add_page_break()
            new_para = doc.add_heading(para_text, level=1)

        elif style_name.startswith('Heading 2') or style_name == 'Heading 2':
            new_para = doc.add_heading(para_text, level=2)

        elif style_name.startswith('Heading 3') or style_name == 'Heading 3':
            new_para = doc.add_heading(para_text, level=3)

        elif style_name == 'Title':
            # Title centered on page
            new_para = doc.add_paragraph()
            new_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            new_para.paragraph_format.space_before = Pt(200)
            new_para.paragraph_format.space_after = Pt(24)
            for run in para.runs:
                new_run = new_para.add_run(run.text)
                set_font_name(new_run, heading_font)
                new_run.font.size = Pt(h1_style['size'] + 14)
                new_run.font.bold = True
                new_run.font.color.rgb = primary_color

        elif 'List Bullet' in style_name or style_name == 'List Bullet':
            new_para = doc.add_paragraph(style='List Bullet')
            new_para.paragraph_format.space_before = Pt(2)
            new_para.paragraph_format.space_after = Pt(2)
            for run in para.runs:
                new_run = new_para.add_run(run.text)
                set_font_name(new_run, body_font)
                new_run.font.size = Pt(body_style['size'])
                new_run.font.color.rgb = text_color
                if run.bold:
                    new_run.bold = True
                if run.italic:
                    new_run.italic = True

        elif 'List Number' in style_name or style_name == 'List Number':
            new_para = doc.add_paragraph(style='List Number')
            new_para.paragraph_format.space_before = Pt(2)
            new_para.paragraph_format.space_after = Pt(2)
            for run in para.runs:
                new_run = new_para.add_run(run.text)
                set_font_name(new_run, body_font)
                new_run.font.size = Pt(body_style['size'])
                new_run.font.color.rgb = text_color
                if run.bold:
                    new_run.bold = True
                if run.italic:
                    new_run.italic = True

        else:
            # Regular paragraph
            new_para = doc.add_paragraph()

            # Preserve alignment
            if para.alignment:
                new_para.alignment = para.alignment

            new_para.paragraph_format.space_before = Pt(0)
            new_para.paragraph_format.space_after = Pt(10)

            # Copy runs with formatting
            for run in para.runs:
                new_run = new_para.add_run(run.text)
                set_font_name(new_run, body_font)
                new_run.font.size = Pt(body_style['size'])
                new_run.font.color.rgb = text_color

                if run.bold:
                    new_run.bold = True
                if run.italic:
                    new_run.italic = True
                if run.underline:
                    new_run.underline = True

    # Copy tables if any
    for table in source_doc.tables:
        rows = len(table.rows)
        cols = len(table.columns)

        new_table = doc.add_table(rows=rows, cols=cols)
        new_table.style = 'Table Grid'

        for i, row in enumerate(table.rows):
            for j, cell in enumerate(row.cells):
                new_cell = new_table.rows[i].cells[j]
                for para in cell.paragraphs:
                    if new_cell.paragraphs:
                        new_para = new_cell.paragraphs[0]
                        new_para.clear()
                    else:
                        new_para = new_cell.add_paragraph()

                    for run in para.runs:
                        new_run = new_para.add_run(run.text)
                        set_font_name(new_run, body_font)
                        new_run.font.size = Pt(body_style['size'])
                        new_run.font.color.rgb = text_color
                        if run.bold:
                            new_run.bold = True

    # Save the new document
    doc.save(output_path)
    print(f"Successfully applied '{brand['name']}' branding to: {output_path}")


def list_brands():
    """List all available brands with descriptions."""
    script_dir = Path(__file__).parent.parent
    config_path = script_dir / 'templates' / 'brand-mapping.json'

    with open(config_path, 'r') as f:
        config = json.load(f)

    print("\n" + "=" * 70)
    print("DOCUMENT POLISHER - Available Brand Styles")
    print("=" * 70 + "\n")

    for brand_id, brand in config['brands'].items():
        print(f"  {brand_id:12} | {brand['name']}")
        print(f"  {' ':12} | {brand['description']}")
        print(f"  {' ':12} | Category: {brand['category']}")
        print(f"  {' ':12} | Primary: {brand['colors']['primary']}, Accent: {brand['colors']['accent']}")
        print()

    print("-" * 70)
    print("Usage: python apply_brand.py <input.docx> <brand_name> <output.docx>")
    print("-" * 70 + "\n")


def main():
    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help', 'list', '--list']:
        list_brands()
        return

    if len(sys.argv) != 4:
        print("Usage: python apply_brand.py <input.docx> <brand_name> <output.docx>")
        print("       python apply_brand.py --list  # Show available brands")
        sys.exit(1)

    input_path = sys.argv[1]
    brand_name = sys.argv[2].lower()
    output_path = sys.argv[3]

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    try:
        apply_brand_to_docx(input_path, brand_name, output_path)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing document: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
