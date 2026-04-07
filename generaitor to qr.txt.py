import json

with open("datos.json") as f:
    data = json.load(f)

# Ordenar las claves por el valor numérico (de menor a mayor)
sorted_keys = sorted(data.keys(), key=lambda k: int(data[k]))

output_file = "qr.txt"
with open(output_file, "w") as f:
    for key in sorted_keys:
        f.write(f"{key}\n")

print(f"Archivo '{output_file}' creado con {len(sorted_keys)} claves ordenadas por valor.")