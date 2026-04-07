import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ruta de la carpeta que contiene los archivos SVG
svg_folder = r"./img"


# Ruta de la carpeta donde se guardarán los archivos PNG
png_folder = r"./img/PNG"

# Comprobar si la carpeta existe, si no existe, crearla
if not os.path.exists(png_folder) and os.path.exists(svg_folder):
    os.makedirs(png_folder)

try:
    svg_files = [filename for filename in os.listdir(svg_folder) if filename.endswith(".svg")]

    if not svg_files:
        print(f"No hay archivos SVG en la carpeta '{svg_folder}'. Primero ejecuta svg.py")
    else:
        total = len(svg_files)
        completados = 0
        lock = threading.Lock()

        def convertir_svg_a_png(filename):
            svg_file = os.path.join(svg_folder, filename)
            png_file = os.path.join(png_folder, filename[:-4] + ".png")

            command = [
                r"C:\Program Files\Inkscape\bin\inkscape",
                svg_file,
                "--export-type=png",
                f"--export-filename={png_file}",
                "--export-width=1476",
                "--export-height=478",
            ]

            subprocess.run(command, check=True)
            return filename

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(convertir_svg_a_png, filename) for filename in svg_files]

            for future in as_completed(futures):
                try:
                    filename = future.result()
                    with lock:
                        completados += 1
                        progreso = round((completados / total) * 100, 2)

                    print(f"Archivo {filename} convertido a PNG")
                    print(f"Progreso: {progreso}%")
                except subprocess.CalledProcessError as error:
                    print(f"Error al convertir un archivo SVG: {error}")

except FileNotFoundError:
    print(f"No hay archivos SVG en la carpeta '{svg_folder}'. Primero ejecuta svg.py")