import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cargar el CSV existente
df = pd.read_csv("motos_procesado.csv")

# Crear sesión HTTP persistente
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

# Función robusta para extraer imagen
def obtener_imagen(url):
    try:
        response = session.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            carousel = soup.find("div", class_="carousel-inner")
            if carousel:
                primera_imagen = carousel.find("div", class_="item")
                if primera_imagen and "data-src" in primera_imagen.attrs:
                    return primera_imagen["data-src"]
    except Exception as e:
        print(f"❌ Error en {url}: {e}")
    return ""  # Devuelve cadena vacía si falla

# Ejecutar en paralelo (hasta 20 hilos)
urls = df["URL"].tolist()
imagenes = [None] * len(urls)

print("🚀 Iniciando scraping en paralelo...")
with ThreadPoolExecutor(max_workers=50) as executor:
    future_to_index = {executor.submit(obtener_imagen, url): i for i, url in enumerate(urls)}
    for future in as_completed(future_to_index):
        i = future_to_index[future]
        imagenes[i] = future.result()
        print(f"[{i+1}/{len(urls)}] Imagen obtenida")

# Agregar columna al DataFrame y guardar
df["Imagen"] = imagenes
df.to_csv("motos_con_imagenes.csv", index=False)
print("✅ CSV actualizado con enlaces de imagen guardado como 'motos_con_imagenes.csv'")
