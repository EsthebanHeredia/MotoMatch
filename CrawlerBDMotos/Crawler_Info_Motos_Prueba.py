from bs4 import BeautifulSoup
import requests

def extraer_datos_modelo(url_modelo):
    response = requests.get(url_modelo)
    soup = BeautifulSoup(response.text, "html.parser")
    
    datos = {
        "Marca": None, #YA
        "Modelo": None, #YA
        "Año": None, #YA
        "Precio": None, #YA
        "Tipo": None, #YA 
        "Cilindrada": None, #YA 
        "Potencia": None,
        "Torque": None,
        "Peso": None,
        "Consumo": None,
        "URL": url_modelo, #YA
        "Imagen": None #YA
    }

    # Obtener el modelo desde el título
    titulo = soup.find("h1")
    if titulo:
        datos["Modelo"] = titulo.get_text(strip=True)

    #Obtener precio
    precio_tag = soup.select_one(".ds_price h2")
    if precio_tag:
        datos["Precio"] = precio_tag.get_text(strip=True)
    else:
        datos["Precio"] = None

    # Obtener Potencia, Peso
    otros_datos = soup.select("ul.other_infos li")

    for li in otros_datos:
        texto = li.get_text(separator=" ", strip=True)
        if "Potencia" in texto:
            datos["Potencia"] = li.find("span").get_text(strip=True)
        elif "Peso" in texto:
            datos["Peso"] = li.find("span").get_text(strip=True)


    # Buscar todos los pares de etiqueta y valor
    for bloque in soup.select("div#details div.r"):
        etiqueta = bloque.select_one("div.rt")
        valor = bloque.select_one("div.rd")
        if not etiqueta or not valor:
            continue

        clave = etiqueta.text.strip().rstrip(":")
        valor_texto = valor.text.strip()

        if clave == "Marca":
            datos["Marca"] = valor_texto
        elif clave == "Año":
            datos["Año"] = valor_texto
        elif "Cilindrada" in clave:
            datos["Cilindrada"] = valor_texto
        elif clave == "Par máximo declarado":
            datos["Torque"] = valor_texto

    # Buscar consumo en toda la página
    for bloque in soup.find_all("div", class_="r"):
        etiqueta = bloque.select_one("div.rt")
        valor = bloque.select_one("div.rd")
        if etiqueta and "Consumo" in etiqueta.text:
            datos["Consumo"] = valor.text.strip()

    #Buscar imagen de la moto
    carousel = soup.find("div", class_="carousel-inner")
    if carousel:
        primera_imagen = carousel.find("div", class_="item")
        if primera_imagen and primera_imagen.has_attr("data-src"):
            datos["Imagen"] = primera_imagen["data-src"]



    return datos

DatosMoto = extraer_datos_modelo("https://www.motofichas.com/marcas/bmw/f-900-r-2020")

print(DatosMoto)