from bs4 import BeautifulSoup
import requests
import csv

def ExtraeInfoMotos(csv_input_path, csv_output_path):
    ListaMotos = []

    # Leer el archivo CSV de entrada
    with open(csv_input_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            url = row['URL']
            tipo_moto = row['Tipo de Moto']
            print(f"Procesando URL: {url}")

            Mipag = requests.get(url)
            Pagina = BeautifulSoup(Mipag.text, "html.parser")

            datos = {
                "Marca": "",
                "Modelo": "",
                "Año": "",
                "Precio": "",
                "Tipo": tipo_moto,  # Asignar el tipo de moto desde el CSV
                "Cilindrada": "",
                "Potencia": "",
                "Torque": "",
                "Peso": "",
                "Consumo": "",
                "Imagen": "",
                "URL": url
            }

            # Obtener el modelo desde el título
            titulo = Pagina.find("h1")
            if titulo:
                datos["Modelo"] = titulo.get_text(strip=True)

            #Obtener precio
            precio_tag = Pagina.select_one(".ds_price h2")
            if precio_tag:
                datos["Precio"] = precio_tag.get_text(strip=True)
            else:
                datos["Precio"] = None

            # Obtener Potencia, Peso
            otros_datos = Pagina.select("ul.other_infos li")

            for li in otros_datos:
                texto = li.get_text(separator=" ", strip=True)
                if "Potencia" in texto:
                    datos["Potencia"] = li.find("span").get_text(strip=True)
                elif "Peso" in texto:
                    datos["Peso"] = li.find("span").get_text(strip=True)


            # Buscar todos los pares de etiqueta y valor
            for bloque in Pagina.select("div#details div.r"):
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
                elif clave == "Potencia":
                    datos["Potencia"] = valor_texto
                elif clave == "Par máximo declarado":
                    datos["Torque"] = valor_texto

            # Buscar consumo en toda la página
            for bloque in Pagina.find_all("div", class_="r"):
                etiqueta = bloque.select_one("div.rt")
                valor = bloque.select_one("div.rd")
                if etiqueta and "Consumo" in etiqueta.text:
                    datos["Consumo"] = valor.text.strip() 

            #Buscar imagen de la moto
            carousel = Pagina.find("div", class_="carousel-inner")
            if carousel:
                primera_imagen = carousel.find("div", class_="item")
                if primera_imagen and primera_imagen.has_attr("data-src"):
                    datos["Imagen"] = primera_imagen["data-src"]   

            ListaMotos.append(datos)

    # Guardar los datos en un archivo CSV de salida
    with open(csv_output_path, mode='w', encoding='utf-8', newline='') as file:
        fieldnames = ["Marca", "Modelo", "Año", "Precio", "Tipo", "Cilindrada", "Potencia", "Torque", "Peso", "Consumo", "Imagen", "URL"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ListaMotos)

    return ListaMotos

# Ejemplo de uso
csv_input_path = "c:\\Users\\jorge\\Desktop\\CrawlerBDMotos\\modelos.csv"
csv_output_path = "c:\\Users\\jorge\\Desktop\\CrawlerBDMotos\\motos_info.csv"
ExtraeInfoMotos(csv_input_path, csv_output_path)