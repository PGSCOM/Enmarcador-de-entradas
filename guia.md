# Guía para generar QRs:

1. Generar IDs de QRs con la app https://github.com/MaculaCSA/MaculaCSAGenerador
   1. Exportar la base de datos generaitor... y guardarla como datos.json en la raíz del proyecto
   2. Ejecutar generaitor to qr.txt.py 
2. Generar QRs en .png con https://github.com/MaculaCSA/Generador-de-QR o con otra herramienta (A partir del archivo qr.txt generado en el paso anterior)
3. Meter el archivo del diseño en https://github.com/MaculaCSA/Enmarcador-de-entradas en img/origen.svg
   * Importante que haya una imagen insertada que se llame 0.png que será el QR
4. Meter todos los QRs en la misma carpeta (0.png, 1.png, ...)
5. Ejecutar svg.py
6. Ejecutar png.py