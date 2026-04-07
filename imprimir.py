import os
import glob
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import subprocess
from pypdf import PdfWriter

def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

# Configurable parameters
INPUT_DIR = './img/PNG'
OUTPUT_DIR = './img/imprimir'
OUTPUT_PDF = 'entradas_imprimir.pdf'
INKSCAPE_PATH = r'C:\Program Files\Inkscape\bin\inkscape.exe'
MAX_WORKERS = 16
PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508
PAGE_MARGIN_X = 0
PAGE_MARGIN_Y = 0
ITEM_SPACING = 0

def get_best_layout(page_w, page_h, orig_w, orig_h, spacing=10, margin_x=0, margin_y=0):
    """
    Finds the maximum number of items that fit on the page, considering both normal and rotated orientations.
    """
    w_m, h_m = orig_w + spacing, orig_h + spacing
    usable_w = max(page_w - (margin_x * 2), 0)
    usable_h = max(page_h - (margin_y * 2), 0)
    
    # Try Normal
    nx1 = int((usable_w + spacing) // w_m)
    ny1 = int((usable_h + spacing) // h_m)
    count1 = nx1 * ny1
    
    # Try Rotated
    nx2 = int((usable_w + spacing) // h_m)
    ny2 = int((usable_h + spacing) // w_m)
    count2 = nx2 * ny2
    
    if count1 >= count2:
        return {'rotated': False, 'nx': nx1, 'ny': ny1, 'count': count1, 'item_w': orig_w, 'item_h': orig_h, 'spacing': spacing, 'margin_x': margin_x, 'margin_y': margin_y}
    else:
        return {'rotated': True, 'nx': nx2, 'ny': ny2, 'count': count2, 'item_w': orig_h, 'item_h': orig_w, 'spacing': spacing, 'margin_x': margin_x, 'margin_y': margin_y}

def escape_xml(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&apos;")

def create_svg_pages(
    dir_in=INPUT_DIR,
    dir_out=OUTPUT_DIR,
    page_w=PAGE_WIDTH,
    page_h=PAGE_HEIGHT,
    spacing=ITEM_SPACING,
):
    ensure_dir(dir_out)
    
    png_files = sorted(glob.glob(os.path.join(dir_in, "*.png")), key=lambda x: int(os.path.splitext(os.path.basename(x))[0]) if os.path.splitext(os.path.basename(x))[0].isdigit() else 0)
    
    if not png_files:
        print(f"No PNG files found in {dir_in}")
        return []
    
    first_img = Image.open(png_files[0])
    orig_w, orig_h = first_img.size
    
    layout = get_best_layout(page_w, page_h, orig_w, orig_h, spacing=spacing, margin_x=PAGE_MARGIN_X, margin_y=PAGE_MARGIN_Y)
    
    if layout['count'] == 0:
        print("Error: The image is too large to fit in the specified page size.")
        return []
    
    print(f"Calculated layout: {layout['count']} items per page (Rotated: {layout['rotated']}) [Grid {layout['nx']}x{layout['ny']}]")
    
    svg_files_created = []
    
    pages = [png_files[i:i + layout['count']] for i in range(0, len(png_files), layout['count'])]
    
    for page_idx, page_files in enumerate(pages):
        svg_filename = os.path.join(dir_out, f"{page_idx}.svg")
        
        # We need relative paths to PNGs if possible, or absolute file:// URIs
        
        svg_content = [
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{page_w}px" height="{page_h}px" viewBox="0 0 {page_w} {page_h}">',
            f'  <rect width="100%" height="100%" fill="white"/>'
        ]
        
        for idx_on_page, png_path in enumerate(page_files):
            # Calculate position
            col = idx_on_page % layout['nx']
            row = idx_on_page // layout['nx']
            
            x = layout['margin_x'] + col * (layout['item_w'] + layout['spacing'])
            y = layout['margin_y'] + row * (layout['item_h'] + layout['spacing'])
            
            # Use absolute uri with forward slashes for SVG href
            abs_png_path = os.path.abspath(png_path).replace("\\", "/")
            href = f"file:///{abs_png_path}"
            
            if layout['rotated']:
                # The image is rotated 90 degrees.
                # In SVG, rotation is around the origin (0,0). We need to translate then rotate.
                # An image of WxH (native) becomes HxW when rotated 90deg.
                # So we translate to (x, y), rotate by 90deg, but since rotation moves the bounding box, 
                # a 90deg rotation around top-left means the image goes into -y.
                # Actually, translating to (x + H, y) and rotating by 90 puts it right.
                svg_content.append(
                    f'  <g transform="translate({x + layout["item_w"]}, {y}) rotate(90)">'
                )
                svg_content.append(
                    f'    <image x="0" y="0" width="{orig_w}" height="{orig_h}" xlink:href="{escape_xml(href)}"/>'
                )
                svg_content.append(
                    f'  </g>'
                )
            else:
                svg_content.append(
                    f'  <image x="{x}" y="{y}" width="{orig_w}" height="{orig_h}" xlink:href="{escape_xml(href)}"/>'
                )
        
        svg_content.append('</svg>')
        
        with open(svg_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(svg_content))
            
        svg_files_created.append(svg_filename)
        print(f"Created {svg_filename} with {len(page_files)} images.")
        
    return svg_files_created

def generate_pdf_from_svgs(svg_files, output_pdf="salida.pdf"):
    """
    Creates a single PDF file where each page is one of the generated SVGs.
    """
    if not svg_files:
        print("No SVG files to combine.")
        return
    print(f"Generating PDF '{output_pdf}' from {len(svg_files)} SVGs...")
    
    # We will use reportlab to combine the SVGs
    inkscape_path = INKSCAPE_PATH
    if not os.path.exists(inkscape_path):
        print(f"Error: Inkscape not found at {inkscape_path}. Please check the path.")
        return

    def convert_svg_to_pdf(svg_f):
        pdf_f = svg_f.replace('.svg', '.pdf')
        print(f"Converting {svg_f} to {pdf_f} via Inkscape...")

        try:
            result = subprocess.run(
                [
                    inkscape_path,
                    os.path.abspath(svg_f),
                    "--export-filename=" + os.path.abspath(pdf_f),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            if os.path.exists(pdf_f):
                return pdf_f, None

            stderr = result.stderr.strip() if result.stderr else ""
            return None, f"Inkscape finished without creating {pdf_f}. {stderr}"
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else ""
            stdout = exc.stdout.strip() if exc.stdout else ""
            return None, f"{svg_f}: {stderr or stdout or str(exc)}"
        except Exception as exc:
            return None, f"{svg_f}: {exc}"

    merger = PdfWriter()
    temp_pdfs = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_svg = {executor.submit(convert_svg_to_pdf, svg_f): svg_f for svg_f in svg_files}

        for future in as_completed(future_to_svg):
            pdf_f, error = future.result()
            if pdf_f:
                temp_pdfs.append(pdf_f)
            elif error:
                print(f"Failed to process SVG with Inkscape: {error}")

    temp_pdfs = sorted(
        temp_pdfs,
        key=lambda path: int(os.path.splitext(os.path.basename(path))[0]) if os.path.splitext(os.path.basename(path))[0].isdigit() else 0,
    )

    if temp_pdfs:
        print(f"Merging {len(temp_pdfs)} pages into {output_pdf}...")
        for pdf_page in temp_pdfs:
            merger.append(pdf_page)
            
        merger.write(output_pdf)
        merger.close()

        # Cleanup temporary PDFs
        for temp_pdf in temp_pdfs:
            try:
                os.remove(temp_pdf)
            except OSError:
                pass
                
        print(f"Successfully generated {output_pdf}")
    else:
        print("No pages were generated.")

if __name__ == "__main__":
    svgs = create_svg_pages()
    if svgs:
        generate_pdf_from_svgs(svgs, OUTPUT_PDF)
