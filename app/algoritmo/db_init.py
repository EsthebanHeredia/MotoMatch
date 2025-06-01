"""
Script de inicialización para la base de datos Neo4j de MotoMatch.
Este script crea las estructuras iniciales necesarias y carga datos de ejemplo.
"""
from neo4j import GraphDatabase
import logging
import argparse
import os
import sys
import random
import pandas as pd

from app.algoritmo.label_propagation import MotoLabelPropagation
from app.algoritmo.moto_ideal import MotoIdealRecommender
from app.algoritmo.pagerank import MotoPageRank

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración por defecto
DEFAULT_URI = "bolt://localhost:7687"
DEFAULT_USER = "neo4j"
DEFAULT_PASSWORD = "password"

class Neo4jInitializer:
    def __init__(self, uri, user, password, use_mock_data=False):
        """
        Inicializa el conector a Neo4j o con datos simulados.
        
        Args:
            uri (str): URI de la base de datos Neo4j
            user (str): Nombre de usuario
            password (str): Contraseña
            use_mock_data (bool): Si es True, utiliza datos simulados en lugar de conectar a Neo4j
        """
        self.use_mock_data = use_mock_data
        
        # Inicialización de atributos
        self.db_connected = False
        self.neo4j_driver = None
        
        # Inicialización de recomendadores
        self.pagerank = MotoPageRank()
        self.label_propagation = MotoLabelPropagation()
        self.recommender = MotoIdealRecommender()
        
        # Inicialización de datos
        self.users = None
        self.motos = None
        self.ratings = None
        self.friendships = None
        
        # Intentar conectar a Neo4j si no estamos usando datos simulados
        if not use_mock_data:
            self.connect_to_neo4j()
        
    def connect_to_neo4j(self):
        """Establece la conexión con la base de datos Neo4j"""
        try:
            # CORRECCIÓN: Usar el URI, usuario y contraseña pasados al constructor
            # en lugar de las constantes DEFAULT_*
            uri = getattr(self, 'uri', DEFAULT_URI)
            user = getattr(self, 'user', DEFAULT_USER)
            password = getattr(self, 'password', DEFAULT_PASSWORD)
            
            self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
            
            # Verificar que la conexión funciona
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
                
            self.db_connected = True
            logger.info(f"Conectado a Neo4j correctamente (URI: {uri}, usuario: {user})")
        except Exception as e:
            logger.error(f"Error al conectar a Neo4j: {str(e)}")
            self.db_connected = False
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.db_connected and self.neo4j_driver:
            self.neo4j_driver.close()
            logger.info("Conexión a Neo4j cerrada")
        
    def clear_database(self):
        """Limpia todos los datos existentes en la base de datos"""
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se puede limpiar.")
            return
        
        with self.neo4j_driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Base de datos limpiada correctamente")
            
    def create_constraints(self):
        """Crea restricciones e índices para mejorar el rendimiento"""
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden crear restricciones.")
            return
        
        with self.neo4j_driver.session() as session:
            # Crear restricciones de unicidad para nodos principales
            try:
                session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
                session.run("CREATE CONSTRAINT moto_id IF NOT EXISTS FOR (m:Moto) REQUIRE m.id IS UNIQUE")
                session.run("CREATE CONSTRAINT marca_nombre IF NOT EXISTS FOR (m:Marca) REQUIRE m.nombre IS UNIQUE")
                session.run("CREATE CONSTRAINT estilo_nombre IF NOT EXISTS FOR (e:Estilo) REQUIRE e.nombre IS UNIQUE")
                logger.info("Restricciones creadas correctamente")
            except Exception as e:
                # Para versiones antiguas de Neo4j
                logger.warning(f"Error al crear restricciones modernas, intentando sintaxis antigua: {str(e)}")
                try:
                    session.run("CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE")
                    session.run("CREATE CONSTRAINT ON (m:Moto) ASSERT m.id IS UNIQUE")
                    session.run("CREATE CONSTRAINT ON (m:Marca) ASSERT m.nombre IS UNIQUE")
                    session.run("CREATE CONSTRAINT ON (e:Estilo) ASSERT e.nombre IS UNIQUE")
                    logger.info("Restricciones creadas correctamente (sintaxis antigua)")
                except Exception as e2:
                    logger.error(f"Error al crear restricciones: {str(e2)}")
    
    def create_users(self):
        """Crea usuarios de ejemplo"""
        if self.use_mock_data:
            logger.info("Usando datos simulados para usuarios")
            self.users = [
                {"id": "admin", "experiencia": "Intermedio", "uso_previsto": "Paseo", "presupuesto": 80000, "edad": 35},
                {"id": "maria", "experiencia": "Principiante", "uso_previsto": "Ciudad", "presupuesto": 50000, "edad": 28},
                {"id": "pedro", "experiencia": "Avanzado", "uso_previsto": "Deportivo", "presupuesto": 120000, "edad": 42},
                {"id": "lucia", "experiencia": "Intermedio", "uso_previsto": "Viajes", "presupuesto": 90000, "edad": 31},
                {"id": "jose", "experiencia": "Avanzado", "uso_previsto": "Mixto", "presupuesto": 100000, "edad": 38}
            ]
            logger.info(f"Datos de usuarios simulados: {self.users}")
            return  # No crear en la base de datos
        
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden crear usuarios.")
            return
        
        with self.neo4j_driver.session() as session:
            # Crear nodos de usuarios
            for user in self.users:
                session.run("""
                    MERGE (u:User {id: $id})
                    SET u.experiencia = $experiencia,
                        u.uso_previsto = $uso_previsto,
                        u.presupuesto = $presupuesto,
                        u.edad = $edad
                """, **user)
                
            logger.info(f"Creados {len(self.users)} usuarios de ejemplo")
    
    def create_motos(self):
        """Crea motos de ejemplo"""
        if self.use_mock_data:
            logger.info("Usando datos simulados para motos")
            self.motos = [
                {"id": "moto1", "potencia": 190, "peso": 200, "cilindrada": 1000, "tipo": "Deportiva", "precio": 92000, 
                 "marca": "Kawasaki", "modelo": "Ninja ZX-10R", 
                 "imagen": "https://www.motofichas.com/images/phocagallery/Kawasaki/ninja-zx-10r-2021/01-kawasaki-ninja-zx-10r-2024-performance-estudio-verde.jpg"},
                {"id": "moto2", "potencia": 120, "peso": 170, "cilindrada": 600, "tipo": "Deportiva", "precio": 75000, 
                 "marca": "Honda", "modelo": "CBR 600RR", 
                 "imagen": "https://img.remediosdigitales.com/2fe8cb/honda-cbr600rr-2021-5-/1366_2000.jpeg"},
                {"id": "moto3", "potencia": 43, "peso": 160, "cilindrada": 390, "tipo": "Naked", "precio": 46000, 
                 "marca": "KTM", "modelo": "Duke 390", 
                 "imagen": "https://www.ktm.com/ktmgroup-storage/PHO_BIKE_90_RE_390-Duke-orange-MY22-Front-Right-49599.png"},
                {"id": "moto4", "potencia": 70, "peso": 220, "cilindrada": 650, "tipo": "Adventure", "precio": 68000, 
                 "marca": "Suzuki", "modelo": "V-Strom 650", 
                 "imagen": "https://suzukicycles.com/content/dam/public/SuzukiCycles/Models/Bikes/Adventure/2023/DL650XAM3_YU1_RIGHT.png"},
                {"id": "moto5", "potencia": 110, "peso": 220, "cilindrada": 1170, "tipo": "Clásica", "precio": 115000, 
                 "marca": "BMW", "modelo": "R nineT", 
                 "imagen": "https://cdp.azureedge.net/products/USA/BM/2023/MC/STANDARD/R_NINE_T/50/BLACKSTORM_METALLIC-BRUSHED_ALUMINUM/2000000001.jpg"},
                {"id": "moto6", "potencia": 42, "peso": 170, "cilindrada": 310, "tipo": "Deportiva", "precio": 48000, 
                 "marca": "Yamaha", "modelo": "R3", 
                 "imagen": "https://yamaha-motor.com.ar/uploads/product_images/R3.png"},
                {"id": "moto7", "potencia": 111, "peso": 190, "cilindrada": 937, "tipo": "Naked", "precio": 89000, 
                 "marca": "Ducati", "modelo": "Monster", 
                 "imagen": "https://www.motofichas.com/images/phocagallery/Ducati/monster-2021/01-ducati-monster-2021-estudio-rojo.jpg"},
                {"id": "moto8", "potencia": 150, "peso": 190, "cilindrada": 750, "tipo": "Deportiva", "precio": 80000, 
                 "marca": "Suzuki", "modelo": "GSX-R750", 
                 "imagen": "https://www.suzuki.es/content/dam/suzukiauto-es/global/motos/sportbikes/GSX-R-series/GSX-R-750/GSX-R750M3/03_GSX-R750M3_Metallic-Matte-Stellar-Blue.jpg"},
                {"id": "moto9", "potencia": 116, "peso": 210, "cilindrada": 900, "tipo": "Naked", "precio": 82000, 
                 "marca": "Kawasaki", "modelo": "Z900", 
                 "imagen": "https://www.motofichas.com/images/phocagallery/Kawasaki/z900-2023/01-kawasaki-z900-2023-estudio-verde.jpg"},
                {"id": "moto10", "potencia": 123, "peso": 208, "cilindrada": 765, "tipo": "Naked", "precio": 85000, 
                 "marca": "Triumph", "modelo": "Street Triple", 
                 "imagen": "https://www.motofichas.com/images/phocagallery/Triumph/street-triple-765-rs-2023/01-triumph-street-triple-765-rs-2023-estudio-gris.jpg"},
                {"id": "moto11", "potencia": 80, "peso": 225, "cilindrada": 850, "tipo": "Adventure", "precio": 76000, 
                 "marca": "BMW", "modelo": "F 850 GS", 
                 "imagen": "https://www.motofichas.com/images/phocagallery/BMW_Motorrad/f-850-gs-2018/01-bmw-f-850-gs-2021-estudio-amarillo.jpg"},
                {"id": "moto12", "potencia": 31, "peso": 150, "cilindrada": 125, "tipo": "Scooter", "precio": 28000, 
                 "marca": "Honda", "modelo": "PCX 125", 
                 "imagen": "https://www.motofichas.com/images/phocagallery/Honda/pcx-125-2021/01-honda-pcx-125-2021-estudio-rojo.jpg"}
            ]
            logger.info(f"Datos de motos simulados: {self.motos}")
            return  # No crear en la base de datos
        
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden crear motos.")
            return
        
        with self.neo4j_driver.session() as session:
            # Crear nodos de motos y relaciones con marcas y estilos
            for moto in self.motos:
                # Crear nodo de moto
                session.run("""
                    MERGE (m:Moto {id: $id})
                    SET m.potencia = $potencia,
                        m.peso = $peso,
                        m.cilindrada = $cilindrada,
                        m.tipo = $tipo,
                        m.precio = $precio,
                        m.marca = $marca,
                        m.modelo = $modelo,
                        m.imagen = $imagen
                """, **moto)
                
                # Crear nodo de marca y relación
                session.run("""
                    MERGE (m:Moto {id: $id})
                    MERGE (ma:Marca {nombre: $marca})
                    MERGE (m)-[:DE_MARCA]->(ma)
                """, id=moto["id"], marca=moto["marca"])
                
                # Crear nodo de estilo y relación
                session.run("""
                    MERGE (m:Moto {id: $id})
                    MERGE (e:Estilo {nombre: $tipo})
                    MERGE (m)-[:DE_ESTILO]->(e)
                """, id=moto["id"], tipo=moto["tipo"])
                
            logger.info(f"Creadas {len(self.motos)} motos de ejemplo")
    
    def create_friendships(self):
        """Crea relaciones de amistad entre usuarios"""
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden crear amistades.")
            return
        
        with self.neo4j_driver.session() as session:
            # Datos de ejemplo para amistades
            friendships = [
                ("admin", "maria"),
                ("admin", "pedro"),
                ("maria", "lucia"),
                ("pedro", "jose"),
                ("lucia", "jose"),
                ("admin", "jose")
            ]
            
            # Crear relaciones de amistad bidireccionales
            for user1, user2 in friendships:
                session.run("""
                    MATCH (u1:User {id: $user1}), (u2:User {id: $user2})
                    MERGE (u1)-[:FRIEND]->(u2)
                    MERGE (u2)-[:FRIEND]->(u1)
                """, user1=user1, user2=user2)
                
            logger.info(f"Creadas {len(friendships)} amistades bidireccionales")
    
    def create_ratings(self):
        """Crea valoraciones de usuarios para motos"""
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden crear valoraciones.")
            return
        
        with self.neo4j_driver.session() as session:
            # Obtener IDs de usuarios y motos
            result_users = session.run("MATCH (u:User) RETURN u.id AS user_id")
            result_motos = session.run("MATCH (m:Moto) RETURN m.id AS moto_id")
            
            users = [record["user_id"] for record in result_users]
            motos = [record["moto_id"] for record in result_motos]
            
            # Crear valoraciones aleatorias pero con cierta lógica para cada usuario
            ratings = []
            
            user_preferences = {
                "admin": ["moto1", "moto8", "moto5"],  # Deportivas y clásicas
                "maria": ["moto6", "moto3", "moto12"],  # Pequeñas y económicas
                "pedro": ["moto7", "moto1", "moto10"],  # Potentes y deportivas
                "lucia": ["moto4", "moto11", "moto9"],  # Adventure y naked
                "jose": ["moto10", "moto7", "moto5"]    # Naked y clásicas
            }
            
            for user_id, preferred_motos in user_preferences.items():
                # Valoraciones altas para las motos preferidas
                for moto_id in preferred_motos:
                    rating = round(random.uniform(4.0, 5.0), 1)  # Entre 4.0 y 5.0
                    ratings.append((user_id, moto_id, rating))
                
                # Algunas valoraciones medias para otras motos
                other_motos = [m for m in motos if m not in preferred_motos]
                sample_size = min(4, len(other_motos))
                for moto_id in random.sample(other_motos, sample_size):
                    rating = round(random.uniform(2.0, 3.9), 1)  # Entre 2.0 y 3.9
                    ratings.append((user_id, moto_id, rating))
            
            # Crear las relaciones de valoración
            for user_id, moto_id, rating in ratings:
                session.run("""
                    MATCH (u:User {id: $user_id}), (m:Moto {id: $moto_id})
                    MERGE (u)-[r:RATED]->(m)
                    SET r.rating = $rating,
                        r.timestamp = timestamp()
                """, user_id=user_id, moto_id=moto_id, rating=rating)
                
            logger.info(f"Creadas {len(ratings)} valoraciones de usuarios")
    
    def create_interactions(self):
        """Crea interacciones entre usuarios y motos (vistas, likes, etc.)"""
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden crear interacciones.")
            return
        
        with self.neo4j_driver.session() as session:
            # Obtener IDs de usuarios y motos
            result_users = session.run("MATCH (u:User) RETURN u.id AS user_id")
            result_motos = session.run("MATCH (m:Moto) RETURN m.id AS moto_id")
            
            users = [record["user_id"] for record in result_users]
            motos = [record["moto_id"] for record in result_motos]
            
            # Tipos de interacción con sus pesos
            interaction_types = {
                "view": 1.0,       # Ver detalles
                "like": 3.0,       # Dar like
                "bookmark": 2.0,   # Guardar en favoritos
                "compare": 1.5     # Comparar con otras
            }
            
            # Crear interacciones aleatorias
            interactions = []
            
            for user_id in users:
                # Más interacciones para el usuario admin
                num_interactions = 15 if user_id == "admin" else 10
                
                # Seleccionar motos aleatorias
                for _ in range(num_interactions):
                    moto_id = random.choice(motos)
                    interaction_type = random.choice(list(interaction_types.keys()))
                    weight = interaction_types[interaction_type]
                    
                    interactions.append((user_id, moto_id, interaction_type, weight))
            
            # Crear las relaciones de interacción
            for user_id, moto_id, interaction_type, weight in interactions:
                session.run("""
                    MATCH (u:User {id: $user_id}), (m:Moto {id: $moto_id})
                    MERGE (u)-[i:INTERACTED]->(m)
                    SET i.type = $type,
                        i.weight = $weight,
                        i.timestamp = timestamp()
                """, user_id=user_id, moto_id=moto_id, type=interaction_type, weight=weight)
                
            logger.info(f"Creadas {len(interactions)} interacciones")
    
    def create_user_preferences(self):
        """Crea preferencias de usuario para estilos y marcas"""
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden crear preferencias de usuario.")
            return
        
        with self.neo4j_driver.session() as session:
            # Preferencias por usuario
            user_preferences = {
                "admin": {
                    "estilos": {"Deportiva": 0.8, "Clásica": 0.6, "Naked": 0.4},
                    "marcas": {"Kawasaki": 0.9, "Suzuki": 0.7, "BMW": 0.5}
                },
                "maria": {
                    "estilos": {"Deportiva": 0.5, "Scooter": 0.8, "Naked": 0.3},
                    "marcas": {"Yamaha": 0.8, "Honda": 0.7, "KTM": 0.6}
                },
                "pedro": {
                    "estilos": {"Deportiva": 0.9, "Naked": 0.7, "Adventure": 0.3},
                    "marcas": {"Ducati": 0.9, "Kawasaki": 0.8, "Triumph": 0.7}
                },
                "lucia": {
                    "estilos": {"Adventure": 0.9, "Naked": 0.5, "Clásica": 0.4},
                    "marcas": {"BMW": 0.8, "Suzuki": 0.6, "Yamaha": 0.4}
                },
                "jose": {
                    "estilos": {"Naked": 0.8, "Clásica": 0.7, "Deportiva": 0.5},
                    "marcas": {"Triumph": 0.9, "Ducati": 0.8, "BMW": 0.6}
                }
            }
            
            # Crear preferencias
            for user_id, preferences in user_preferences.items():
                # Preferencias de estilos
                for estilo, valor in preferences["estilos"].items():
                    session.run("""
                        MATCH (u:User {id: $user_id})
                        MERGE (e:Estilo {nombre: $estilo})
                        MERGE (u)-[p:PREFIERE]->(e)
                        SET p.valor = $valor
                    """, user_id=user_id, estilo=estilo, valor=valor)
                
                # Preferencias de marcas
                for marca, valor in preferences["marcas"].items():
                    session.run("""
                        MATCH (u:User {id: $user_id})
                        MERGE (m:Marca {nombre: $marca})
                        MERGE (u)-[p:PREFIERE]->(m)
                        SET p.valor = $valor
                    """, user_id=user_id, marca=marca, valor=valor)
            
            logger.info("Creadas preferencias de usuarios para estilos y marcas")
    
    def initialize_database(self, clear=False):
        """
        Inicializa la base de datos con estructuras y datos de ejemplo.
        
        Args:
            clear (bool): Si es True, limpia la base de datos antes de inicializarla
        """
        if clear:
            self.clear_database()
        
        self.create_constraints()
        self.create_users()
        self.create_motos()
        self.create_friendships()
        self.create_ratings()
        self.create_interactions()
        self.create_user_preferences()
        
        logger.info("Inicialización de la base de datos completada")
    
    def import_motos_from_csv(self, csv_path):
        """Importa motos desde un archivo CSV y las crea en Neo4j"""
        if not self.db_connected:
            logger.warning("No hay conexión a la base de datos. No se pueden importar motos.")
            return
        
        try:
            # Leer el archivo CSV
            df = pd.read_csv(csv_path)
            logger.info(f"CSV leído: {len(df)} motos encontradas")
            
            # Procesar cada moto
            with self.neo4j_driver.session() as session:
                for _, row in df.iterrows():
                    # Crear identificador único
                    moto_id = f"{row['Marca']}_{row['Modelo']}".replace(" ", "_").lower()
                    
                    # Crear propiedades
                    properties = {
                        'id': moto_id,
                        'marca': row['Marca'],
                        'modelo': row['Modelo'],
                        'tipo': row['Tipo'].lower() if not pd.isna(row['Tipo']) else 'desconocido',
                        'cilindrada': float(row['Cilindrada']) if not pd.isna(row['Cilindrada']) else 0,
                        'precio': float(row['Precio']) if not pd.isna(row['Precio']) else 0,
                        'potencia': float(row['Potencia']) if not pd.isna(row['Potencia']) else 0,
                        'peso': float(row['Peso']) if not pd.isna(row['Peso']) else 0,
                        'imagen': row['Imagen'] if not pd.isna(row['Imagen']) else '',
                        'año': int(row['Año']) if not pd.isna(row['Año']) else 2023
                    }
                    
                    # Crear nodo de moto
                    session.run("""
                        MERGE (m:Moto {id: $id})
                        SET m.marca = $marca,
                            m.modelo = $modelo,
                            m.tipo = $tipo,
                            m.cilindrada = $cilindrada,
                            m.precio = $precio,
                            m.potencia = $potencia,
                            m.peso = $peso,
                            m.imagen = $imagen,
                            m.año = $año
                    """, **properties)
                    
                    # Crear nodo de marca y relación
                    session.run("""
                        MERGE (m:Moto {id: $id})
                        MERGE (ma:Marca {nombre: $marca})
                        MERGE (m)-[:DE_MARCA]->(ma)
                    """, id=moto_id, marca=row['Marca'])
                    
                    # Crear nodo de estilo y relación
                    session.run("""
                        MERGE (m:Moto {id: $id})
                        MERGE (e:Estilo {nombre: $tipo})
                        MERGE (m)-[:DE_ESTILO]->(e)
                    """, id=moto_id, tipo=row['Tipo'].lower() if not pd.isna(row['Tipo']) else 'desconocido')
                
                logger.info(f"Importación de motos desde CSV completada")
        except Exception as e:
            logger.error(f"Error al importar motos desde CSV: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Inicializa la base de datos Neo4j para MotoMatch")
    parser.add_argument("--uri", default=DEFAULT_URI, help=f"URI de Neo4j (por defecto: {DEFAULT_URI})")
    parser.add_argument("--user", default=DEFAULT_USER, help=f"Usuario de Neo4j (por defecto: {DEFAULT_USER})")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Contraseña de Neo4j")
    parser.add_argument("--clear", action="store_true", help="Limpiar la base de datos antes de inicializarla")
    
    args = parser.parse_args()
    
    logger.info(f"Conectando a Neo4j en {args.uri} con usuario {args.user}")
    
    initializer = Neo4jInitializer(args.uri, args.user, args.password)
    
    try:
        initializer.initialize_database(clear=args.clear)
        logger.info("Inicialización completada con éxito")
    except Exception as e:
        logger.error(f"Error durante la inicialización: {str(e)}")
        sys.exit(1)
    finally:
        initializer.close()

if __name__ == "__main__":
    main()
