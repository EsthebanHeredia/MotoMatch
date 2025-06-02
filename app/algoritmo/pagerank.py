"""
Implementación del algoritmo PageRank adaptado para recomendación de motos.
"""
import numpy as np
import pandas as pd
from collections import defaultdict
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MotoPageRank:
    """
    Implementación del algoritmo PageRank para recomendación de motos.
    """
    
    def __init__(self, damping_factor=0.85, max_iterations=200, tolerance=1e-4):
        """
        Inicializa el algoritmo PageRank con parámetros mejorados.
        
        Args:
            damping_factor (float): Factor de amortiguación (típicamente 0.85)
            max_iterations (int): Número máximo de iteraciones (aumentado a 200)
            tolerance (float): Tolerancia para convergencia (menos estricta)
        """
        self.damping_factor = damping_factor
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.moto_scores = {}
        self.user_scores = {}
        self.graph = defaultdict(list)
        self.reverse_graph = defaultdict(list)
        self.logger = logger
        
    def _safe_numeric_conversion(self, value, default=0.0):
        """
        Convierte un valor a float de manera segura.
        
        Args:
            value: Valor a convertir
            default: Valor por defecto si la conversión falla
            
        Returns:
            float: Valor convertido o valor por defecto
        """
        if value is None:
            return default
            
        # Si ya es numérico, devolverlo
        if isinstance(value, (int, float)):
            return float(value)
            
        # Si es string, intentar convertir
        if isinstance(value, str):
            # Limpiar el string
            cleaned_value = value.strip()
            
            # Manejar strings vacíos
            if not cleaned_value:
                return default
                
            try:
                return float(cleaned_value)
            except ValueError:
                # Intentar extraer números del string
                import re
                numbers = re.findall(r'-?\d+\.?\d*', cleaned_value)
                if numbers:
                    try:
                        return float(numbers[0])
                    except ValueError:
                        pass
                        
                self.logger.warning(f"No se pudo convertir '{value}' a número, usando {default}")
                return default
        
        # Para otros tipos, intentar conversión directa
        try:
            return float(value)
        except (ValueError, TypeError):
            self.logger.warning(f"No se pudo convertir {type(value).__name__} '{value}' a número, usando {default}")
            return default
    
    def build_graph(self, interaction_data):
        """
        Construye el grafo de interacciones desde los datos.
        
        Args:
            interaction_data (list): Lista de diccionarios con interacciones
                Cada diccionario debe tener: user_id, moto_id, weight
        """
        self.logger.info("Construyendo grafo desde datos de interacción...")
        
        # Limpiar datos previos
        self.graph.clear()
        self.reverse_graph.clear()
        self.moto_scores.clear()
        self.user_scores.clear()
        
        # Validar datos de entrada
        if not interaction_data:
            self.logger.warning("No hay datos de interacción para construir el grafo")
            return
            
        # Contadores para debugging
        valid_interactions = 0
        invalid_interactions = 0
        
        # Procesar cada interacción
        for interaction in interaction_data:
            try:
                # Extraer datos básicos
                user_id = interaction.get('user_id')
                moto_id = interaction.get('moto_id')
                raw_weight = interaction.get('weight', 1.0)
                
                # FIXED: Validación más estricta
                if not user_id or not moto_id:
                    invalid_interactions += 1
                    self.logger.debug(f"Interacción inválida: user_id='{user_id}', moto_id='{moto_id}'")
                    continue
                
                # Convertir a strings para asegurar consistencia
                user_id = str(user_id).strip()
                moto_id = str(moto_id).strip()
                
                # Validar que no sean strings vacíos
                if not user_id or not moto_id or user_id == 'None' or moto_id == 'None':
                    invalid_interactions += 1
                    self.logger.debug(f"Interacción con IDs vacíos: user_id='{user_id}', moto_id='{moto_id}'")
                    continue
                
                # Convertir weight de manera segura
                weight = self._safe_numeric_conversion(raw_weight, 1.0)
                
                # Validar que el peso es positivo
                if weight <= 0:
                    weight = 1.0
                
                # Inicializar scores si no existen
                if moto_id not in self.moto_scores:
                    self.moto_scores[moto_id] = 0.0
                if user_id not in self.user_scores:
                    self.user_scores[user_id] = 0.0
                
                # Agregar peso al score de la moto (FIXED: asegurar que ambos son float)
                self.moto_scores[moto_id] = float(self.moto_scores[moto_id]) + float(weight)
                
                # Construir grafo bidireccional
                self.graph[user_id].append((moto_id, weight))
                self.reverse_graph[moto_id].append((user_id, weight))
                
                valid_interactions += 1
                
            except Exception as e:
                self.logger.error(f"Error procesando interacción {interaction}: {str(e)}")
                invalid_interactions += 1
                continue
        
        self.logger.info(f"Grafo construido: {valid_interactions} interacciones válidas, {invalid_interactions} inválidas")
        self.logger.info(f"Nodos: {len(self.moto_scores)} motos, {len(self.user_scores)} usuarios")
        
        # FIXED: Solo crear scores por defecto si tenemos algunos datos válidos pero no suficientes
        if not self.moto_scores and valid_interactions == 0:
            self.logger.warning("No se crearon scores de motos. Inicializando scores por defecto.")
            # Crear al menos algunos scores por defecto si hay motos en los datos
            unique_motos = set()
            for interaction in interaction_data:
                moto_id = interaction.get('moto_id')
                if moto_id and str(moto_id).strip() and str(moto_id) != 'None':
                    unique_motos.add(str(moto_id).strip())
            
            for moto_id in unique_motos:
                self.moto_scores[moto_id] = 1.0
                
        # Si aún no hay motos, el PageRank no funcionará
        if not self.moto_scores:
            self.logger.error("No se pudieron crear scores de motos válidos")
    
    def calculate_pagerank(self):
        """
        Calcula PageRank para todas las motos.
        
        Returns:
            dict: Diccionario con scores de PageRank {moto_id: score}
        """
        if not self.moto_scores:
            self.logger.warning("No hay motos para calcular PageRank")
            return {}
        
        # Inicializar scores
        all_nodes = set(self.moto_scores.keys()) | set(self.user_scores.keys())
        N = len(all_nodes)
        
        # Verificación adicional: si hay muy pocos nodos, retornar scores uniformes
        if N <= 2:
            self.logger.warning("Muy pocos nodos para PageRank, usando scores uniformes")
            return {moto_id: 1.0 for moto_id in self.moto_scores.keys()}
        
        # Inicializar scores con valor uniforme 1/N
        scores = {node: 1.0 / N for node in all_nodes}
        
        # Iterar hasta convergencia
        for iteration in range(self.max_iterations):
            new_scores = {node: (1.0 - self.damping_factor) / N for node in all_nodes}
            
            # Actualizar scores según enlaces entrantes
            for source_node in all_nodes:
                # Solo procesar nodos con enlaces salientes
                if source_node in self.graph:
                    outlinks = self.graph[source_node]
                    if outlinks:  # Evitar división por cero
                        share = self.damping_factor * scores[source_node] / len(outlinks)
                        for target_node, weight in outlinks:
                            new_scores[target_node] += share * weight
        
            # Verificar convergencia con normalización por número de nodos
            diff = sum(abs(new_scores.get(node, 0) - scores.get(node, 0)) for node in all_nodes)
            norm_diff = diff / max(1, len(all_nodes))
            
            # Actualizar scores para la próxima iteración
            scores = new_scores
            
            if norm_diff < self.tolerance:
                self.logger.info(f"PageRank convergió en {iteration + 1} iteraciones")
                break
        else:
            self.logger.warning(f"PageRank no convergió después de {self.max_iterations} iteraciones")
        
        # Extraer solo scores de motos
        moto_pagerank = {moto_id: scores.get(moto_id, 0.0) for moto_id in self.moto_scores.keys()}
        
        # Normalizar scores
        max_score = max(moto_pagerank.values()) if moto_pagerank else 1.0
        if max_score > 0:
            normalized_scores = {moto_id: score / max_score for moto_id, score in moto_pagerank.items()}
            return normalized_scores
        
        self.logger.info(f"PageRank calculado para {len(moto_pagerank)} motos")
        return moto_pagerank
    
    def get_top_motos(self, n=10):
        """
        Obtiene las top N motos según PageRank.
        
        Args:
            n (int): Número de motos a retornar
            
        Returns:
            list: Lista de tuplas (moto_id, score) ordenadas por score descendente
        """
        if not self.moto_scores:
            return []
            
        # Calcular PageRank si no se ha hecho
        pagerank_scores = self.calculate_pagerank()
        
        # Ordenar por score descendente
        sorted_motos = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_motos[:n]
    
    def get_moto_score(self, moto_id):
        """
        Obtiene el score de una moto específica.
        
        Args:
            moto_id: ID de la moto
            
        Returns:
            float: Score de la moto (0.0 si no existe)
        """
        if not self.moto_scores:
            return 0.0
            
        pagerank_scores = self.calculate_pagerank()
        return pagerank_scores.get(moto_id, 0.0)
    
    def update_from_neo4j(self, driver):
        """
        Actualiza el ranking desde Neo4j.
        
        Args:
            driver: Driver de Neo4j
        """
        try:
            self.logger.info("Actualizando ranking desde Neo4j...")
            
            with driver.session() as session:
                # Consulta para obtener interacciones relevantes
                query = """
                MATCH (u:User)-[r:RATED]->(m:Moto)
                RETURN u.id as user_id, m.id as moto_id, r.rating as weight
                UNION
                MATCH (u:User)-[i:INTERACTED]->(m:Moto)
                RETURN u.id as user_id, m.id as moto_id, coalesce(i.weight, 1.0) as weight
                UNION
                MATCH (u:User)-[r:IDEAL]->(m:Moto)
                RETURN u.id as user_id, m.id as moto_id, 5.0 as weight
                """
                
                result = session.run(query)
                interactions = []
                
                for record in result:
                    # Validar que los datos son correctos
                    user_id = record.get('user_id')
                    moto_id = record.get('moto_id')
                    weight = self._safe_numeric_conversion(record.get('weight', 1.0))
                    
                    if user_id and moto_id:
                        interactions.append({
                            'user_id': user_id,
                            'moto_id': moto_id,
                            'weight': weight
                        })
                
                self.logger.info(f"Obtenidas {len(interactions)} interacciones desde Neo4j")
                
                # Construir grafo y calcular PageRank
                if interactions:
                    self.build_graph(interactions)
                    self.calculate_pagerank()
                else:
                    self.logger.warning("No se encontraron interacciones en Neo4j")
                    
        except Exception as e:
            self.logger.error(f"Error actualizando desde Neo4j: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def get_recommendations_for_user(self, user_id, moto_features=None, n=5):
        """
        Obtiene recomendaciones personalizadas para un usuario.
        
        Args:
            user_id: ID del usuario
            moto_features (pandas.DataFrame, optional): Características de las motos
            n (int): Número de recomendaciones
            
        Returns:
            list: Lista de tuplas (moto_id, score, reason)
        """
        if not self.moto_scores:
            return []
            
        # Obtener motos con las que el usuario ya interactuó
        user_motos = set()
        if user_id in self.graph:
            user_motos = {moto_id for moto_id, _ in self.graph[user_id]}
        
        # Calcular PageRank
        pagerank_scores = self.calculate_pagerank()
        
        # Filtrar motos no vistas por el usuario
        available_motos = {moto_id: score for moto_id, score in pagerank_scores.items() 
                          if moto_id not in user_motos}
        
        # Ordenar por score
        sorted_motos = sorted(available_motos.items(), key=lambda x: x[1], reverse=True)
        
        # Preparar recomendaciones con razones
        recommendations = []
        for moto_id, score in sorted_motos[:n]:
            # Razón basada en popularidad
            if score > 0.8:
                reason = "Muy popular entre la comunidad"
            elif score > 0.6:
                reason = "Alta valoración general"
            elif score > 0.4:
                reason = "Buena puntuación comunitaria"
            else:
                reason = "Recomendado por el algoritmo"
            
            recommendations.append((moto_id, score, reason))
        
        return recommendations
