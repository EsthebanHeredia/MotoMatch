"""
Sistema híbrido de recomendaciones que combina múltiples algoritmos para mayor variabilidad y precisión
"""
import pandas as pd
import numpy as np
import logging
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from typing import List, Dict
from .quantitative_evaluator import QuantitativeEvaluator



logger = logging.getLogger(__name__)

class HybridMotoRecommender:
    """
    Sistema híbrido que combina:
    1. Filtrado basado en contenido (características de motos)
    2. Filtrado colaborativo (comportamiento de usuarios similares)
    3. Algoritmo basado en conocimiento (reglas expertas)
    4. Diversificación activa
    5. Exploración vs Explotación
    """
    def __init__(self, neo4j_connector=None):
        self.neo4j_connector = neo4j_connector
        self.motos_df = None
        self.users_df = None
        self.interactions_df = None
        self.user_similarity_matrix = None
        self.moto_features_matrix = None
        self.scaler = StandardScaler()
        self.quantitative_evaluator = QuantitativeEvaluator()
        self.logger = logging.getLogger(__name__)

        # Puedes pasar los pesos como argumento, o usar los default
        self.weights ={
            'content': 0.1,
            'knowledge': 0.7,
            'popularity': 0.2
        }

        # Define los máximos teóricos de cada método
        self.CONTENT_MAX = 1.5
        self.KNOWLEDGE_MAX = 8.0
        self.POPULARITY_MAX = 1.0

    @property
    def score_max(self):
        """Calcula el score máximo teórico según los pesos actuales"""
        
        return (
            (self.CONTENT_MAX * self.weights['content'] +
            self.KNOWLEDGE_MAX * self.weights['knowledge'] +
            self.POPULARITY_MAX * self.weights['popularity'])*1.1 # Añadir un 10% de margen para exploración
        )
        
    def _load_data(self):
        """Carga y prepara todos los datos necesarios"""
        if not self.neo4j_connector:
            return False
            
        try:
            with self.neo4j_connector.driver.session() as session:
                # Cargar motos con todas sus características
                motos_query = """
                MATCH (m:Moto)
                RETURN m.id as id, m.marca as marca, m.modelo as modelo, 
                       m.tipo as tipo, m.cilindrada as cilindrada, m.precio as precio,
                       m.potencia as potencia, m.peso as peso,
                       m.imagen as imagen, m.url as url, m.anio as anio, m.torque as torque
                """
                result = session.run(motos_query)
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
                        'imagen': record['imagen'] or '',
                        'url': record['url'] or '',
                        'anio': self._parse_numeric(record['anio']),
                        'torque': self._parse_numeric(record['torque'])
                    })
                self.motos_df = pd.DataFrame(motos_data)
                
                # Cargar usuarios y sus preferencias
                users_query = """
                MATCH (u:User)
                RETURN u.id as id, u.username as username
                """
                result = session.run(users_query)
                users_data = []
                for record in result:
                    users_data.append({
                        'id': record['id'],
                        'username': record['username']
                    })
                self.users_df = pd.DataFrame(users_data)
                
                # Cargar interacciones (likes, views, etc.)
                interactions_query = """
                MATCH (u:User)-[r:INTERACTED]->(m:Moto)
                RETURN u.id as user_id, m.id as moto_id, r.type as interaction_type,
                       r.weight as weight, r.timestamp as timestamp
                """
                result = session.run(interactions_query)
                interactions_data = []
                for record in result:
                    interactions_data.append({
                        'user_id': record['user_id'],
                        'moto_id': record['moto_id'],
                        'interaction_type': record['interaction_type'],
                        'weight': float(record['weight']) if record['weight'] else 1.0,
                        'timestamp': record['timestamp']
                    })
                self.interactions_df = pd.DataFrame(interactions_data)
                
                logger.info(f"Datos cargados: {len(self.motos_df)} motos, {len(self.users_df)} usuarios, {len(self.interactions_df)} interacciones")
                return True
                
        except Exception as e:
            logger.error(f"Error cargando datos: {str(e)}")
            return False
    
    def _parse_numeric(self, value):
        """Convierte valores a numérico de forma segura"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            import re
            # Extraer números de strings
            numbers = re.findall(r'\d+\.?\d*', str(value))
            return float(numbers[0]) if numbers else 0.0
        except:
            return 0.0
    
    def _prepare_feature_matrices(self):
        """Prepara matrices de características para similitud"""
        if self.motos_df is None:
            return
            
        # Crear matriz de características de motos
        numeric_features = ['cilindrada', 'precio', 'potencia', 'peso', 'anio']
        feature_matrix = []
        
        for _, moto in self.motos_df.iterrows():
            features = []
            
            # Características numéricas normalizadas
            for feature in numeric_features:
                features.append(moto[feature])
            
            # Características categóricas (one-hot encoding simplificado)
            # Tipos de moto
            tipos = ['naked', 'sport', 'touring', 'trail', 'scooter', 'cruiser', 'enduro']
            tipo_moto = str(moto['tipo']).lower()
            for tipo in tipos:
                features.append(1.0 if tipo in tipo_moto else 0.0)
            
            # Marcas principales
            marcas = ['yamaha', 'honda', 'kawasaki', 'suzuki', 'bmw', 'ducati', 'ktm', 'aprilia']
            marca_moto = str(moto['marca']).lower()
            for marca in marcas:
                features.append(1.0 if marca in marca_moto else 0.0)
            
            feature_matrix.append(features)
        
        # Normalizar características numéricas
        self.moto_features_matrix = self.scaler.fit_transform(feature_matrix)
        logger.info(f"Matriz de características creada: {self.moto_features_matrix.shape}")
    
    
    def get_hybrid_recommendations(self, user_id, preferences, top_n=5):
        """Obtiene recomendaciones híbridas combinando múltiples métodos"""
        try:
            # Cargar datos si es necesario
            if not self._load_data():
                self.logger.error("No se pudieron cargar los datos")
                return []
            
            # Preparar matrices de características
            #self._prepare_feature_matrices()
            
            # Obtener recomendaciones de cada método
            content_recs = self._content_based_recommendations(preferences, top_n)
            knowledge_recs = self._knowledge_based_recommendations(preferences, top_n)
            popularity_recs = self._popularity_based_recommendations(top_n)
            
            # Combinar y diversificar recomendaciones
            final_recommendations = self._combine_and_diversify_recommendations(
                content_recs, knowledge_recs, popularity_recs,
                user_id, preferences, top_n
            )
            
            return final_recommendations
            
        except Exception as e:
            self.logger.error(f"Error en recomendaciones híbridas: {str(e)}")
            return []
    
    def _content_based_recommendations(self, preferences: Dict, top_n: int) -> List[Dict]:
        """Obtiene recomendaciones basadas en el contenido de las preferencias"""
        try:
            uso_previsto = preferences.get('uso_previsto', 'mixto').lower()
            presupuesto_min = float(preferences.get('presupuesto_min', 0))
            presupuesto_max = float(preferences.get('presupuesto_max', 100000))
            cilindrada_max = float(preferences.get('cilindrada_max', 2000))

            if cilindrada_max > 400: experiencia = 'avanzado'
            else: experiencia = 'inexperto'

            filtered_motos = self.motos_df.copy()

            if uso_previsto == 'ciudad':
                filtered_motos = filtered_motos[filtered_motos['tipo'].str.lower().isin(['naked', 'scooter'])]
            elif uso_previsto == 'paseo':
                filtered_motos = filtered_motos[filtered_motos['tipo'].str.lower().isin(['sport', 'touring'])]
            elif uso_previsto == 'mixto':
                filtered_motos = filtered_motos[filtered_motos['tipo'].str.lower().isin(['naked', 'adventure'])]

            filtered_motos = filtered_motos[
                (filtered_motos['precio'] >= presupuesto_min) & 
                (filtered_motos['precio'] <= presupuesto_max)
            ]

            if experiencia == 'inexperto':
                filtered_motos = filtered_motos[filtered_motos['potencia'] <= 400]
            elif experiencia == 'avanzado':
                filtered_motos = filtered_motos[filtered_motos['potencia'] > 400]

            results = []
            for _, moto in filtered_motos.iterrows():
                score = 1.0
                reasons = ["Cumple tus preferencias básicas"]

                if uso_previsto == 'ciudad' and moto['tipo'].lower() in ['naked', 'scooter']:
                    score += 0.3
                    reasons.append("Ideal para uso en ciudad")
                elif uso_previsto == 'carretera' and moto['tipo'].lower() in ['sport', 'touring']:
                    score += 0.3
                    reasons.append("Ideal para carretera")
                elif uso_previsto == 'mixto' and moto['tipo'].lower() in ['naked', 'adventure']:
                    score += 0.3
                    reasons.append("Versátil para uso mixto")

                if experiencia == 'inexperto' and moto['potencia'] <= 400:
                    score += 0.2
                    reasons.append("Potencia adecuada para principiantes")
                elif experiencia == 'avanzado' and moto['potencia'] > 400:
                    score += 0.2
                    reasons.append("Alta potencia para tu experiencia")

                results.append({
                    'moto_id': str(moto.get('moto_id', moto.get('id', ''))),
                    'score': score,
                    'reasons': reasons,
                    'method': 'content',
                    'moto_data': moto.to_dict()
                })

            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_n]

        except Exception as e:
            self.logger.error(f"Error en recomendaciones basadas en contenido: {str(e)}")
            return []
    
    def _knowledge_based_recommendations(self, preferences: Dict, top_n: int) -> List[Dict]:
        """Genera recomendaciones personalizadas basadas en preferencias específicas del test."""
        logger.info(f"Calculando recomendaciones con preferencias: {preferences}")

        # Extraer parámetros de preferencias
        marcas_preferidas = preferences.get('marcas', {})
        estilos_preferidos = preferences.get('estilos', {})

        # Extraer rangos específicos con tolerancia del 10%
        presupuesto_min = float(preferences.get('presupuesto_min', 0))
        presupuesto_max = float(preferences.get('presupuesto_max', 100000))
        cilindrada_min = float(preferences.get('cilindrada_min', 0))
        cilindrada_max = float(preferences.get('cilindrada_max', 2000))
        potencia_min = float(preferences.get('potencia_min', 0))
        potencia_max = float(preferences.get('potencia_max', 300))
        torque_min = float(preferences.get('torque_min', 0))
        torque_max = float(preferences.get('torque_max', 200))
        peso_min = float(preferences.get('peso_min', 0))
        peso_max = float(preferences.get('peso_max', 500))
        ano_min = int(preferences.get('ano_min', 2000))
        ano_max = int(preferences.get('ano_max', 2025))

        # Aplicar tolerancia del 10% a los rangos
        tolerancia = 0.10
        presupuesto_min_tolerancia = presupuesto_min * (1 - tolerancia)
        presupuesto_max_tolerancia = presupuesto_max * (1 + tolerancia)
        cilindrada_min_tolerancia = cilindrada_min * (1 - tolerancia)
        cilindrada_max_tolerancia = cilindrada_max * (1 + tolerancia)
        potencia_min_tolerancia = potencia_min * (1 - tolerancia)
        potencia_max_tolerancia = potencia_max * (1 + tolerancia)
        torque_min_tolerancia = torque_min * (1 - tolerancia)
        torque_max_tolerancia = torque_max * (1 + tolerancia)
        peso_min_tolerancia = peso_min * (1 - tolerancia)
        peso_max_tolerancia = peso_max * (1 + tolerancia)

        logger.info(f"Filtros aplicados con 10% tolerancia:")
        logger.info(f"Presupuesto: {presupuesto_min_tolerancia:.0f} - {presupuesto_max_tolerancia:.0f}")
        logger.info(f"Cilindrada: {cilindrada_min_tolerancia:.0f} - {cilindrada_max_tolerancia:.0f}")
        logger.info(f"Potencia: {potencia_min_tolerancia:.0f} - {potencia_max_tolerancia:.0f}")
        logger.info(f"Torque: {torque_min_tolerancia:.0f} - {torque_max_tolerancia:.0f}")
        logger.info(f"Peso: {peso_min_tolerancia:.0f} - {peso_max_tolerancia:.0f}")

        filtered_motos = self.motos_df.copy()

        # PASO 1: FILTROS DE PREFERENCIAS (PRIORIDAD ALTA)
        if estilos_preferidos:
            estilo_filter = filtered_motos['tipo'].str.lower().isin(estilos_preferidos.keys())
            filtered_motos = filtered_motos[estilo_filter]
            logger.info(f"Después de filtro por estilo {list(estilos_preferidos.keys())}: {len(filtered_motos)} motos")
            if filtered_motos.empty:
                logger.warning(f"No hay motos del estilo preferido. Relajando filtro de estilo...")
                filtered_motos = self.motos_df.copy()

        if marcas_preferidas and not filtered_motos.empty:
            marca_filter = filtered_motos['marca'].isin(marcas_preferidas.keys())
            filtered_motos_marca = filtered_motos[marca_filter]
            if not filtered_motos_marca.empty:
                filtered_motos = filtered_motos_marca
                logger.info(f"Después de filtro por marca {list(marcas_preferidas.keys())}: {len(filtered_motos)} motos")
            else:
                logger.warning(f"No hay motos de la marca preferida en el estilo elegido. Manteniendo filtro de estilo...")

        # PASO 2: FILTROS TÉCNICOS (aplicar después de preferencias)
        filtered_motos = filtered_motos[
            (filtered_motos['precio'] >= presupuesto_min_tolerancia) &
            (filtered_motos['precio'] <= presupuesto_max_tolerancia)
        ]
        if 'cilindrada' in filtered_motos.columns:
            filtered_motos = filtered_motos[
                (filtered_motos['cilindrada'] >= cilindrada_min_tolerancia) &
                (filtered_motos['cilindrada'] <= cilindrada_max_tolerancia)
            ]
        if 'potencia' in filtered_motos.columns:
            filtered_motos = filtered_motos[
                (filtered_motos['potencia'] >= potencia_min_tolerancia) &
                (filtered_motos['potencia'] <= potencia_max_tolerancia)
            ]
        if 'torque' in filtered_motos.columns:
            filtered_motos = filtered_motos[
                (filtered_motos['torque'] >= torque_min_tolerancia) &
                (filtered_motos['torque'] <= torque_max_tolerancia)
            ]
        if 'anio' in filtered_motos.columns:
            filtered_motos = filtered_motos[
                (filtered_motos['anio'] >= ano_min) &
                (filtered_motos['anio'] <= ano_max)
            ]
        if 'peso' in filtered_motos.columns:
            filtered_motos = filtered_motos[
                (filtered_motos['peso'] >= peso_min_tolerancia) &
                (filtered_motos['peso'] <= peso_max_tolerancia)
            ]
            logger.info(f"Motos que cumplen TODOS los filtros (preferencias + técnicos): {len(filtered_motos)} de {len(self.motos_df)}")
        if filtered_motos.empty:
            logger.warning(f"No hay motos que cumplan TODOS los filtros. Aplicando filtros relajados...")

            # FILTROS RELAJADOS: Mantener preferencias de estilo/marca pero relajar especificaciones técnicas
            filtered_motos = self.motos_df.copy()
            if estilos_preferidos:
                estilo_filter = filtered_motos['tipo'].str.lower().isin(estilos_preferidos.keys())
                filtered_motos = filtered_motos[estilo_filter]
                logger.info(f"Filtros relajados - Manteniendo filtro de estilo: {len(filtered_motos)} motos")
                if filtered_motos.empty:
                    logger.warning(f"Sin motos del estilo preferido. Expandiendo búsqueda...")
                    filtered_motos = self.motos_df.copy()
            if marcas_preferidas and not filtered_motos.empty:
                marca_filter = filtered_motos['marca'].isin(marcas_preferidas.keys())
                filtered_motos_marca = filtered_motos[marca_filter]
                if not filtered_motos_marca.empty:
                    filtered_motos = filtered_motos_marca
                    logger.info(f"Filtros relajados - Manteniendo filtro de marca: {len(filtered_motos)} motos")

            # Aplicar solo los filtros técnicos más importantes con mayor tolerancia (30%)
            tolerancia_relajada = 0.30
            presupuesto_min_rel = presupuesto_min * (1 - tolerancia_relajada)
            presupuesto_max_rel = presupuesto_max * (1 + tolerancia_relajada)
            cilindrada_min_rel = cilindrada_min * (1 - tolerancia_relajada)
            cilindrada_max_rel = cilindrada_max * (1 + tolerancia_relajada)

            logger.info(f"Filtros relajados con 30% tolerancia:")
            logger.info(f"Presupuesto: {presupuesto_min_rel:.0f} - {presupuesto_max_rel:.0f}")
            logger.info(f"Cilindrada: {cilindrada_min_rel:.0f} - {cilindrada_max_rel:.0f}")

            if 'cilindrada' in filtered_motos.columns:
                filtered_motos = filtered_motos[
                    (filtered_motos['cilindrada'] >= cilindrada_min_rel) &
                    (filtered_motos['cilindrada'] <= cilindrada_max_rel)
                ]
            if filtered_motos.empty:
                logger.warning(f"No hay motos que cumplan filtros relajados. Intentando solo con preferencias...")
                filtered_motos = self.motos_df.copy()
                if estilos_preferidos:
                    estilo_filter = filtered_motos['tipo'].str.lower().isin(estilos_preferidos.keys())
                    filtered_motos = filtered_motos[estilo_filter]
                    logger.info(f"Solo filtro de estilo: {len(filtered_motos)} motos")
                if marcas_preferidas and not filtered_motos.empty:
                    marca_filter = filtered_motos['marca'].isin(marcas_preferidas.keys())
                    filtered_motos_marca = filtered_motos[marca_filter]
                    if not filtered_motos_marca.empty:
                        filtered_motos = filtered_motos_marca
                        logger.info(f"Solo filtros de preferencias (estilo + marca): {len(filtered_motos)} motos")
                if filtered_motos.empty:
                    logger.warning(f"No hay motos que cumplan las preferencias. Usando top motos populares.")
                    if 'popularity' in self.motos_df.columns:
                        filtered_motos = self.motos_df.sort_values('popularity', ascending=False).head(top_n)
                    else:
                        filtered_motos = self.motos_df.head(top_n)
                    logger.info(f"Seleccionadas {len(filtered_motos)} motos populares como recomendación de respaldo")
                else:
                    logger.info(f"Usando solo filtros de preferencias: {len(filtered_motos)} motos")
            else:
                logger.info(f"Motos que cumplen filtros relajados (preferencias + técnicos relajados): {len(filtered_motos)} de {len(self.motos_df)}")

        # Calcular score para cada moto que cumple los filtros
        results = []
        for _, moto in filtered_motos.iterrows():
            score = 0  
            reasons = []

            # Bonus por anio
            if 'anio' in moto:
                anio = moto['anio']
                if anio >= ano_min and anio <= ano_max:
                    score += 1
                    reasons.append(f"Año dentro de tu rango")

            # Bonus por cilindrada
            if 'cilindrada' in moto:
                cilindrada = moto['cilindrada']
                if cilindrada >= cilindrada_min and cilindrada <= cilindrada_max:
                    score += 1
                    reasons.append(f"Cilindrada dentro de tu rango")

            # Bonus por marca preferida
            if 'marca' in moto and marcas_preferidas:
                marca = str(moto['marca'])
                if marca in marcas_preferidas:
                    nivel = marcas_preferidas[marca]
                    score += nivel
                    reasons.append(f"Marca entre tus preferidas")

            # Bonus por peso
            if 'peso' in moto:
                peso = moto['peso']
                if peso >= peso_min and peso <= peso_max:
                    score += 1
                    reasons.append(f"Peso dentro de tu rango")

            # Bonus por potencia
            if 'potencia' in moto:
                potencia = moto['potencia']
                if potencia >= potencia_min and potencia <= potencia_max:
                    score += 1
                    reasons.append(f"Potencia dentro de tu rango")

            # Bonus por presupuesto
            if 'precio' in moto:
                precio = moto['precio']
                if precio >= presupuesto_min or precio <= presupuesto_max:

                    score += 1  # Bonus si está dentro del rango
                    reasons.append(f"Precio dentro de tu rango")
                    
            # Bonus por preferencias de estilo
            if 'tipo' in moto and estilos_preferidos:
                tipo = str(moto['tipo']).lower()
                if tipo in estilos_preferidos:
                    nivel = estilos_preferidos[tipo]
                    score += nivel
                    reasons.append(f"Estilo entre tus preferidos")

            # Bonus por torque
            if 'torque' in moto:
                torque = moto['torque']
                if torque >= torque_min and torque <= torque_max:
                    score += 1
                    reasons.append(f"Torque dentro de tu rango")

            # Formato igual a _popularity_based_recommendations
            results.append({
                'moto_id': str(moto.get('moto_id', moto.get('id', ''))),
                'score': score,
                'reasons': reasons,
                'method': 'knowledge',
                'moto_data': moto.to_dict()
            })

            print(f"Recomendación: {moto['marca']} {moto['modelo']} - Score: {score:.2f}")

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:10]

    def _popularity_based_recommendations(self, top_n: int) -> List[Dict]:
        """Recomendaciones basadas en popularidad general (normalizado a 1.0)"""
        if self.interactions_df is None:
            return []
        
        # Calcular popularidad por número de interacciones
        popularity = self.interactions_df.groupby('moto_id').agg({
            'weight': 'sum',
            'user_id': 'count'
        }).reset_index()
        
        popularity['popularity_score'] = popularity['weight'] + (popularity['user_id'] * 0.5)
        popularity = popularity.sort_values('popularity_score', ascending=False)
        
        # Normalizar: la moto más popular tiene score 1.0, el resto es porcentaje respecto a la más popular
        max_score = popularity['popularity_score'].max() if not popularity.empty else 1.0
        if max_score == 0:
            max_score = 1.0  # Evitar división por cero
        
        popularity['normalized_score'] = popularity['popularity_score'] / max_score
        
        result = []
        for _, row in popularity.head(top_n).iterrows():
            moto_data = self.motos_df[self.motos_df['id'] == row['moto_id']]
            if not moto_data.empty:
                result.append({
                    'moto_id': row['moto_id'],
                    'score': row['normalized_score'],
                    'reasons': [f"Popularidad: {row['normalized_score']:.2%} respecto a la más popular"],
                    'method': 'popularity',
                    'moto_data': moto_data.iloc[0].to_dict()
                })
        
        return result
    
    def _combine_and_diversify_recommendations(self, content_recs, 
                                             knowledge_recs, popularity_recs, 
                                             user_id, preferences, top_n):
        """Combina recomendaciones de diferentes métodos y asegura diversidad"""
        
        all_recommendations = {}
        
        # Usa los pesos definidos en self.weights
        for recs, method in zip(
            [content_recs, knowledge_recs, popularity_recs],
            ['content', 'knowledge', 'popularity']
        ):
            weight = self.weights[method]
            for rec in recs:
                moto_id = rec['moto_id']
                if moto_id not in all_recommendations:
                    all_recommendations[moto_id] = {
                        'combined_score': 0.0,
                        'methods': [],
                        'all_reasons': [],
                        'moto_data': rec.get('moto_data', {})
                    }
                all_recommendations[moto_id]['combined_score'] += rec['score'] * weight
                all_recommendations[moto_id]['methods'].append(rec.get('method', 'unknown'))
                all_recommendations[moto_id]['all_reasons'].extend(rec.get('reasons', []))
        
        # Agregar factor de exploración vs explotación
        all_recommendations = self._add_exploration_factor(all_recommendations, user_id)
        
        # Ordenar por score combinado
        sorted_recs = sorted(all_recommendations.items(), 
                           key=lambda x: x[1]['combined_score'], reverse=True)
        
        # Asegurar diversidad en el resultado final
        final_recs = self._ensure_final_diversity(sorted_recs, top_n)
        
        return final_recs
    
    
    def _add_exploration_factor(self, recommendations, user_id):
        """Añade factor de exploración para mostrar opciones nuevas"""
        
        # Obtener motos ya vistas por el usuario
        seen_motos = set()
        if self.interactions_df is not None:
            user_interactions = self.interactions_df[self.interactions_df['user_id'] == user_id]
            seen_motos = set(user_interactions['moto_id'].tolist())
        
        # Dar boost a motos no vistas (exploración)
        for moto_id, rec in recommendations.items():
            if moto_id not in seen_motos:
                rec['combined_score'] *= 1.1  # 10% de boost por exploración
                rec['all_reasons'].append("Nueva opción para explorar")
        
        return recommendations
    
    
    def _ensure_final_diversity(self, sorted_recs, top_n):
        """Asegura diversidad en el resultado final y agrega porcentaje de score"""
        
        final_results = []
        used_marcas = {}
        used_tipos = {}
        
        # Score máximo teórico (ajusta si cambias los pesos)
        SCORE_MAX = self.score_max

        print(f"Score máximo teórico: {SCORE_MAX}")
        
        # Primera pasada: seleccionar diversas opciones
        for moto_id, rec_data in sorted_recs:
            if len(final_results) >= top_n:
                break
                
            moto_data = rec_data['moto_data']
            marca = moto_data.get('marca', '')
            tipo = moto_data.get('tipo', '').lower()
            
            marca_count = used_marcas.get(marca, 0)
            tipo_count = used_tipos.get(tipo, 0)

            # Permitir máximo 3 motos por marca y 3 por tipo
            if marca_count < 3 and tipo_count < 3:
                score = rec_data['combined_score']
                porcentaje = min((score / SCORE_MAX), 1)
                final_results.append({
                    'moto_id': moto_id,
                    'score': round(porcentaje, 2),
                    'marca': moto_data.get('marca', ''),
                    'modelo': moto_data.get('modelo', ''),
                    'tipo': moto_data.get('tipo', ''),
                    'precio': moto_data.get('precio', 0),
                    'cilindrada': moto_data.get('cilindrada', 0),
                    'imagen': moto_data.get('imagen', ''),
                    'methods_used': list(set(rec_data['methods'])),
                    'reasons': ' | '.join(list(set(rec_data['all_reasons']))),
                    'details': moto_data,
                    'anio': moto_data.get('anio', ''),
                    'torque': moto_data.get('torque', 0),
                    'potencia': moto_data.get('potencia', 0),
                    'url': moto_data.get('url', '')
                })
                # Sumar 1 al contador solo cuando se agrega la moto
                used_marcas[marca] = marca_count + 1
                used_tipos[tipo] = tipo_count + 1

            else: 
                
                print(f"Marca {marca} y tipo {tipo} ya alcanzaron el límite de 3 motos. Saltando moto {moto_id}")
                print(f"Contadores actuales - Marcas: {used_marcas}, Tipos: {used_tipos}")
        
        # Segunda pasada: llenar espacios restantes si es necesario
        if len(final_results) < top_n:
            for moto_id, rec_data in sorted_recs:
                if len(final_results) >= top_n:
                    break
                    
                # Si no está ya en los resultados, agregarlo
                if not any(r['moto_id'] == moto_id for r in final_results):
                    moto_data = rec_data['moto_data']
                    score = rec_data['combined_score']
                    porcentaje = min((score / SCORE_MAX), 1)
                    final_results.append({
                        'moto_id': moto_id,
                        'score': score,
                        'marca': moto_data.get('marca', ''),
                        'modelo': moto_data.get('modelo', ''),
                        'tipo': moto_data.get('tipo', ''),
                        'precio': moto_data.get('precio', 0),
                        'cilindrada': moto_data.get('cilindrada', 0),
                        'imagen': moto_data.get('imagen', ''),
                        'methods_used': list(set(rec_data['methods'])),
                        'reasons': ', '.join(list(set(rec_data['all_reasons']))),
                        'details': moto_data,
                        'anio': moto_data.get('anio', ''),
                        'torque': moto_data.get('torque', 0),
                        'potencia': moto_data.get('potencia', 0),
                        'url': moto_data.get('url', '')
                    })
                    # Sumar 1 al contador solo cuando se agrega la moto
                    marca = moto_data.get('marca', '')
                    tipo = moto_data.get('tipo', '').lower()
                    used_marcas[marca] = used_marcas.get(marca, 0) + 1
                    used_tipos[tipo] = used_tipos.get(tipo, 0) + 1
        
        return final_results
