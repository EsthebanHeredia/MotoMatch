# MotoMatch - Sistema de Recomendación de Motos

MotoMatch es una aplicación web para recomendar motos personalizadas a usuarios basadas en sus preferencias, interacciones sociales y patrones de navegación.

## Requisitos previos

1. Python 3.7 o superior
2. Pip (gestor de paquetes de Python)
3. Neo4j (base de datos de grafos)
4. Flask y dependencias (ver requirements.txt)

---

> **Nota para usuarios de macOS:**  
> Se recomienda utilizar [conda](https://docs.conda.io/en/latest/miniconda.html) para instalar las librerías y evitar problemas de compatibilidad, especialmente con dependencias científicas y de Neo4j.  
>  
> Ejemplo:
> ```sh
> conda create -n motomatch python=3.9
> conda activate motomatch
> pip install -r requirements.txt
> ```

---

## Instalación y configuración

### 1. Clonar el repositorio

```sh
git clone https://github.com/EsthebanHeredia/MotoMatch.git
cd MotoMatch
```

### 2. Instalar dependencias

```sh
pip install -r requirements.txt
```

### 3. Configurar la base de datos Neo4j

1. Instala Neo4j desde [https://neo4j.com/download/](https://neo4j.com/download/)
2. Instala los plugins **APOC** y **Graph Data Science Library** desde Neo4j Desktop o descargándolos desde [APOC Releases](https://github.com/neo4j/apoc/releases) y [GDS Releases](https://neo4j.com/download/graph-data-science/) y colócalos en la carpeta `plugins` de tu base de datos.
3. Copia el archivo `neo.conf` a la carpeta `conf` de tu base de datos de Neo4j.
4. Copia el archivo `motos_procesadas_final.csv` a la carpeta `import` de tu base de datos de Neo4j.
5. Inicia Neo4j y abre Neo4j Browser.
6. Ejecuta el contenido del archivo `cypher.txt` en el Neo4j Browser para cargar los datos.
7. Cambia la contraseña de tu base por "22446688"

### 4. Ejecutar la aplicación

```sh
python run_fixed_app.py
```

La aplicación estará disponible en [http://localhost:5000](http://localhost:5000).

---

## Estructura principal

- `app/`: Código principal de la aplicación (Flask, algoritmos, rutas)
- `static/`: Archivos estáticos (CSS, JS, imágenes)
- `templates/`: Plantillas HTML
- `requirements.txt`: Dependencias de Python

---

## Notas

- Si Neo4j no está disponible, la app puede funcionar con datos simulados (ver `app/config.py`).
- Para pruebas, consulta la sección de testing en el README original.

---