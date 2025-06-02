import logging
import pandas as pd
import numpy as np
import os
import time
import traceback
import json
from neo4j import GraphDatabase
from app.algoritmo.pagerank import MotoPageRank
from app.algoritmo.label_propagation import MotoLabelPropagation
from app.algoritmo.moto_ideal import MotoIdealRecommender
from app.algoritmo.utils import DatabaseConnector, DataPreprocessor

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MotoRecommenderAdapter')

class MotoRecommenderAdapter:
    """Adaptador que integra diferentes algoritmos de recomendación para motos."""
    
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="22446688"):
        """Inicializa el adaptador con la conexión a Neo4j"""
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.motos_df = None
        self.users_df = None
        self.logger = logging.getLogger(__name__)
        self.neo4j_connector = self  # Para que el recomendador híbrido pueda acceder al conector
        
        # Inicializar DataFrames
        self.ratings_df = None
        self.friendships_df = None
        
        # Configuración
        self.allow_mock_data = False  # Solo usar datos de Neo4j
        
        # Inicializar algoritmos de recomendación correctamente
        self.pagerank = MotoPageRank()
        self.label_propagation = MotoLabelPropagation()
        
        # Usar la versión simplificada de MotoIdealRecommender
        try:
            from app.algoritmo.moto_ideal_simple import MotoIdealRecommender
            self.moto_ideal = MotoIdealRecommender(neo4j_connector=self)
            logger.info("Usando MotoIdealRecommender simplificado")
        except ImportError:
            from app.algoritmo.moto_ideal import MotoIdealRecommender
            self.moto_ideal = MotoIdealRecommender()
            logger.info("Usando MotoIdealRecommender estándar")
        
        # Conectar a Neo4j inmediatamente
        if not self.connect_to_neo4j():
            logger.error("No se pudo establecer la conexión inicial con Neo4j")
            raise ConnectionError("No se pudo conectar a Neo4j")
        
        # Cargar datos inmediatamente
        self.load_data()
        
    def connect_to_neo4j(self, max_retries=3, timeout=10):
        """Establecer conexión robusta a Neo4j."""
        from neo4j import GraphDatabase
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Intento {attempt+1}/{max_retries} de conexión a Neo4j: {self.uri}")
                
                # Cerrar driver existente si hay uno
                if self.driver:
                    try:
                        self.driver.close()
                    except Exception as e:
                        logger.warning(f"Error al cerrar driver existente: {str(e)}")
                    self.driver = None
                
                # Crear nuevo driver
                self.driver = GraphDatabase.driver(
                    self.uri, 
                    auth=(self.user, self.password),
                    max_connection_lifetime=3600  # 1 hora
                )
                
                # Test connection
                with self.driver.session() as session:
                    result = session.run("RETURN 'Conexión exitosa' as mensaje")
                    message = result.single()["mensaje"]
                    logger.info(f"Neo4j: {message}")
                
                logger.info("Conexión a Neo4j establecida exitosamente")
                return True
                
            except Exception as e:
                logger.error(f"Error de conexión a Neo4j (intento {attempt+1}): {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = timeout * (attempt + 1)
                    logger.info(f"Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    logger.error("Se agotaron los intentos de conexión a Neo4j.")
                    return False
                    
    def _ensure_neo4j_connection(self):
        """Asegura que hay una conexión activa a Neo4j o intenta reconectar."""
        try:
            if not self.driver:
                logger.warning("No hay un driver de Neo4j, intentando conectar...")
                return self.connect_to_neo4j()
            
            # Probar la conexión existente
            with self.driver.session() as session:
                try:
                    result = session.run("RETURN 'Conexión verificada' as mensaje")
                    message = result.single()["mensaje"]
                    logger.debug(f"Neo4j conexión verificada: {message}")
                    return True
                except Exception as session_error:
                    logger.warning(f"Error con la sesión actual: {str(session_error)}. Reconectando...")
                    return self.connect_to_neo4j()
        except Exception as e:
            logger.error(f"Error al verificar conexión Neo4j: {str(e)}")
            return self.connect_to_neo4j()
    
    def load_data(self):
        """Cargar datos desde Neo4j de manera robusta"""
        self.logger.info("Cargando datos desde Neo4j (modo exclusivo)")
        
        if not self.driver:
            self.logger.error("No hay conexión a Neo4j disponible")
            if not self.allow_mock_data:
                self.logger.error("La aplicación requiere Neo4j. No se usarán datos mock.")
                raise RuntimeError("No se pudieron cargar datos desde Neo4j")
            return False
        
        try:
            # Intentar cargar datos reales desde Neo4j
            success = self._load_from_neo4j()
            if success:
                self.logger.info(f"Datos cargados desde Neo4j: {len(self.motos_df)} motos, {len(self.users_df)} usuarios, {len(self.ratings_df)} ratings")
                
                # NUEVO: Construir ranking con manejo de errores mejorado
                try:
                    self.logger.info("Construyendo ranking desde datos de interacción...")
                    
                    # Preparar datos para PageRank con validación de tipos
                    pagerank_data = []
                    for _, row in self.ratings_df.iterrows():
                        # Validar y convertir datos
                        user_id = str(row['user_id']) if row['user_id'] else None
                        moto_id = str(row['moto_id']) if row['moto_id'] else None
                        
                        # Convertir weight de manera segura
                        raw_weight = row.get('rating', 1.0)
                        try:
                            if isinstance(raw_weight, str):
                                # Limpiar string y convertir
                                cleaned_weight = raw_weight.strip()
                                weight = float(cleaned_weight) if cleaned_weight else 1.0
                            else:
                                weight = float(raw_weight) if raw_weight is not None else 1.0
                        except (ValueError, TypeError):
                            weight = 1.0
                            self.logger.warning(f"Peso inválido '{raw_weight}' convertido a 1.0")
                        
                        # Solo agregar si tenemos datos válidos
                        if user_id and moto_id and weight > 0:
                            pagerank_data.append({
                                'user_id': user_id,
                                'moto_id': moto_id,
                                'weight': weight
                            })
                    
                    self.logger.info(f"Preparados {len(pagerank_data)} registros para PageRank")
                    
                    # Construir grafo con datos validados
                    if pagerank_data:
                        self.pagerank.build_graph(pagerank_data)
                        self.logger.info("Ranking de motos construido exitosamente")
                    else:
                        self.logger.warning("No hay datos válidos para construir el ranking")
                        
                except Exception as ranking_error:
                    self.logger.error(f"Error construyendo ranking: {str(ranking_error)}")
                    # Continuar sin ranking en lugar de fallar completamente
                    self.logger.info("Continuando sin sistema de ranking...")
                
                return True
            else:
                self.logger.error("Error crítico al cargar datos desde Neo4j")
                
        except Exception as e:
            self.logger.error(f"Error crítico al cargar datos desde Neo4j: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Si llegamos aquí, falló la carga desde Neo4j
        if not self.allow_mock_data:
            self.logger.error("La aplicación requiere Neo4j. No se usarán datos mock.")
            raise RuntimeError("No se pudieron cargar datos desde Neo4j")
        
        return False
    
    def _load_from_neo4j(self):
        """Carga los datos reales desde Neo4j."""
        logger.info("Cargando datos desde Neo4j...")
        
        try:
            # Verificar conexión a Neo4j
            if not self._ensure_neo4j_connection():
                logger.error("No se pudo conectar a Neo4j. La aplicación requiere Neo4j.")
                raise ConnectionError("No hay conexión a Neo4j")
                
            # Usar DatabaseConnector para obtener datos
            db_connector = DatabaseConnector(self.driver)
            
            # Cargar datos con manejo de errores mejorado
            try:
                self.users_df = db_connector.get_users()
                if self.users_df is not None and not self.users_df.empty:
                    logger.info(f"Usuarios cargados: {len(self.users_df)}")
                else:
                    logger.warning("No se encontraron usuarios")
                    self.users_df = pd.DataFrame()
            except Exception as e:
                logger.error(f"Error al cargar usuarios: {str(e)}")
                self.users_df = pd.DataFrame()

            try:
                self.motos_df = db_connector.get_motos()
                if self.motos_df is not None and not self.motos_df.empty:
                    logger.info(f"Motos cargadas: {len(self.motos_df)}")
                else:
                    logger.warning("No se encontraron motos")
                    self.motos_df = pd.DataFrame()
            except Exception as e:
                logger.error(f"Error al cargar motos: {str(e)}")
                self.motos_df = pd.DataFrame()

            try:
                self.ratings_df = db_connector.get_ratings()
                if self.ratings_df is not None and not self.ratings_df.empty:
                    logger.info(f"Ratings cargados: {len(self.ratings_df)}")
                else:
                    logger.warning("No se encontraron ratings")
                    self.ratings_df = pd.DataFrame()
            except Exception as e:
                logger.error(f"Error al cargar ratings: {str(e)}")
                self.ratings_df = pd.DataFrame()
            
            # Verificar que se obtuvieron datos
            if self.motos_df.empty:
                logger.error("No se obtuvieron datos de motos desde Neo4j")
                raise ValueError("No hay datos de motos en Neo4j")
            
            # Inicializar algoritmos con los datos de Neo4j
            if hasattr(self.pagerank, 'build_graph') and not self.ratings_df.empty:
                # Preparar datos para PageRank
                pagerank_data = []
                for _, row in self.ratings_df.iterrows():
                    try:
                        pagerank_data.append({
                            'user_id': str(row['user_id']),
                            'moto_id': str(row['moto_id']),
                            'weight': float(row['rating'])/5.0  # Normalizar ratings a 0-1
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error al procesar rating: {str(e)}")
                        continue
                
                if pagerank_data:
                    # Construir el grafo con los datos
                    self.pagerank.build_graph(pagerank_data)
                    logger.info("Grafo de PageRank construido exitosamente")
            
            # Inicializar otros algoritmos si tienen el método load_data
            if hasattr(self.label_propagation, 'load_data'):
                self.label_propagation.load_data(self.users_df, self.motos_df, self.ratings_df)
            elif hasattr(self.label_propagation, 'add_moto_features'):
                # Convertir las motos a una lista de diccionarios para el algoritmo de similitud
                moto_features_list = self.motos_df.to_dict('records')
                self.label_propagation.add_moto_features(moto_features_list)
            
            if hasattr(self.moto_ideal, 'load_data'):
                self.moto_ideal.load_data(self.users_df, self.motos_df, self.ratings_df)
            
            # Cargar relaciones de amistad si es posible
            try:
                self._load_friendships_from_neo4j()
            except Exception as e:
                logger.warning(f"Error al cargar relaciones de amistad: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error crítico al cargar datos desde Neo4j: {str(e)}")
            traceback.print_exc()
            
            # No usar datos mock - fallar explícitamente
            logger.error("La aplicación requiere Neo4j. No se usarán datos mock.")
            raise RuntimeError("No se pudieron cargar datos desde Neo4j")
    
    def _load_friendships_from_neo4j(self):
        """Carga relaciones de amistad entre usuarios desde Neo4j."""
        logger.info("Cargando relaciones de amistad desde Neo4j...")
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u1:User)-[:FRIEND]->(u2:User)
                RETURN u1.id AS user_id, u2.id AS friend_id
                """)
                
                friendships_data = []
                for record in result:
                    friendships_data.append({
                        'user_id': record['user_id'],
                        'friend_id': record['friend_id']
                    })
                
                self.friendships_df = pd.DataFrame(friendships_data)
                logger.info(f"Relaciones de amistad cargadas: {len(self.friendships_df)}")
                
        except Exception as e:
            logger.error(f"Error al cargar relaciones de amistad: {str(e)}")
            self.friendships_df = pd.DataFrame(columns=['user_id', 'friend_id'])
    
    def get_recommendations(self, user_id, algorithm='hybrid', top_n=5, user_preferences=None):
        """Obtiene recomendaciones según el algoritmo especificado"""
        try:
            # Validar preferencias
            if user_preferences is None:
                user_preferences = {}
            
            # Asegurar que uso_previsto tenga un valor válido
            if 'uso_previsto' not in user_preferences or not user_preferences['uso_previsto']:
                user_preferences['uso_previsto'] = 'Mixto'
            
            # Asegurar que experiencia tenga un valor válido
            if 'experiencia' not in user_preferences or not user_preferences['experiencia']:
                user_preferences['experiencia'] = 'Principiante'
            
            self.logger.info(f"Calculando recomendaciones para {user_id} con preferencias: {user_preferences}")
            
            # Obtener recomendaciones según el algoritmo
            if algorithm == 'pagerank':
                return self._get_pagerank_recommendations(user_id, top_n)
            elif algorithm == 'label_propagation':
                return self._get_label_propagation_recommendations(user_id, top_n)
            elif algorithm in ['hybrid', 'moto_ideal']:
                return self._get_recommendations_with_preferences(user_id, user_preferences, top_n)
            else:
                self.logger.warning(f"Algoritmo no reconocido: {algorithm}, usando híbrido por defecto")
                return self._get_recommendations_with_preferences(user_id, user_preferences, top_n)
                
        except Exception as e:
            self.logger.error(f"Error al obtener recomendaciones: {str(e)}")
            return []
    
    def _get_pagerank_recommendations(self, user_id, top_n):
        """Obtiene recomendaciones usando PageRank"""
        try:
            return self.pagerank.get_recommendations(user_id, top_n)
        except Exception as e:
            self.logger.error(f"Error al obtener recomendaciones con PageRank: {str(e)}")
            return []
    
    def _get_label_propagation_recommendations(self, user_id, top_n):
        """Obtiene recomendaciones usando propagación de etiquetas"""
        try:
            if not self.label_propagation.user_preferences:
                # Preparar datos de interacciones con características detalladas de las motos
                interactions = self._get_enriched_interactions(user_id)
                self.label_propagation.initialize_from_interactions(interactions)
            return self.label_propagation.get_recommendations(user_id, top_n)
        except Exception as e:
            self.logger.error(f"Error al obtener recomendaciones con Label Propagation: {str(e)}")
            return []
    
    def _get_recommendations_with_preferences(self, user_id, preferences, top_n=5, save_to_db=False):
        """Obtiene recomendaciones basadas en preferencias específicas"""
        try:
            self.logger.info(f"Calculando recomendaciones con preferencias: {preferences}")
            
            # Crear instancia del recomendador híbrido
            from app.algoritmo.hybrid_recommender import HybridMotoRecommender
            recommender = HybridMotoRecommender(self)  # Pasar self como conector
            
            # Obtener recomendaciones
            recommendations = recommender.get_hybrid_recommendations(user_id, preferences, top_n)
            
            # Guardar recomendaciones en la base de datos si se solicita
            if save_to_db and recommendations:
                self._save_recommendations_to_db(user_id, recommendations)
            
            self.logger.info(f"Generadas {len(recommendations)} recomendaciones para {user_id}")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error al obtener recomendaciones con preferencias: {str(e)}")
            return []
        
    def _user_exists(self, user_id):
        """Comprueba si un usuario existe por su ID."""
        if self.users_df is None:
            return False
        return user_id in self.users_df['user_id'].values
        
    def set_ideal_moto(self, username, moto_id):
        """
        Establece una moto como la ideal para un usuario y la guarda en Neo4j.
        
        Args:
            username (str): Nombre del usuario
            moto_id (str): ID de la moto ideal
            
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        logger.info(f"Guardando moto {moto_id} como ideal para usuario {username}")
        
        # Asegurar que hay conexión a Neo4j
        self._ensure_neo4j_connection()
        
        try:
            # Buscar el ID del usuario en la base de datos
            user_id = username
            if self.users_df is not None:
                user_rows = self.users_df[self.users_df['username'] == username]
                if not user_rows.empty:
                    user_id = user_rows.iloc[0].get('user_id', username)
            
            # Razones por defecto
            default_reasons = ["Seleccionada como moto ideal por el usuario"]
            
            # Intentar obtener detalles de la moto para mejores razones
            try:
                moto_details = self.get_moto_by_id(moto_id)
                if moto_details:
                    marca = moto_details.get('marca', '')
                    modelo = moto_details.get('modelo', '')
                    tipo = moto_details.get('tipo', '')
                    
                    reasons = [
                        f"Te gusta la marca {marca}",
                        f"El modelo {modelo} se ajusta a tus preferencias"
                    ]
                    
                    if tipo:
                        reasons.append(f"Prefieres el estilo {tipo}")
                else:
                    reasons = default_reasons
            except Exception as e:
                logger.error(f"Error al obtener detalles de la moto: {str(e)}")
                reasons = default_reasons
            
            # Usar el DatabaseConnector para guardar en Neo4j
            with self.driver.session() as session:
                # Convertir reasons a formato JSON
                reasons_json = json.dumps(reasons)
                
                # Actualizar o crear la relación de IDEAL
                result = session.run("""
                MATCH (u:User {id: $user_id})
                MATCH (m:Moto {id: $moto_id})
                MERGE (u)-[r:IDEAL]->(m)
                SET r.score = 100.0,
                    r.reasons = $reasons,
                    r.timestamp = timestamp()
                RETURN r
                """, user_id=user_id, moto_id=moto_id, reasons=reasons_json)
                
                return True
        except Exception as e:
            logger.error(f"Error al guardar moto ideal: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def get_moto_by_id(self, moto_id):
        """Obtiene los datos de una moto por su ID"""
        try:
            if not self.motos_df.empty:
                # Buscar la moto en el DataFrame
                moto_data = self.motos_df[self.motos_df['moto_id'] == moto_id]
                if len(moto_data) > 0:
                    # Convertir a diccionario y devolver
                    moto_dict = moto_data.iloc[0].to_dict()
                    return moto_dict
        
            # Si no se encuentra en el DataFrame o está vacío, intentar con Neo4j
            if self.driver:
                with self.driver.session() as session:
                    result = session.run(
                        "MATCH (m:Moto) WHERE m.id = $moto_id RETURN m",
                        moto_id=moto_id
                    )
                    record = result.single()
                    if record:
                        moto = record['m']
                        moto_data = dict(moto.items())
                        return moto_data
        
            self.logger.error(f"Moto no encontrada con ID: {moto_id}")
            return None
        except Exception as e:
            self.logger.error(f"Error al obtener moto por ID: {str(e)}")
            return None
    
    def get_popular_motos(self, top_n=10):
        """
        Obtiene las motos más populares usando PageRank.
        
        Args:
            top_n (int): Número de motos a devolver
            
        Returns:
            list: Lista de motos populares con sus puntuaciones
        """
        try:
            # Conectar a Neo4j si es necesario
            if not self._ensure_neo4j_connection():
                logger.error("No se pudo conectar a Neo4j para obtener motos populares")
                return self._get_mock_popular_motos(top_n)
                
            # FIXED: Mejorar la consulta para obtener datos correctos
            query = """
            MATCH (u:User)-[r:INTERACTED]->(m:Moto)
            WHERE r.type = 'like' OR r.type = 'rating'
            RETURN u.id as user_id, m.id as moto_id, 
                   COALESCE(r.weight, 1.0) as weight
            UNION
            MATCH (u:User)-[r:RATED]->(m:Moto)
            RETURN u.id as user_id, m.id as moto_id, 
                   COALESCE(r.rating, 1.0) as weight
            UNION
            MATCH (u:User)-[r:IDEAL]->(m:Moto)
            RETURN u.id as user_id, m.id as moto_id, 
                   5.0 as weight
            """
            
            with self.driver.session() as session:
                result = session.run(query)
                
                # FIXED: Convertir a formato de diccionario con validación
                interactions = []
                for record in result:
                    user_id = record.get("user_id")
                    moto_id = record.get("moto_id")
                    weight = record.get("weight", 1.0)
                    
                    # Validar que tenemos datos válidos
                    if user_id and moto_id:
                        # Asegurar que weight es numérico
                        try:
                            weight = float(weight) if weight is not None else 1.0
                        except (ValueError, TypeError):
                            weight = 1.0
                            
                        interaction = {
                            'user_id': str(user_id),
                            'moto_id': str(moto_id),
                            'weight': weight
                        }
                        interactions.append(interaction)
            
            logger.info(f"Obtenidas {len(interactions)} interacciones para PageRank")
            
            # Si no hay datos de interacción suficientes, devolver motos mock
            if len(interactions) < 5:
                logger.warning("Pocos datos de interacción para calcular motos populares, usando datos mock")
                return self._get_mock_popular_motos(top_n)
                
            # Inicializar y ejecutar PageRank
            from app.algoritmo.pagerank import MotoPageRank
            pagerank = MotoPageRank()
            pagerank.build_graph(interactions)
            
            # FIXED: Usar el parámetro correcto 'n' en lugar de 'top_n'
            popular_moto_rankings = pagerank.get_top_motos(n=top_n)
            
            if not popular_moto_rankings:
                logger.warning("No se obtuvieron rankings de PageRank, usando datos mock")
                return self._get_mock_popular_motos(top_n)
            
            # Obtener información detallada de las motos
            popular_motos_info = []
            
            for i, (moto_id, score) in enumerate(popular_moto_rankings):
                # Buscar datos de la moto en Neo4j
                moto_query = """
                MATCH (m:Moto {id: $moto_id})
                OPTIONAL MATCH (u:User)-[r:INTERACTED]->(m) WHERE r.type = 'like'
                RETURN m.marca as marca, m.modelo as modelo, m.tipo as estilo,
                       m.precio as precio, m.imagen as imagen, count(r) as likes
                """
                
                with self.driver.session() as session:
                    result = session.run(moto_query, moto_id=moto_id)
                    record = result.single()
                    
                    if record:
                        # FIXED: Asegurar que todos los campos requeridos están presentes
                        moto_info = {
                            'moto_id': moto_id,
                            'marca': record.get('marca', 'Marca desconocida'),
                            'modelo': record.get('modelo', 'Modelo desconocido'),
                            'estilo': record.get('estilo', 'Estilo desconocido'),
                            'precio': record.get('precio', 0),
                            'imagen': record.get('imagen', '/static/images/default-moto.jpg'),
                            'likes': record.get('likes', 0),
                            'score': round(score * 100, 1),  # Convertir a escala 0-100
                            'ranking_position': i + 1
                        }
                        popular_motos_info.append(moto_info)
            
            logger.info(f"Obtenidas {len(popular_motos_info)} motos populares del ranking PageRank")
            
            # Si no obtuvimos suficientes motos, complementar con mock data
            if len(popular_motos_info) < top_n:
                logger.info("Complementando con datos mock para alcanzar el número solicitado")
                mock_motos = self._get_mock_popular_motos(top_n - len(popular_motos_info))
                # Ajustar posiciones de ranking
                for i, moto in enumerate(mock_motos):
                    moto['ranking_position'] = len(popular_motos_info) + i + 1
                    moto['score'] = max(0, moto.get('score', 50) - (i * 10))  # Decrementar scores
                popular_motos_info.extend(mock_motos)
            
            return popular_motos_info[:top_n]
            
        except Exception as e:
            logger.error(f"Error al obtener motos populares: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # En caso de error, devolver datos mock
            return self._get_mock_popular_motos(top_n)
    
    def save_preferences(self, user_id, preferences):
        """
        Guarda las preferencias del usuario en Neo4j.
        
        Args:
            user_id (str): ID del usuario
            preferences (dict): Preferencias del usuario
        
        Returns:
            bool: True si se guardaron correctamente
        """
        if not self._ensure_neo4j_connection():
            self.logger.error("Error de conexión a Neo4j al guardar preferencias")
            return False
            
        try:
            with self.driver.session() as session:
                # Convertir preferencias a formato adecuado para Neo4j
                prefs_json = json.dumps(preferences)
                
                # Guardar preferencias en el nodo User
                query = """
                MATCH (u:User {id: $user_id})
                SET u.preferences = $preferences
                RETURN u
                """
                
                result = session.run(query, user_id=user_id, preferences=prefs_json)
                summary = result.consume()
                
                if summary.counters.properties_set > 0:
                    self.logger.info(f"Preferencias guardadas para usuario {user_id}")
                    return True
                else:
                    self.logger.warning(f"No se guardaron preferencias para {user_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error guardando preferencias: {str(e)}")
            return False