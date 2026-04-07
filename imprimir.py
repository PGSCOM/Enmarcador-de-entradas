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
PAGE_MARGIN_X = 20
PAGE_MARGIN_Y = 20
ITEM_SPACING = 10

def get_best_layout(page_w, page_h, orig_w, orig_h, spacing=10, margin_x=0, margin_y=0):
    """
    Finds the maximum number of items that fit on the page, packing them both in normal and rotated orientations.
    """
    usable_w = max(page_w - (margin_x * 2), 0)
    usable_h = max(page_h - (margin_y * 2), 0)
    
    def calculate_pack(uw, uh, bw, bh, is_rotated):
        nx = int((uw + spacing) // (bw + spacing)) if bw > 0 else 0
        ny = int((uh + spacing) // (bh + spacing)) if bh > 0 else 0
        count1 = nx * ny
        
        # Bottom leftover space
        used_h = ny * (bh + spacing) - spacing if ny > 0 else 0
        bottom_h_usable = max(0, uh - used_h - spacing)
        bottom_pack_nx = int((uw + spacing) // (bh + spacing)) if bh > 0 else 0
        bottom_pack_ny = int((bottom_h_usable + spacing) // (bw + spacing)) if bw > 0 else 0
        bottom_count = bottom_pack_nx * bottom_pack_ny
        
        # Right leftover space
        used_w = nx * (bw + spacing) - spacing if nx > 0 else 0
        right_w_usable = max(0, uw - used_w - spacing)
        right_pack_nx = int((right_w_usable + spacing) // (bh + spacing)) if bh > 0 else 0
        right_pack_ny = int((uh + spacing) // (bw + spacing)) if bw > 0 else 0
        right_count = right_pack_nx * right_pack_ny
        
        if bottom_count >= right_count:
            return count1 + bottom_count, {
                'main_nx': nx, 'main_ny': ny,
                'main_bw': bw, 'main_bh': bh,
                'main_rotated': is_rotated,
                'extra_nx': bottom_pack_nx, 'extra_ny': bottom_pack_ny,
                'extra_bw': bh, 'extra_bh': bw,
                'extra_rotated': not is_rotated,
                'extra_offset_x': 0,
                'extra_offset_y': ny * (bh + spacing) if ny > 0 else 0,
                'margin_x': margin_x, 'margin_y': margin_y, 'spacing': spacing,
                'count': count1 + bottom_count
            }
        else:
            return count1 + right_count, {
                'main_nx': nx, 'main_ny': ny,
                'main_bw': bw, 'main_bh': bh,
                'main_rotated': is_rotated,
                'extra_nx': right_pack_nx, 'extra_ny': right_pack_ny,
                'extra_bw': bh, 'extra_bh': bw,
                'extra_rotated': not is_rotated,
                'extra_offset_x': nx * (bw + spacing) if nx > 0 else 0,
                'extra_offset_y': 0,
                'margin_x': margin_x, 'margin_y': margin_y, 'spacing': spacing,
                'count': count1 + right_count
            }

    c1, pack1 = calculate_pack(usable_w, usable_h, orig_w, orig_h, False)
    c2, pack2 = calculate_pack(usable_w, usable_h, orig_h, orig_w, True)
    
    if c1 >= c2:
        return pack1
    else:
        return pack2

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
    
    print(f"Calculated layout: {layout['count']} items per page [Main: {layout['main_nx']}x{layout['main_ny']} (Rotated: {layout['main_rotated']}), Extra: {layout['extra_nx']}x{layout['extra_ny']} (Rotated: {layout['extra_rotated']})]")
    
    svg_files_created = []
    
    pages = [png_files[i:i + layout['count']] for i in range(0, len(png_files), layout['count'])]
    
    main_limit = layout['main_nx'] * layout['main_ny']

    for page_idx, page_files in enumerate(pages):
        svg_filename = os.path.join(dir_out, f"{page_idx}.svg")
        
        # We need relative paths to PNGs if possible, or absolute file:// URIs
        
        svg_content = [
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{page_w}px" height="{page_h}px" viewBox="0 0 {page_w} {page_h}">',
            f'  <rect width="100%" height="100%" fill="white"/>'
        ]
        
        for idx_on_page, png_path in enumerate(page_files):
            # Calculate position
            if idx_on_page < main_limit:
                col = idx_on_page % layout['main_nx']
                row = idx_on_page // layout['main_nx']
                
                x = layout['margin_x'] + col * (layout['main_bw'] + layout['spacing'])
                y = layout['margin_y'] + row * (layout['main_bh'] + layout['spacing'])
                is_rotated = layout['main_rotated']
                cell_w = layout['main_bw']
            else:
                extra_idx = idx_on_page - main_limit
                col = extra_idx % layout['extra_nx']
                row = extra_idx // layout['extra_nx']
                
                x = layout['margin_x'] + layout['extra_offset_x'] + col * (layout['extra_bw'] + layout['spacing'])
                y = layout['margin_y'] + layout['extra_offset_y'] + row * (layout['extra_bh'] + layout['spacing'])
                is_rotated = layout['extra_rotated']
                cell_w = layout['extra_bw']
            
            # Use absolute uri with forward slashes for SVG href
            abs_png_path = os.path.abspath(png_path).replace("\\", "/")
            href = f"file:///{abs_png_path}"
            
            if is_rotated:
                svg_content.append(
                    f'  <g transform="translate({x + cell_w}, {y}) rotate(90)">'
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
