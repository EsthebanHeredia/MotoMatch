from bs4 import BeautifulSoup
import requests
import csv

BASE_URL = "https://www.motofichas.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MotoScraper/1.0; +https://tusitio.com/bot)"
}

def ExtraeTipos():

    url = f"{BASE_URL}/marcas"
    TipoMoto = []

    Mipag = requests.get(url)
    Pagina = BeautifulSoup(Mipag.text, "html.parser")

    for tipo in Pagina.select(".brand_anchor"):
        a_tag = tipo.find("a")

        if a_tag:
            href = a_tag.get("href")
            TipoMoto.append(href)
            
    return TipoMoto

def ExtraeModelos(ListaTipo):

    Modelos = {}

    for tipo in ListaTipo:

        url = tipo
        tipomoto = url.split("/")[-1]  # Divide la cadena por "/" y toma el último elemento
        Mipag = requests.get(url)
        Pagina = BeautifulSoup(Mipag.text, "html.parser")

        for modelo in Pagina.select(".mw"):
            a_tag = modelo.find("a")

            if a_tag:
                href = a_tag.get("href")

                if "https://www.motofichas.com" in href: Modelos[href]= tipomoto
                else: Modelos["https://www.motofichas.com" + href]= tipomoto

    return Modelos

Modelos = ExtraeModelos(ExtraeTipos())

# Guardar los modelos en un archivo CSV
with open("modelos.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["URL", "Tipo de Moto"])  # Encabezado del archivo CSV
    for url, tipo_moto in Modelos.items():
        writer.writerow([url, tipo_moto])

print(f"Modelos de Motos guardados en modelos.csv: {len(Modelos)}")