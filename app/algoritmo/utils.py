"""
Utilidades para los algoritmos de recomendación de motos.
Incluye funciones para conectar con la base de datos y preprocesar datos.
"""
import pandas as pd
import numpy as np
from neo4j import GraphDatabase
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConnector:
    """Clase para manejar conexiones y consultas a Neo4j"""
    
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="22446688"):
        """
        Inicializa el conector a Neo4j.
        
        Args:
            uri (str): URI de Neo4j
            user (str): Nombre de usuario
            password (str): Contraseña
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.is_connected = False
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Probar la conexión
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.is_connected = True
            logger.info("Conexión a Neo4j establecida correctamente")
        except Exception as e:
            logger.error(f"No se pudo conectar a Neo4j: {str(e)}")
    
    def execute_query(self, query, params=None):
        """
        Ejecuta una consulta en Neo4j.
        
        Args:
            query (str): Consulta Cypher a ejecutar
            params (dict, optional): Parámetros para la consulta
            
        Returns:
            list: Resultados de la consulta
        """
        if not self.is_connected:
            logger.error("No hay conexión a Neo4j")
            return None
            
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error al ejecutar consulta: {str(e)}")
            return None
    
    def get_user_data(self):
        """
        Obtiene datos de usuarios.
        
        Returns:
            pandas.DataFrame: DataFrame con datos de usuarios
        """
        if not self.is_connected:
            return pd.DataFrame()
            
        try:
            query = """
            MATCH (u:User)
            RETURN u.user_id as user_id, 
                   u.experiencia as experiencia,
                   u.uso_previsto as uso_previsto,
                   u.presupuesto as presupuesto,
                   u.nombre as nombre,
                   u.password as password
            """
            with self.driver.session() as session:
                result = session.run(query)
                data = [record.data() for record in result]
                return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Error al obtener datos de usuarios: {str(e)}")
            return pd.DataFrame()
    
    def get_users(self):
        """Obtiene todos los usuarios de Neo4j"""
        if not self.is_connected:
            logger.error("No hay conexión a Neo4j para obtener usuarios")
            return pd.DataFrame(columns=['user_id', 'username', 'edad', 'experiencia', 'uso_previsto', 'presupuesto'])
            
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User)
                RETURN u.id AS user_id, 
                       u.username AS username,
                       u.edad AS edad,
                       u.experiencia AS experiencia,
                       u.uso_previsto AS uso_previsto,
                       u.presupuesto AS presupuesto,
                       u.password AS password
                """)
                
                users_data = []
                for record in result:
                    users_data.append({
                        'user_id': record['user_id'],
                        'username': record['username'],
                        'edad': record.get('edad', 30),
                        'experiencia': record.get('experiencia', 'Intermedio'),
                        'uso_previsto': record.get('uso_previsto', 'Paseo'),
                        'presupuesto': record.get('presupuesto', 8000),
                        'password': record.get('password', '')
                    })
                
                logger.info(f"Obtenidos {len(users_data)} usuarios de Neo4j")
                return pd.DataFrame(users_data)
        except Exception as e:
            logger.error(f"Error al obtener usuarios de Neo4j: {str(e)}")
            return pd.DataFrame(columns=['user_id', 'username', 'edad', 'experiencia', 'uso_previsto', 'presupuesto'])
    
    def get_moto_data(self):
        """
        Obtiene datos de motos.
        
        Returns:
            pandas.DataFrame: DataFrame con datos de motos
        """
        if not self.is_connected:
            return pd.DataFrame()
            
        try:
            query = """
            MATCH (m:Moto)
            RETURN m.moto_id as moto_id,
                   m.modelo as modelo,
                   m.marca as marca,
                   m.tipo as tipo,
                   m.potencia as potencia,
                   m.cilindrada as cilindrada,
                   m.peso as peso,
                   m.precio as precio,
                   m.imagen as imagen,
                   m.url as url, 
                   m.anio as anio,
                   m.torque as torque
            """
            with self.driver.session() as session:
                result = session.run(query)
                data = [record.data() for record in result]
                return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Error al obtener datos de motos: {str(e)}")
            return pd.DataFrame()
    
    def get_ratings_data(self):
        """
        Obtiene datos de valoraciones.
        
        Returns:
            pandas.DataFrame: DataFrame con valoraciones
        """
        if not self.is_connected:
            return pd.DataFrame()
            
        try:
            query = """
            MATCH (u:User)-[r:RATED]->(m:Moto)
            RETURN u.user_id as user_id,
                   m.moto_id as moto_id,
                   r.rating as rating
            """
            with self.driver.session() as session:
                result = session.run(query)
                data = [record.data() for record in result]
                return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Error al obtener valoraciones: {str(e)}")
            return pd.DataFrame()
    
    def store_user_preferences(self, user_id, test_data):
        """
        Almacena preferencias del usuario en Neo4j.
        
        Args:
            user_id (str): ID del usuario
            test_data (dict): Datos del test
            
        Returns:
            bool: True si fue exitoso
        """
        if not self.is_connected:
            logger.error("No hay conexión a Neo4j para almacenar preferencias")
            return False
            
        try:
            # Verificar si el usuario existe
            query_check = """
            MATCH (u:User {user_id: $user_id})
            RETURN count(u) as count
            """
            result = self.execute_query(query_check, {'user_id': user_id})
            user_exists = result[0]['count'] > 0 if result else False
            
            if user_exists:
                # Actualizar usuario existente
                query = """
                MATCH (u:User {user_id: $user_id})
                SET u.experiencia = $experiencia,
                    u.uso_previsto = $uso_previsto,
                    u.presupuesto = $presupuesto
                RETURN u
                """
            else:
                # Crear nuevo usuario
                query = """
                CREATE (u:User {
                    user_id: $user_id,
                    experiencia: $experiencia,
                    uso_previsto: $uso_previsto,
                    presupuesto: $presupuesto
                })
                RETURN u
                """
                
            # Ejecutar query con parámetros
            params = {
                'user_id': user_id,
                'experiencia': test_data.get('experiencia', 'principiante'),
                'uso_previsto': test_data.get('uso', 'urbano'),
                'presupuesto': float(test_data.get('presupuesto', 8000))
            }
            
            result = self.execute_query(query, params)
            logger.info(f"Preferencias de {user_id} actualizadas en Neo4j: {params}")
            return True
        except Exception as e:
            logger.error(f"Error al almacenar preferencias de usuario: {str(e)}")
            return False
    
    def close(self):
        """Cierra la conexión a Neo4j."""
        if self.driver:
            self.driver.close()
            self.is_connected = False
    
    def get_motos(self):
        """Obtiene todas las motos de Neo4j"""
        if not self.is_connected:
            logger.error("No hay conexión a Neo4j para obtener motos")
            return pd.DataFrame(columns=['moto_id', 'marca', 'modelo', 'tipo', 'cilindrada', 'precio', 'potencia', 'peso', 'imagen', 'url'])
            
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m:Moto)
                RETURN m.id AS moto_id, 
                       m.marca AS marca,
                       m.modelo AS modelo,
                       m.tipo AS tipo,
                       m.cilindrada AS cilindrada,
                       m.precio AS precio,
                       m.potencia AS potencia,
                       m.peso AS peso,
                       m.imagen AS imagen,
                       m.url AS url,
                       m.anio AS anio,
                       m.torque AS torque              
                """)
                
                motos_data = []
                for record in result:
                    motos_data.append({
                        'moto_id': record['moto_id'],
                        'marca': record['marca'],
                        'modelo': record['modelo'],
                        'tipo': record.get('tipo', 'Desconocido'),
                        'cilindrada': record.get('cilindrada', 0),
                        'precio': record.get('precio', 0),
                        'potencia': record.get('potencia', 0),
                        'peso': record.get('peso', 0),
                        'imagen': record.get('imagen', ''),
                        'url': record.get('url', ''),
                        'anio': record.get('anio', ''),
                        'torque': record.get('torque', 0)
                    })
                
                return pd.DataFrame(motos_data)
        except Exception as e:
            logger.error(f"Error al obtener motos de Neo4j: {str(e)}")
            return pd.DataFrame(columns=['moto_id', 'marca', 'modelo', 'tipo', 'cilindrada', 'precio', 'potencia', 'peso', 'imagen'])
    
    def get_ratings(self):
        """Obtiene todas las valoraciones de Neo4j"""
        if not self.is_connected:
            logger.error("No hay conexión a Neo4j para obtener valoraciones")
            return pd.DataFrame(columns=['user_id', 'moto_id', 'rating'])
            
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User)-[r:RATED]->(m:Moto)
                RETURN u.id AS user_id, 
                       m.id AS moto_id,
                       r.rating AS rating
                """)
                
                ratings_data = []
                for record in result:
                    ratings_data.append({
                        'user_id': record['user_id'],
                        'moto_id': record['moto_id'],
                        'rating': record['rating']
                    })
                
                return pd.DataFrame(ratings_data)
        except Exception as e:
            logger.error(f"Error al obtener valoraciones de Neo4j: {str(e)}")
            return pd.DataFrame(columns=['user_id', 'moto_id', 'rating'])
    
    def _ensure_neo4j_connection(self):
        """Asegura que hay una conexión activa a Neo4j, reintentando si es necesario"""
        if self.is_connected and self.driver:
            try:
                # Verificar que la conexión sigue siendo válida
                with self.driver.session() as session:
                    session.run("RETURN 1")
                return True
            except Exception:
                self.is_connected = False
                self.driver = None
        
        # Si no hay conexión, intentar conectar
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.is_connected = True
            logger.info("Conexión a Neo4j restablecida correctamente")
            return True
        except Exception as e:
            logger.error(f"No se pudo restaurar la conexión a Neo4j: {str(e)}")
            return False


