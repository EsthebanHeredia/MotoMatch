import pandas as pd

# Cargar el archivo CSV principal
archivo_principal = "motos_info_final.csv"
df = pd.read_csv(archivo_principal)

# Función para limpiar los datos numéricos
def limpiar_numero(valor, caracteres_a_eliminar):
    if pd.isna(valor):  # Si el valor es NaN, devolverlo tal cual
        return "N.D."
    for caracter in caracteres_a_eliminar:
        valor = valor.replace(caracter, "")

    try:
        return int(valor.strip())  # Convertir a entero después de limpiar
    except ValueError:
        try:
            return float(valor.strip())  # Intentar convertir a float si no es entero
        except ValueError:
            return "N.D."

# Función para extraer el primer número del torque
def extraer_torque(valor):
    if pd.isna(valor):  # Si el valor es NaN, devolverlo tal cual
        return valor
    try:
        return valor.split()[0]  # Dividir por espacios y tomar el primer elemento
    except IndexError:
        return valor

# Limpiar las columnas específicas
df['Precio'] = df['Precio'].apply(lambda x: limpiar_numero(str(x), ['€', '.', ' ', '*', ',']))
df['Cilindrada'] = df['Cilindrada'].apply(lambda x: limpiar_numero(str(x), ['cc', ' ']))
df['Potencia'] = df['Potencia'].apply(lambda x: limpiar_numero(str(x), ['kW', ' ', 'cv']))
df['Torque'] = df['Torque'].apply(lambda x: extraer_torque(str(x)))  # Aplicar la función para el torque
df['Peso'] = df['Peso'].apply(lambda x: limpiar_numero(str(x), ['kg', ' ']))

# Eliminar la columna 'Consumo'
df = df.drop(columns=['Consumo'])

# Guardar el archivo procesado
archivo_salida = "motos_procesadas_final.csv"
df.to_csv(archivo_salida, index=False)

print(f"Archivo procesado guardado como {archivo_salida}")