import os
import subprocess

# Ruta de la carpeta que contiene los archivos SVG
svg_folder = r"./img"


# Ruta de la carpeta donde se guardarán los archivos PNG
png_folder = r"./img/PNG"

# Comprobar si la carpeta existe, si no existe, crearla
if not os.path.exists(png_folder) and os.path.exists(svg_folder):
    os.makedirs(png_folder)

try:
    # Bucle para convertir cada archivo SVG en la carpeta
    for filename in os.listdir(svg_folder):
        if filename.endswith(".svg"):
            # Ruta completa del archivo SVG
            svg_file = os.path.join(svg_folder, filename)

            # Ruta completa del archivo PNG
            png_file = os.path.join(png_folder, filename[:-4] + ".png")

            # Comando para convertir el archivo SVG en PNG utilizando Inkscape
            command = f'"C:\\Program Files\\Inkscape\\bin\\inkscape" {svg_file} --export-type=png --export-filename={png_file} --export-width=1476 --export-height=478'

            # Ejecutar el comando en la línea de comandos
            subprocess.run(command, shell=True)

            print(f"Archivo {filename} convertido a PNG")

            # Decir progreso en porcentaje de cuantos quedan
            print(f"Progreso: {round((os.listdir(svg_folder).index(filename)) / len(os.listdir(svg_folder)) * 100, 2)}%")

except FileNotFoundError:
    print(f"No hay archivos SVG en la carpeta '{svg_folder}'. Primero ejecuta svg.py")