"""
Algoritmo de recomendación de moto ideal mejorado con sistema híbrido
"""
import pandas as pd
import numpy as np
import logging
from .hybrid_recommender import HybridMotoRecommender
from .quantitative_evaluator import QuantitativeEvaluator

logger = logging.getLogger(__name__)

class MotoIdealRecommender:
    """
    Clase mejorada que usa un sistema híbrido para mayor variabilidad y precisión
    """
    def __init__(self, df_motos=None, neo4j_connector=None):
        self.df_motos = df_motos
        self.neo4j_connector = neo4j_connector
        self.hybrid_system = HybridMotoRecommender(neo4j_connector)
        self.quantitative_evaluator = QuantitativeEvaluator()
        self.logger = logging.getLogger(__name__)
        self.logger.info("MotoIdealRecommender inicializado con sistema híbrido y evaluador cuantitativo")
    
    def get_recommendations(self, user_id, top_n=5, preferences=None):
        """
        Obtiene recomendaciones usando el sistema híbrido mejorado con evaluación cuantitativa
        """
        self.logger.info(f"Calculando recomendaciones híbridas para {user_id} con preferencias: {preferences}")
        
        # Si no se proporcionan preferencias, obtenerlas de Neo4j
        if preferences is None and self.neo4j_connector:
            preferences = self._get_user_preferences(user_id)
            
        if not preferences:
            self.logger.warning(f"No se encontraron preferencias para {user_id}")
            preferences = {}
        
        try:
            # Detectar si hay preferencias cuantitativas disponibles
            has_quantitative = self._has_quantitative_preferences(preferences)
            
            if has_quantitative:
                self.logger.info("Detectadas preferencias cuantitativas, usando evaluador híbrido")
                
                # Combinar recomendaciones híbridas con evaluación cuantitativa
                hybrid_recommendations = self.hybrid_system.get_hybrid_recommendations(
                    user_id, preferences, top_n * 2  # Obtener más para diversificar
                )
                
                quantitative_recommendations = self.get_quantitative_recommendations(
                    user_id, preferences, top_n * 2
                )
                
                # Combinar y rebalancear las recomendaciones
                final_recommendations = self._combine_recommendations(
                    hybrid_recommendations, quantitative_recommendations, top_n
                )
                
                if final_recommendations:
                    self.logger.info(f"Generadas {len(final_recommendations)} recomendaciones híbrido-cuantitativas")
                    return final_recommendations
            
            # Si no hay datos cuantitativos o falló la combinación, usar solo híbridas
            hybrid_recommendations = self.hybrid_system.get_hybrid_recommendations(
                user_id, preferences, top_n
            )
            
            if hybrid_recommendations:
                self.logger.info(f"Generadas {len(hybrid_recommendations)} recomendaciones híbridas para {user_id}")
                return hybrid_recommendations
            else:
                # Fallback al método original si el híbrido falla
                self.logger.warning("Sistema híbrido no devolvió resultados, usando fallback")
                return self._fallback_recommendations(top_n)
                
        except Exception as e:
            self.logger.error(f"Error en recomendaciones híbridas: {str(e)}")
            return self._fallback_recommendations(top_n)
    
    def _get_user_preferences(self, user_id):
        """Obtiene las preferencias del usuario desde Neo4j"""
        if not self.neo4j_connector:
            return None
            
        try:
            with self.neo4j_connector.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {id: $user_id})-[:HAS_PREFERENCE]->(p:UserPreference)
                    RETURN p.estilos_preferidos as estilos, p.marcas_preferidas as marcas,
                           p.experiencia as experiencia, p.presupuesto as presupuesto,
                           p.uso_previsto as uso_previsto, p.datos_test as datos_test
                """, user_id=user_id)
                
                record = result.single()
                if record:
                    preferences = {}
                    
                    # Procesar estilos preferidos
                    estilos_str = record.get('estilos', '')
                    if estilos_str:
                        try:
                            import json
                            preferences['estilos'] = json.loads(estilos_str)
                        except:
                            estilos = {}
                            for estilo in estilos_str.split(','):
                                estilo = estilo.strip()
                                if estilo:
                                    estilos[estilo] = 1.0
                            preferences['estilos'] = estilos
                    
                    # Procesar marcas preferidas
                    marcas_str = record.get('marcas', '')
                    if marcas_str:
                        try:
                            import json
                            preferences['marcas'] = json.loads(marcas_str)
                        except:
                            marcas = {}
                            for marca in marcas_str.split(','):
                                marca = marca.strip()
                                if marca:
                                    marcas[marca] = 1.0
                            preferences['marcas'] = marcas
                    
                    # Datos simples
                    preferences['experiencia'] = record.get('experiencia')
                    preferences['presupuesto'] = record.get('presupuesto')
                    preferences['uso_previsto'] = record.get('uso_previsto')
                    
                    # Datos de test completos
                    datos_test = record.get('datos_test')
                    if datos_test:
                        try:
                            import json
                            test_data = json.loads(datos_test)
                            for key, value in test_data.items():
                                if key not in preferences:
                                    preferences[key] = value
                        except:
                            pass
                    
                    return preferences
                    
                return None
        except Exception as e:
            self.logger.error(f"Error al obtener preferencias para {user_id}: {str(e)}")
            return None
    
    def _fallback_recommendations(self, top_n):
        """Recomendaciones de fallback cuando el sistema híbrido falla"""
        if not self.neo4j_connector:
            return []
            
        try:
            with self.neo4j_connector.driver.session() as session:
                result = session.run("""
                    MATCH (m:Moto)
                    OPTIONAL MATCH (m)<-[r:INTERACTED]-()
                    WITH m, count(r) as interactions
                    ORDER BY interactions DESC, m.precio ASC
                    LIMIT $limit
                    RETURN m.id as moto_id, m.marca as marca, m.modelo as modelo,
                           m.tipo as tipo, m.precio as precio, m.cilindrada as cilindrada,
                           m.imagen as imagen, m.anio as anio, interactions as score
                """, limit=top_n)
                
                result_list = []
                for record in result:
                    result_list.append({
                        'moto_id': record['moto_id'],
                        'marca': record['marca'],
                        'modelo': record['modelo'],
                        'tipo': record.get('tipo', 'N/A'),
                        'precio': record.get('precio', 0),
                        'cilindrada': record.get('cilindrada', 0),
                        'imagen': record.get('imagen', ''),
                        'score': record['score'],
                        'note': 'Recomendación popular (sistema de respaldo)',
                        'methods_used': ['popularity_fallback'],
                        'anio': record.get('anio', '')
                    })
                
                return result_list
        except Exception as e:
            self.logger.error(f"Error en recomendaciones de fallback: {str(e)}")
            return []
    
    def get_quantitative_recommendations(self, user_id, preferences, top_n=5):
        """
        Obtiene recomendaciones usando el evaluador cuantitativo
        """
        self.logger.info(f"Calculando recomendaciones cuantitativas para {user_id}")
        
        # Si no tenemos motos cargadas, cargarlas desde Neo4j
        if self.df_motos is None:
            self._load_motos_from_neo4j()
        
        if self.df_motos is None or len(self.df_motos) == 0:
            self.logger.warning("No hay datos de motos disponibles para evaluación cuantitativa")
            return []
        
        try:
            # Usar el evaluador cuantitativo para obtener scores
            scores = self.quantitative_evaluator.evaluate_preferences(preferences, self.df_motos)
            
            # Si no hay scores, devolver lista vacía
            if not scores:
                self.logger.warning("No se generaron scores cuantitativos")
                return []
            
            # Convertir a lista de tuplas ordenadas por score
            recommendations = [(moto_id, score) for moto_id, score in scores.items()]
            recommendations.sort(key=lambda x: x[1], reverse=True)
            
            # Limitar al top_n
            recommendations = recommendations[:top_n]
            
            self.logger.info(f"Generadas {len(recommendations)} recomendaciones cuantitativas")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error en evaluación cuantitativa: {str(e)}")
            return []
    
    def _load_motos_from_neo4j(self):
        """Carga datos de motos desde Neo4j a DataFrame"""
        if not self.neo4j_connector:
            return
            
        try:
            with self.neo4j_connector.driver.session() as session:
                result = session.run("""
                    MATCH (m:Moto)
                    RETURN m.id as id, m.marca as marca, m.modelo as modelo,
                           m.tipo as tipo, m.cilindrada as cilindrada, m.precio as precio,
                           m.potencia as potencia, m.peso as peso, m.torque as torque,
                           m.descripcion as descripcion, m.imagen as imagen, m.anio as anio
                """)
                
                motos_data = []
                for record in result:
                    motos_data.append({
                        'id': record['id'],
                        'marca': record['marca'],
                        'modelo': record['modelo'],
                        'tipo': record['tipo'],
                        'cilindrada': self._parse_numeric(record['cilindrada']),
                        'precio': self._parse_numeric(record['precio']),
                        'potencia': self._parse_numeric(record['potencia']),
                        'peso': self._parse_numeric(record['peso']),
                        'torque': self._parse_numeric(record['torque']),
                        'descripcion': record['descripcion'] or '',
                        'imagen': record['imagen'] or '',
                        'anio': self._parse_numeric(record['anio'])
                    })
                
                self.df_motos = pd.DataFrame(motos_data)
                self.logger.info(f"Cargadas {len(self.df_motos)} motos desde Neo4j")
                
        except Exception as e:
            self.logger.error(f"Error al cargar motos desde Neo4j: {str(e)}")
            
    def _parse_numeric(self, value):
        """Convierte un valor a numérico, manejando strings y valores None"""
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return float(value)
        
        # Si es string, intentar extraer números
        import re
        try:
            if isinstance(value, str):
                # Extraer solo los números
                numbers = re.findall(r'\d+', value)
                if numbers:
                    return float(numbers[0])
            return 0
        except:
            return 0
    
    def _has_quantitative_preferences(self, preferences):
        """
        Detecta si las preferencias contienen datos cuantitativos
        """
        quantitative_keys = ['potencia', 'torque', 'cilindrada', 'presupuesto_min', 'presupuesto_max']
        
        for key in quantitative_keys:
            if key in preferences and preferences[key] is not None:
                return True
                
        # También verificar si hay rangos de presupuesto
        if 'presupuesto' in preferences:
            value = preferences['presupuesto']
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return True
            elif isinstance(value, str) and '-' in value:
                return True
                
        return False
    
    def _combine_recommendations(self, hybrid_recs, quantitative_recs, top_n):
        """
        Combina recomendaciones híbridas y cuantitativas con ponderación balanceada
        """
        try:
            combined_scores = {}
            
            # Peso para cada tipo de recomendación
            hybrid_weight = 0.6
            quantitative_weight = 0.4
            
            # Procesar recomendaciones híbridas
            if hybrid_recs:
                for i, rec in enumerate(hybrid_recs):
                    if isinstance(rec, dict):
                        moto_id = rec.get('moto_id')
                        score = rec.get('score', 0)
                    elif isinstance(rec, tuple):
                        moto_id = rec[0]
                        score = rec[1] if len(rec) > 1 else 0
                    else:
                        continue
                        
                    if moto_id:
                        # Normalizar score híbrido y aplicar peso
                        normalized_score = score * hybrid_weight
                        combined_scores[moto_id] = combined_scores.get(moto_id, 0) + normalized_score
            
            # Procesar recomendaciones cuantitativas
            if quantitative_recs:
                for i, rec in enumerate(quantitative_recs):
                    if isinstance(rec, tuple) and len(rec) >= 2:
                        moto_id = rec[0]
                        score = rec[1]
                    else:
                        continue
                        
                    if moto_id:
                        # Normalizar score cuantitativo y aplicar peso
                        normalized_score = score * quantitative_weight
                        combined_scores[moto_id] = combined_scores.get(moto_id, 0) + normalized_score
            
            # Convertir a lista ordenada
            final_recommendations = [(moto_id, score) for moto_id, score in combined_scores.items()]
            final_recommendations.sort(key=lambda x: x[1], reverse=True)
            
            # Limitar al top_n
            return final_recommendations[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error al combinar recomendaciones: {str(e)}")
            # En caso de error, devolver solo las híbridas
            return hybrid_recs[:top_n] if hybrid_recs else []
    
    def _apply_filters(self, motos, preferences, tolerance=0.2):  # Increase tolerance from 0.1 to 0.2
        """
        Aplica filtros a las motos según las preferencias.
        
        Args:
            motos (list): Lista de motos
            preferences (dict): Preferencias del usuario
            tolerance (float): Tolerancia para ampliar rangos (0.2 = 20%)
            
        Returns:
            list: Motos filtradas
        """
        # Obtener valores mínimos y máximos con tolerancia
        filtered_motos = [...] # your existing filtering code
        
        # Lógica de retroceso
        original_tolerance = tolerance
        max_tolerance = 0.5  # Máximo 50% de tolerancia
        
        while len(filtered_motos) < 10 and tolerance < max_tolerance:
            tolerance += 0.1
            self.logger.info(f"Incrementando tolerancia a {tolerance*100}% para obtener más resultados")
            # Recalcular min/max con nueva tolerancia
            # ...recalculate your filters with the new tolerance...
            # Re-aplicar filtrado
        
        if len(filtered_motos) < 5:
            self.logger.warning(f"Pocos resultados ({len(filtered_motos)}), añadiendo motos recomendadas por popularidad")
            # Agregar algunas motocicletas populares
            popular_motos = self._get_popular_motos(10)
            filtered_motos.extend(popular_motos)
            # Eliminar duplicados
            seen = set()
            filtered_motos = [m for m in filtered_motos if not (m['id'] in seen or seen.add(m['id']))]
        
        return filtered_motos