class DataPreprocessor:
    """Clase para preprocesar datos para algoritmos de recomendación"""
    
    @staticmethod
    def clean_data(df):
        """
        Limpia un DataFrame eliminando valores nulos y duplicados.
        
        Args:
            df (pandas.DataFrame): DataFrame a limpiar
            
        Returns:
            pandas.DataFrame: DataFrame limpio
        """
        if df is None or df.empty:
            return pd.DataFrame()
            
        # Eliminar filas con todos los valores nulos
        df_clean = df.dropna(how='all')
        
        # Eliminar duplicados
        df_clean = df_clean.drop_duplicates()
        
        return df_clean
    
    @staticmethod
    def normalize_data(df, columns):
        """
        Normaliza valores numéricos en el rango [0, 1].
        
        Args:
            df (pandas.DataFrame): DataFrame a normalizar
            columns (list): Columnas a normalizar
            
        Returns:
            pandas.DataFrame: DataFrame con columnas normalizadas
        """
        if df is None or df.empty:
            return pd.DataFrame()
            
        df_norm = df.copy()
        
        for col in columns:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                min_val = df[col].min()
                max_val = df[col].max()
                
                if max_val > min_val:
                    df_norm[col] = (df[col] - min_val) / (max_val - min_val)
                else:
                    df_norm[col] = 0  # Si todos los valores son iguales
        
        return df_norm
        
    @staticmethod
    def encode_categorical(df, columns):
        """
        Codifica variables categóricas usando one-hot encoding.
        
        Args:
            df (pandas.DataFrame): DataFrame a procesar
            columns (list): Columnas categóricas a codificar
            
        Returns:
            pandas.DataFrame: DataFrame con columnas codificadas
        """
        if df is None or df.empty:
            return pd.DataFrame()
            
        df_encoded = df.copy()
        
        for col in columns:
            if col in df.columns and pd.api.types.is_object_dtype(df[col]):
                dummies = pd.get_dummies(df[col], prefix=col)
                df_encoded = pd.concat([df_encoded.drop(col, axis=1), dummies], axis=1)
        
        return df_encoded
        
    @staticmethod
    def normalize_features(df, columns=None):
        """
        Normaliza características numéricas a escala 0-1.
        
        Args:
            df (pandas.DataFrame): DataFrame con columnas numéricas
            columns (list, optional): Lista de columnas a normalizar
            
        Returns:
            pandas.DataFrame: DataFrame con columnas normalizadas
        """
        if df is None or df.empty:
            return df
            
        result = df.copy()
        
        # Si no se especifican columnas, detectar automáticamente
        if columns is None:
            columns = [col for col in result.columns 
                     if col not in ['user_id', 'moto_id'] 
                     and pd.api.types.is_numeric_dtype(result[col])]
                     
        # Normalizar cada columna
        for col in columns:
            if col in result.columns:
                min_val = result[col].min()
                max_val = result[col].max()
                
                # Evitar división por cero
                if min_val == max_val:
                    result[col] = 0.5  # Valor medio si todos son iguales
                else:
                    result[col] = (result[col] - min_val) / (max_val - min_val)
        
        return result