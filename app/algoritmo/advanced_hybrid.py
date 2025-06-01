"""
Sistema de Recomendación Híbrido Avanzado para Motos.
Este módulo implementa un algoritmo de recomendación de última generación que combina
múltiples técnicas de aprendizaje automático para proporcionar recomendaciones precisas.
"""
import numpy as np
import pandas as pd
from collections import defaultdict
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Dense, Dropout, Input, Embedding, Flatten, Concatenate
from tensorflow.keras.optimizers import Adam
import pickle
import os
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedHybridRecommender:
    """
    Sistema de recomendación híbrido avanzado que combina:
    - Filtrado colaborativo con factorización matricial
    - Redes neuronales profundas
    - Modelos basados en contenido
    - Factores contextuales
    - Técnicas de ranking avanzadas
    """
    def __init__(self, config=None):
        """
        Inicializa el recomendador avanzado.
        
        Args:
            config (dict): Configuración del recomendador con parámetros como:
                - learning_rate: Tasa de aprendizaje para modelos de deep learning
                - regularization: Factor de regularización para modelos de factorización
                - embedding_size: Tamaño de los embeddings para redes neuronales
                - hidden_layers: Estructura de capas ocultas para redes neuronales
                - epochs: Número de épocas para entrenamiento
                - batch_size: Tamaño de lote para entrenamiento
                - contextual_weight: Peso de los factores contextuales
        """
        # Configuración predeterminada
        self.config = {
            'learning_rate': 0.001,
            'regularization': 0.01,
            'embedding_size': 50,
            'hidden_layers': [128, 64, 32],
            'epochs': 20,
            'batch_size': 64,
            'contextual_weight': 0.3,
            'feature_weight': 0.4,
            'collaborative_weight': 0.3,
            'model_path': 'models/'
        }
        
        # Actualizar con configuración proporcionada
        if config:
            self.config.update(config)
            
        # Inicializar modelos y datos
        self.user_features = None
        self.moto_features = None
        self.ratings_matrix = None
        self.interaction_matrix = None
        self.user_embeddings = None
        self.moto_embeddings = None
        self.mfm_model = None  # Modelo de factorización matricial
        self.nn_model = None   # Modelo de red neuronal
        self.moto_feature_model = None  # Modelo basado en características
        self.feature_scalers = {}  # Escaladores para características
        self.is_trained = False
        
        # Crear directorio para modelos si no existe
        if not os.path.exists(self.config['model_path']):
            os.makedirs(self.config['model_path'])
    
    def load_data(self, user_features, moto_features, user_interactions, user_context=None):
        """
        Carga y preprocesa los datos para el entrenamiento de los modelos.
        
        Args:
            user_features (pandas.DataFrame): Características de los usuarios
            moto_features (pandas.DataFrame): Características de las motos
            user_interactions (pandas.DataFrame): Interacciones usuario-moto (valoraciones, vistas, etc.)
            user_context (pandas.DataFrame, optional): Datos contextuales de usuarios (hora, ubicación, etc.)
        """
        logger.info("Cargando y preprocesando datos...")
        
        # Almacenar datos originales
        self.user_features_raw = user_features.copy()
        self.moto_features_raw = moto_features.copy()
        self.user_interactions_raw = user_interactions.copy()
        self.user_context_raw = user_context.copy() if user_context is not None else None
        
        # Preprocesar características de usuario
        self.user_features = self._preprocess_user_features(user_features)
        
        # Preprocesar características de motos
        self.moto_features = self._preprocess_moto_features(moto_features)
        
        # Construir matrices de interacción
        self._build_interaction_matrices(user_interactions)
        
        # Procesar datos contextuales si están disponibles
        if user_context is not None:
            self.user_context = self._preprocess_context_data(user_context)
        else:
            self.user_context = None
            
        logger.info("Datos cargados y preprocesados con éxito")
        
    def _preprocess_user_features(self, user_features):
        """
        Preprocesa las características de los usuarios.
        
        Args:
            user_features (pandas.DataFrame): Características de los usuarios
            
        Returns:
            pandas.DataFrame: Características preprocesadas
        """
        df = user_features.copy()
        
        # Asegurarse de que user_id sea el índice
        if 'user_id' in df.columns:
            df = df.set_index('user_id')
            
        # Identificar columnas numéricas y categóricas
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        
        # Escalar características numéricas
        for col in numeric_cols:
            scaler = StandardScaler()
            df[col] = scaler.fit_transform(df[[col]])
            self.feature_scalers[f'user_{col}'] = scaler
            
        # Codificar características categóricas
        df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)
        
        return df
    
    def _preprocess_moto_features(self, moto_features):
        """
        Preprocesa las características de las motos.
        
        Args:
            moto_features (pandas.DataFrame): Características de las motos
            
        Returns:
            pandas.DataFrame: Características preprocesadas
        """
        df = moto_features.copy()
        
        # Asegurarse de que moto_id sea el índice
        if 'moto_id' in df.columns:
            df = df.set_index('moto_id')
            
        # Identificar columnas numéricas y categóricas
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        
        # Escalar características numéricas
        for col in numeric_cols:
            scaler = MinMaxScaler()  # Normalización Min-Max para características de motos
            df[col] = scaler.fit_transform(df[[col]])
            self.feature_scalers[f'moto_{col}'] = scaler
            
        # Codificar características categóricas
        df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)
        
        return df
    
    def _preprocess_context_data(self, context_data):
        """
        Preprocesa los datos contextuales.
        
        Args:
            context_data (pandas.DataFrame): Datos contextuales
            
        Returns:
            pandas.DataFrame: Datos contextuales preprocesados
        """
        df = context_data.copy()
        
        # Procesamiento específico para datos temporales
        if 'timestamp' in df.columns:
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            df['month'] = pd.to_datetime(df['timestamp']).dt.month
            df = df.drop('timestamp', axis=1)
            
        # Procesamiento para datos de geolocalización
        if 'latitude' in df.columns and 'longitude' in df.columns:
            # Aquí se podrían implementar técnicas de clustering geográfico
            # Por simplicidad, solo escalaremos los valores
            scaler = MinMaxScaler()
            df[['latitude', 'longitude']] = scaler.fit_transform(df[['latitude', 'longitude']])
            self.feature_scalers['geo'] = scaler
            
        return df
    
    def _build_interaction_matrices(self, interactions):
        """
        Construye matrices de interacción usuario-moto.
        
        Args:
            interactions (pandas.DataFrame): Datos de interacciones
        """
        # Crear mapeos de IDs a índices
        unique_users = interactions['user_id'].unique()
        unique_motos = interactions['moto_id'].unique()
        
        self.user_map = {user: i for i, user in enumerate(unique_users)}
        self.moto_map = {moto: i for i, moto in enumerate(unique_motos)}
        self.inv_user_map = {i: user for user, i in self.user_map.items()}
        self.inv_moto_map = {i: moto for moto, i in self.moto_map.items()}
        
        # Crear matriz de valoraciones si existe la columna 'rating'
        if 'rating' in interactions.columns:
            # Pivot table para matriz de valoraciones
            self.ratings_df = interactions.pivot_table(
                index='user_id', 
                columns='moto_id', 
                values='rating',
                fill_value=0
            )
            
            # Convertir a matriz dispersa para eficiencia
            self.ratings_matrix = csr_matrix(self.ratings_df.values)
            
        # Crear matriz de interacciones generales (vistas, clicks, etc.)
        if 'interaction_type' in interactions.columns and 'weight' in interactions.columns:
            # Agregar por usuario, moto y tipo de interacción
            agg_interactions = interactions.groupby(['user_id', 'moto_id', 'interaction_type'])['weight'].sum().reset_index()
            
            # Pivotar para tener tipos de interacción como columnas
            interaction_pivot = agg_interactions.pivot_table(
                index=['user_id', 'moto_id'], 
                columns='interaction_type', 
                values='weight',
                fill_value=0
            ).reset_index()
            
            # Simplificar a una puntuación ponderada de interacción
            # (esto podría ser más sofisticado en una implementación real)
            interaction_weights = {
                'view': 1,
                'click': 2,
                'favorite': 3,
                'purchase': 5
            }
            
            # Aplicar pesos a cada tipo de interacción
            for int_type, weight in interaction_weights.items():
                if int_type in interaction_pivot.columns:
                    interaction_pivot[int_type] = interaction_pivot[int_type] * weight
            
            # Suma ponderada de interacciones
            interaction_pivot['total_weighted'] = interaction_pivot.drop(['user_id', 'moto_id'], axis=1).sum(axis=1)
            
            # Crear matriz de interacciones
            interaction_matrix_df = interaction_pivot.pivot_table(
                index='user_id', 
                columns='moto_id', 
                values='total_weighted',
                fill_value=0
            )
            
            self.interaction_matrix = csr_matrix(interaction_matrix_df.values)
            self.interaction_df = interaction_matrix_df
        
    def train_models(self):
        """
        Entrena todos los modelos de recomendación.
        """
        logger.info("Iniciando entrenamiento de los modelos...")
        
        # Entrenar modelo de factorización matricial
        self._train_matrix_factorization()
        
        # Entrenar modelo de red neuronal profunda
        self._train_neural_network()
        
        # Entrenar modelo basado en características
        self._train_feature_based_model()
        
        self.is_trained = True
        logger.info("Entrenamiento de modelos completado")
        
    def _train_matrix_factorization(self):
        """
        Entrena un modelo de factorización matricial para filtrado colaborativo.
        """
        logger.info("Entrenando modelo de factorización matricial...")
        
        # Usar la matriz de valoraciones o interacciones según disponibilidad
        matrix = self.ratings_matrix if hasattr(self, 'ratings_matrix') else self.interaction_matrix
        
        if matrix is None:
            logger.warning("No hay datos de interacción para entrenar el modelo de factorización matricial")
            return
            
        # Dimensión de latent factors
        k = self.config['embedding_size']
        
        # Aplicar SVD
        U, sigma, Vt = svds(matrix, k=k)
        
        # Ajustar los valores singulares como matriz diagonal
        sigma_diag = np.diag(sigma)
        
        # Calcular predicciones base
        self.mfm_predictions = U.dot(sigma_diag).dot(Vt)
        
        # Guardar embeddings para uso posterior
        self.user_embeddings = U
        self.moto_embeddings = Vt.T
        
        # Guardar modelo
        model_data = {
            'user_embeddings': self.user_embeddings,
            'moto_embeddings': self.moto_embeddings,
            'sigma': sigma_diag,
            'user_map': self.user_map,
            'moto_map': self.moto_map
        }
        
        with open(os.path.join(self.config['model_path'], 'mfm_model.pkl'), 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info("Modelo de factorización matricial entrenado y guardado")
        
    def _train_neural_network(self):
        """
        Entrena un modelo de red neuronal profunda para capturar patrones complejos.
        """
        logger.info("Entrenando modelo de red neuronal profunda...")
        
        # Verificar si hay suficientes datos
        if not hasattr(self, 'ratings_df') and not hasattr(self, 'interaction_df'):
            logger.warning("No hay datos de interacción para entrenar la red neuronal")
            return
            
        # Usar valoraciones o interacciones según disponibilidad
        if hasattr(self, 'ratings_df'):
            interactions_df = self.ratings_df.reset_index()
            value_col = 'rating'
        else:
            interactions_df = self.interaction_df.reset_index()
            value_col = 'total_weighted'
            
        # Preparar datos para el entrenamiento
        train_data = []
        
        for _, row in interactions_df.iterrows():
            user_id = row['user_id']
            for col in interactions_df.columns:
                if col != 'user_id' and row[col] > 0:
                    moto_id = col
                    value = row[col]
                    
                    # Agregar características de usuario y moto si están disponibles
                    user_features = []
                    if self.user_features is not None and user_id in self.user_features.index:
                        user_features = self.user_features.loc[user_id].values.tolist()
                        
                    moto_features = []
                    if self.moto_features is not None and moto_id in self.moto_features.index:
                        moto_features = self.moto_features.loc[moto_id].values.tolist()
                        
                    # Añadir a datos de entrenamiento
                    train_data.append({
                        'user_id': self.user_map.get(user_id, -1),
                        'moto_id': self.moto_map.get(moto_id, -1),
                        'value': value,
                        'user_features': user_features,
                        'moto_features': moto_features
                    })
        
        if not train_data:
            logger.warning("No hay datos de entrenamiento para la red neuronal")
            return
            
        # Verificar que hay mapeos válidos
        valid_data = [d for d in train_data if d['user_id'] != -1 and d['moto_id'] != -1]
        
        if not valid_data:
            logger.warning("No hay mapeos válidos de usuarios/motos para entrenar la red neuronal")
            return
            
        # Preparar tensores para entrenamiento
        num_users = len(self.user_map)
        num_motos = len(self.moto_map)
        
        user_ids = np.array([d['user_id'] for d in valid_data])
        moto_ids = np.array([d['moto_id'] for d in valid_data])
        values = np.array([d['value'] for d in valid_data])
        
        # Normalizar valores
        values_scaler = MinMaxScaler()
        values = values_scaler.fit_transform(values.reshape(-1, 1)).flatten()
        self.feature_scalers['values'] = values_scaler
        
        # Construir modelo de red neuronal
        # Input layers
        user_input = Input(shape=(1,), name='user_input')
        moto_input = Input(shape=(1,), name='moto_input')
        
        # Embedding layers
        user_embedding = Embedding(num_users, self.config['embedding_size'], name='user_embedding')(user_input)
        moto_embedding = Embedding(num_motos, self.config['embedding_size'], name='moto_embedding')(moto_input)
        
        # Flatten embeddings
        user_vec = Flatten()(user_embedding)
        moto_vec = Flatten()(moto_embedding)
        
        # Agregar capas para características si están disponibles
        inputs = [user_input, moto_input]
        vectors = [user_vec, moto_vec]
        
        # Características de usuario
        if valid_data[0]['user_features']:
            user_feat_dim = len(valid_data[0]['user_features'])
            user_feat_input = Input(shape=(user_feat_dim,), name='user_feat_input')
            inputs.append(user_feat_input)
            vectors.append(user_feat_input)
            
            # Preparar tensor de características de usuario
            user_features_array = np.array([d['user_features'] for d in valid_data])
        else:
            user_features_array = None
            
        # Características de moto
        if valid_data[0]['moto_features']:
            moto_feat_dim = len(valid_data[0]['moto_features'])
            moto_feat_input = Input(shape=(moto_feat_dim,), name='moto_feat_input')
            inputs.append(moto_feat_input)
            vectors.append(moto_feat_input)
            
            # Preparar tensor de características de moto
            moto_features_array = np.array([d['moto_features'] for d in valid_data])
        else:
            moto_features_array = None
            
        # Concatenar todas las entradas
        concat = Concatenate()(vectors)
        
        # Capas ocultas
        dense = concat
        for i, units in enumerate(self.config['hidden_layers']):
            dense = Dense(units, activation='relu', name=f'dense_{i}')(dense)
            dense = Dropout(0.2)(dense)  # Regularización dropout
            
        # Capa de salida
        output = Dense(1, activation='linear', name='output')(dense)
        
        # Compilar modelo
        model = Model(inputs=inputs, outputs=output)
        model.compile(
            optimizer=Adam(learning_rate=self.config['learning_rate']),
            loss='mean_squared_error'
        )
        
        # Preparar datos de entrenamiento
        train_inputs = [user_ids, moto_ids]
        
        if user_features_array is not None:
            train_inputs.append(user_features_array)
        
        if moto_features_array is not None:
            train_inputs.append(moto_features_array)
        
        # Entrenar modelo
        model.fit(
            train_inputs, 
            values,
            epochs=self.config['epochs'],
            batch_size=self.config['batch_size'],
            verbose=1,
            validation_split=0.1
        )
        
        # Guardar modelo
        self.nn_model = model
        model.save(os.path.join(self.config['model_path'], 'nn_model'))
        
        logger.info("Modelo de red neuronal entrenado y guardado")
        
    def _train_feature_based_model(self):
        """
        Entrena un modelo basado en características para filtrado basado en contenido.
        """
        logger.info("Entrenando modelo basado en características...")
        
        # Verificar si hay características de motos
        if self.moto_features is None:
            logger.warning("No hay características de motos para entrenar el modelo basado en contenido")
            return
            
        # Calcular matriz de similitud entre motos basada en características
        self.moto_similarity = cosine_similarity(self.moto_features.values)
        
        # Guardar modelo
        model_data = {
            'moto_similarity': self.moto_similarity,
            'moto_features': self.moto_features,
            'moto_indices': {moto: i for i, moto in enumerate(self.moto_features.index)}
        }
        
        with open(os.path.join(self.config['model_path'], 'feature_model.pkl'), 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info("Modelo basado en características entrenado y guardado")
        
    def get_recommendations(self, user_id, context=None, top_n=10, diversity_factor=0.3):
        """
        Genera recomendaciones para un usuario utilizando todos los modelos entrenados.
        
        Args:
            user_id: ID del usuario
            context (dict, optional): Datos contextuales (hora, ubicación, etc.)
            top_n (int): Número de recomendaciones a generar
            diversity_factor (float): Factor para aumentar la diversidad (0-1)
            
        Returns:
            list: Lista de tuplas (moto_id, score, reasons) con recomendaciones
        """
        if not self.is_trained:
            logger.warning("Los modelos no han sido entrenados. Entrenando ahora...")
            self.train_models()
            
        # Obtener recomendaciones de cada modelo
        collab_recs = self._get_collaborative_recommendations(user_id, n=top_n*2)
        content_recs = self._get_content_based_recommendations(user_id, n=top_n*2)
        
        # Aplicar factores contextuales si están disponibles
        context_boost = {}
        if context is not None:
            context_boost = self._apply_contextual_factors(user_id, context, collab_recs + content_recs)
            
        # Combinar y ponderar recomendaciones
        all_recs = defaultdict(float)
        reasons = defaultdict(list)
        
        # Agregar recomendaciones colaborativas
        for moto_id, score in collab_recs:
            all_recs[moto_id] += score * self.config['collaborative_weight']
            reasons[moto_id].append("Basado en usuarios con gustos similares al tuyo")
            
        # Agregar recomendaciones basadas en contenido
        for moto_id, score, reason in content_recs:
            all_recs[moto_id] += score * self.config['feature_weight']
            reasons[moto_id].append(reason)
            
        # Aplicar boost contextual
        for moto_id, boost in context_boost.items():
            if moto_id in all_recs:
                all_recs[moto_id] += boost * self.config['contextual_weight']
                reasons[moto_id].append("Recomendado para tu contexto actual")
                
        # Aplicar factor de diversidad (exploración vs explotación)
        final_recs = self._apply_diversity(all_recs, diversity_factor)
        
        # Ordenar por puntuación
        sorted_recs = sorted(final_recs.items(), key=lambda x: x[1], reverse=True)
        
        # Preparar resultados con razones
        detailed_recs = []
        for moto_id, score in sorted_recs[:top_n]:
            # Obtener características de la moto
            moto_info = None
            if hasattr(self, 'moto_features_raw'):
                moto_index = self.moto_features_raw.index.get_loc(moto_id) if moto_id in self.moto_features_raw.index else None
                if moto_index is not None:
                    moto_info = self.moto_features_raw.iloc[moto_index]
            
            # Determinar razones principales
            moto_reasons = self._get_detailed_reasons(user_id, moto_id, moto_info, reasons[moto_id])
            
            detailed_recs.append((moto_id, score, moto_reasons))
            
        return detailed_recs
        
    def _get_collaborative_recommendations(self, user_id, n=10):
        """
        Obtiene recomendaciones basadas en filtrado colaborativo.
        
        Args:
            user_id: ID del usuario
            n (int): Número de recomendaciones a generar
            
        Returns:
            list: Lista de tuplas (moto_id, score)
        """
        # Verificar si el usuario está en el mapeo
        if user_id not in self.user_map:
            logger.warning(f"Usuario {user_id} no encontrado en los datos de entrenamiento")
            return []
            
        user_idx = self.user_map[user_id]
        
        # Obtener predicciones para este usuario
        user_predictions = self.mfm_predictions[user_idx]
        
        # Obtener ítems que el usuario no ha valorado/interactuado
        unrated_items = []
        
        if hasattr(self, 'ratings_df'):
            # Si tenemos ratings explícitos
            user_ratings = self.ratings_df.loc[user_id] if user_id in self.ratings_df.index else pd.Series()
            unrated_items = [(self.moto_map[moto_id], moto_id) 
                            for moto_id in self.moto_map.keys() 
                            if moto_id not in user_ratings or user_ratings[moto_id] == 0]
        else:
            # Si solo tenemos interacciones implícitas
            if hasattr(self, 'interaction_df') and user_id in self.interaction_df.index:
                user_interactions = self.interaction_df.loc[user_id]
                unrated_items = [(self.moto_map[moto_id], moto_id) 
                               for moto_id in self.moto_map.keys() 
                               if moto_id not in user_interactions or user_interactions[moto_id] == 0]
            else:
                # Si no hay datos del usuario, recomendar todos los ítems
                unrated_items = [(idx, self.inv_moto_map[idx]) for idx in range(len(self.inv_moto_map))]
        
        # Predecir puntuaciones
        predictions = [(moto_id, user_predictions[idx]) for idx, moto_id in unrated_items]
        
        # Ordenar por puntuación
        sorted_predictions = sorted(predictions, key=lambda x: x[1], reverse=True)
        
        return sorted_predictions[:n]
    
    def _get_content_based_recommendations(self, user_id, n=10):
        """
        Obtiene recomendaciones basadas en contenido.
        
        Args:
            user_id: ID del usuario
            n (int): Número de recomendaciones a generar
            
        Returns:
            list: Lista de tuplas (moto_id, score, reason)
        """
        # Verificar si tenemos características de motos
        if self.moto_features is None:
            logger.warning("No hay características de motos para recomendaciones basadas en contenido")
            return []
            
        # Obtener perfil del usuario
        user_profile = self._get_user_profile(user_id)
        if user_profile is None:
            logger.warning(f"No se pudo generar perfil para el usuario {user_id}")
            return []
            
        recommendations = []
        
        # Obtener items con los que el usuario ha interactuado
        user_items = []
        if hasattr(self, 'ratings_df') and user_id in self.ratings_df.index:
            user_ratings = self.ratings_df.loc[user_id]
            user_items = [(moto_id, rating) for moto_id, rating in user_ratings.items() if rating > 0]
        elif hasattr(self, 'interaction_df') and user_id in self.interaction_df.index:
            user_interactions = self.interaction_df.loc[user_id]
            user_items = [(moto_id, interaction) for moto_id, interaction in user_interactions.items() if interaction > 0]
            
        # Si no hay interacciones previas, usar perfil de usuario para recomendar
        if not user_items:
            # Calcular afinidad con cada moto basada en perfil
            for moto_id, moto_features in self.moto_features.iterrows():
                compatibility = self._calculate_profile_compatibility(user_profile, moto_features)
                reason = self._get_feature_based_reason(user_profile, moto_features)
                recommendations.append((moto_id, compatibility, reason))
        else:
            # Usar motos previamente valoradas para encontrar similares
            for moto_id, rating in sorted(user_items, key=lambda x: x[1], reverse=True)[:5]:
                if moto_id not in self.moto_features.index:
                    continue
                    
                # Encontrar motos similares
                moto_idx = self.moto_features.index.get_loc(moto_id)
                similarities = list(enumerate(self.moto_similarity[moto_idx]))
                
                for i, similarity in sorted(similarities, key=lambda x: x[1], reverse=True):
                    if similarity > 0.1:  # Umbral mínimo de similitud
                        similar_moto = self.moto_features.index[i]
                        
                        # Evitar recomendar la misma moto u otras ya valoradas
                        if similar_moto == moto_id or any(item[0] == similar_moto for item in user_items):
                            continue
                        
                        score = similarity * rating if rating else similarity
                        reason = self._get_similarity_reason(moto_id, similar_moto)
                        
                        # Agregar a recomendaciones o actualizar si ya existe con mayor score
                        existing = next((i for i, rec in enumerate(recommendations) if rec[0] == similar_moto), None)
                        if existing is not None:
                            if recommendations[existing][1] < score:
                                recommendations[existing] = (similar_moto, score, reason)
                        else:
                            recommendations.append((similar_moto, score, reason))
        
        # Ordenar por puntuación
        sorted_recs = sorted(recommendations, key=lambda x: x[1], reverse=True)
        
        return sorted_recs[:n]
    
    def _get_user_profile(self, user_id):
        """
        Obtiene o genera el perfil de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            dict: Perfil del usuario
        """
        profile = {}
        
        # Usar características explícitas si están disponibles
        if self.user_features is not None and user_id in self.user_features.index:
            profile['features'] = self.user_features.loc[user_id].to_dict()
            
        # Inferir preferencias basadas en interacciones previas
        item_preferences = {}
        
        # Preferencias basadas en valoraciones
        if hasattr(self, 'ratings_df') and user_id in self.ratings_df.index:
            user_ratings = self.ratings_df.loc[user_id]
            rated_items = [(moto_id, rating) for moto_id, rating in user_ratings.items() if rating > 0]
            
            # Normalizar ratings
            if rated_items:
                max_rating = max(rating for _, rating in rated_items)
                item_preferences = {moto_id: rating/max_rating for moto_id, rating in rated_items}
        
        # O preferencias basadas en interacciones
        elif hasattr(self, 'interaction_df') and user_id in self.interaction_df.index:
            user_interactions = self.interaction_df.loc[user_id]
            interacted_items = [(moto_id, interaction) for moto_id, interaction in user_interactions.items() if interaction > 0]
            
            # Normalizar interacciones
            if interacted_items:
                max_interaction = max(interaction for _, interaction in interacted_items)
                item_preferences = {moto_id: interaction/max_interaction for moto_id, interaction in interacted_items}
                
        profile['item_preferences'] = item_preferences
        
        # Si no hay suficiente información, devolver None
        if not profile.get('features') and not profile.get('item_preferences'):
            return None
            
        return profile
    
    def _calculate_profile_compatibility(self, user_profile, moto_features):
        """
        Calcula la compatibilidad entre un perfil de usuario y características de moto.
        
        Args:
            user_profile (dict): Perfil del usuario
            moto_features (pandas.Series): Características de la moto
            
        Returns:
            float: Puntuación de compatibilidad
        """
        compatibility = 0.0
        
        # Si tenemos características de usuario
        if 'features' in user_profile:
            user_features = user_profile['features']
            
            # Mapeo de características y pesos
            # Esto debe personalizarse según las características específicas disponibles
            feature_mapping = {
                # Experiencia -> potencia/cilindrada
                'experiencia_principiante': {'potencia': -0.8, 'cilindrada': -0.8},
                'experiencia_intermedio': {'potencia': 0.0, 'cilindrada': 0.0},
                'experiencia_experto': {'potencia': 0.8, 'cilindrada': 0.8},
                
                # Uso previsto -> tipo de moto
                'uso_previsto_urbano': {'tipo_scooter': 0.8, 'tipo_naked': 0.6, 'tipo_custom': 0.3},
                'uso_previsto_carretera': {'tipo_touring': 0.8, 'tipo_sport': 0.7, 'tipo_naked': 0.5},
                'uso_previsto_offroad': {'tipo_enduro': 0.9, 'tipo_cross': 0.8, 'tipo_trail': 0.6},
                
                # Presupuesto -> precio
                'presupuesto': {'precio': -0.5}  # Relación negativa (mayor presupuesto es mejor)
            }
            
            # Calcular compatibilidad basada en mapeos
            for user_feature, value in user_features.items():
                if user_feature in feature_mapping:
                    for moto_feature, weight in feature_mapping[user_feature].items():
                        if moto_feature in moto_features:
                            # Para características numéricas como presupuesto vs precio
                            if user_feature == 'presupuesto' and moto_feature == 'precio':
                                # Si el precio es mayor que el presupuesto, penalizar
                                if value < moto_features[moto_feature]:
                                    compatibility += weight * 0.5  # Penalización moderada
                                else:
                                    # Premiar si está en presupuesto, más si es económico
                                    compatibility += abs(weight) * (1 - moto_features[moto_feature]/value)
                            else:
                                # Para características categóricas
                                compatibility += value * weight * moto_features.get(moto_feature, 0)
                                
        # Ajustar escala
        compatibility = 1 / (1 + np.exp(-compatibility))  # Función sigmoide para normalizar
        
        return compatibility
    
    def _get_feature_based_reason(self, user_profile, moto_features):
        """
        Genera una razón explicativa basada en características.
        
        Args:
            user_profile (dict): Perfil del usuario
            moto_features (pandas.Series): Características de la moto
            
        Returns:
            str: Razón para la recomendación
        """
        reasons = []
        
        # Obtener características originales (no procesadas) si están disponibles
        moto_id = moto_features.name
        moto_orig = None
        
        if hasattr(self, 'moto_features_raw') and moto_id in self.moto_features_raw.index:
            moto_orig = self.moto_features_raw.loc[moto_id]
        
        # Generar razones basadas en compatibilidad de características
        if 'features' in user_profile and moto_orig is not None:
            user_features = user_profile['features']
            
            # Experiencia vs potencia
            if 'experiencia_principiante' in user_features and user_features['experiencia_principiante'] > 0:
                if 'potencia' in moto_orig and moto_orig['potencia'] <= 50:
                    reasons.append(f"Potencia de {moto_orig['potencia']}CV adecuada para principiantes")
            elif 'experiencia_intermedio' in user_features and user_features['experiencia_intermedio'] > 0:
                if 'potencia' in moto_orig and 50 < moto_orig['potencia'] <= 100:
                    reasons.append(f"Potencia de {moto_orig['potencia']}CV ideal para nivel intermedio")
            elif 'experiencia_experto' in user_features and user_features['experiencia_experto'] > 0:
                if 'potencia' in moto_orig and moto_orig['potencia'] > 100:
                    reasons.append(f"Alta potencia de {moto_orig['potencia']}CV para usuarios experimentados")
                    
            # Uso previsto vs tipo
            if 'uso_previsto_urbano' in user_features and user_features['uso_previsto_urbano'] > 0:
                if 'tipo' in moto_orig and moto_orig['tipo'] in ['scooter', 'naked']:
                    reasons.append(f"Moto tipo {moto_orig['tipo']} ideal para uso urbano")
            elif 'uso_previsto_carretera' in user_features and user_features['uso_previsto_carretera'] > 0:
                if 'tipo' in moto_orig and moto_orig['tipo'] in ['sport', 'touring']:
                    reasons.append(f"Moto tipo {moto_orig['tipo']} perfecta para carretera")
            elif 'uso_previsto_offroad' in user_features and user_features['uso_previsto_offroad'] > 0:
                if 'tipo' in moto_orig and moto_orig['tipo'] in ['enduro', 'cross', 'trail']:
                    reasons.append(f"Moto tipo {moto_orig['tipo']} diseñada para off-road")
                    
            # Presupuesto vs precio
            if 'presupuesto' in user_features and 'precio' in moto_orig:
                if moto_orig['precio'] <= user_features['presupuesto']:
                    reasons.append(f"Precio de {moto_orig['precio']}€ dentro de tu presupuesto")
                    
        # Si no se generaron razones específicas
        if not reasons:
            reasons.append("Características técnicas compatibles con tu perfil")
            
        return reasons[0] if reasons else "Recomendado según tus preferencias"
    
    def _get_similarity_reason(self, base_moto_id, similar_moto_id):
        """
        Genera una razón explicativa basada en similitud.
        
        Args:
            base_moto_id: ID de la moto base
            similar_moto_id: ID de la moto similar
            
        Returns:
            str: Razón para la recomendación
        """
        # Obtener características originales
        if not hasattr(self, 'moto_features_raw'):
            return f"Similar a otra moto que te gustó"
            
        if base_moto_id not in self.moto_features_raw.index or similar_moto_id not in self.moto_features_raw.index:
            return f"Similar a otra moto que te gustó"
            
        base_moto = self.moto_features_raw.loc[base_moto_id]
        similar_moto = self.moto_features_raw.loc[similar_moto_id]
        
        # Encontrar similitudes principales
        similarities = []
        
        if 'tipo' in base_moto and 'tipo' in similar_moto and base_moto['tipo'] == similar_moto['tipo']:
            similarities.append(f"mismo tipo ({base_moto['tipo']})")
            
        if 'marca' in base_moto and 'marca' in similar_moto and base_moto['marca'] == similar_moto['marca']:
            similarities.append(f"misma marca ({base_moto['marca']})")
            
        if 'cilindrada' in base_moto and 'cilindrada' in similar_moto:
            diff = abs(base_moto['cilindrada'] - similar_moto['cilindrada'])
            if diff <= 100:  # Umbral arbitrario para considerar cilindradas similares
                similarities.append(f"cilindrada similar")
                
        if 'potencia' in base_moto and 'potencia' in similar_moto:
            diff = abs(base_moto['potencia'] - similar_moto['potencia'])
            if diff <= 10:  # Umbral arbitrario para considerar potencias similares
                similarities.append(f"potencia similar")
                
        # Generar razón completa
        if similarities:
            return f"Similar a {base_moto.get('marca', '')} {base_moto.get('modelo', '')} que te gustó ({', '.join(similarities[:2])})"
        else:
            return f"Similar a otra moto con la que interactuaste"
    
    def _apply_contextual_factors(self, user_id, context, candidates):
        """
        Aplica factores contextuales a las recomendaciones.
        
        Args:
            user_id: ID del usuario
            context (dict): Datos contextuales
            candidates (list): Lista de recomendaciones candidatas
            
        Returns:
            dict: Diccionario con boosts contextuales {moto_id: boost_value}
        """
        context_boost = {}
        
        # No realizar boost contextual si no hay datos de contexto o candidatos
        if not context or not candidates:
            return context_boost
            
        # Extraer candidatos
        candidate_ids = [item[0] for item in candidates]
        
        # Aplicar boost por hora del día
        if 'hour' in context:
            hour = context['hour']
            
            # Obtener características originales de motos
            if hasattr(self, 'moto_features_raw'):
                for moto_id in candidate_ids:
                    if moto_id in self.moto_features_raw.index:
                        moto = self.moto_features_raw.loc[moto_id]
                        
                        # Ejemplo: Boost para scooters en horas punta
                        if 'tipo' in moto and moto['tipo'] == 'scooter' and (8 <= hour <= 10 or 17 <= hour <= 19):
                            context_boost[moto_id] = context_boost.get(moto_id, 0) + 0.2
                            
                        # Ejemplo: Boost para motos deportivas en fin de semana y tardes
                        if 'tipo' in moto and moto['tipo'] in ['sport', 'naked'] and (12 <= hour <= 19):
                            context_boost[moto_id] = context_boost.get(moto_id, 0) + 0.15
        
        # Aplicar boost por temporada/mes
        if 'month' in context:
            month = context['month']
            
            # Obtener características originales de motos
            if hasattr(self, 'moto_features_raw'):
                for moto_id in candidate_ids:
                    if moto_id in self.moto_features_raw.index:
                        moto = self.moto_features_raw.loc[moto_id]
                        
                        # Ejemplo: Boost para motos off-road en meses de verano
                        if 'tipo' in moto and moto['tipo'] in ['enduro', 'cross', 'trail'] and (5 <= month <= 9):
                            context_boost[moto_id] = context_boost.get(moto_id, 0) + 0.25
                            
                        # Ejemplo: Boost para scooters en meses lluviosos
                        if 'tipo' in moto and moto['tipo'] == 'scooter' and month in [10, 11, 12, 1, 2, 3]:
                            context_boost[moto_id] = context_boost.get(moto_id, 0) + 0.15
                            
        # Se podrían agregar más factores contextuales como ubicación, clima, etc.
                            
        return context_boost
    
    def _apply_diversity(self, recommendations, diversity_factor):
        """
        Aplica un factor de diversidad a las recomendaciones.
        
        Args:
            recommendations (dict): Diccionario de recomendaciones {moto_id: score}
            diversity_factor (float): Factor de diversidad (0-1)
            
        Returns:
            dict: Recomendaciones con diversidad aplicada
        """
        if not recommendations:
            return {}
            
        diverse_recs = recommendations.copy()
        
        # Si no hay características de motos, no se puede aplicar diversidad basada en ellas
        if not hasattr(self, 'moto_features'):
            return diverse_recs
            
        # Obtener tipos únicos de motos recomendadas
        moto_types = {}
        type_counts = defaultdict(int)
        
        for moto_id in recommendations:
            if moto_id in self.moto_features.index:
                # Intentar encontrar columnas de tipo
                tipo_cols = [col for col in self.moto_features.columns if 'tipo_' in col]
                
                if tipo_cols:
                    # Para cada moto, identificar su tipo
                    for col in tipo_cols:
                        if self.moto_features.loc[moto_id, col] > 0:
                            moto_type = col
                            moto_types[moto_id] = moto_type
                            type_counts[moto_type] += 1
                            break
        
        # Si no hay suficiente variedad de tipos, no aplicar penalización
        if len(type_counts) <= 1:
            return diverse_recs
            
        # Aplicar factor de diversidad para penalizar tipos sobrerrepresentados
        for moto_id, score in recommendations.items():
            if moto_id in moto_types:
                moto_type = moto_types[moto_id]
                
                # Penalizar motos de tipos que ya están bien representados
                if type_counts[moto_type] > 1:
                    # Ajustar el score según la proporción del tipo
                    diversity_penalty = (type_counts[moto_type] - 1) / sum(type_counts.values())
                    diverse_recs[moto_id] = score * (1 - diversity_factor * diversity_penalty)
                    
        return diverse_recs
    
    def _get_detailed_reasons(self, user_id, moto_id, moto_info, base_reasons):
        """
        Genera razones detalladas para una recomendación.
        
        Args:
            user_id: ID del usuario
            moto_id: ID de la moto
            moto_info: Información de la moto
            base_reasons (list): Razones base para la recomendación
            
        Returns:
            list: Lista de razones detalladas
        """
        detailed_reasons = base_reasons.copy()
        
        # Agregar razones basadas en popularidad general
        if hasattr(self, 'mfm_predictions') and moto_id in self.moto_map:
            moto_idx = self.moto_map[moto_id]
            
            # Calcular popularidad general
            popularity = np.mean(self.mfm_predictions[:, moto_idx])
            
            # Normalizar a escala 0-1
            max_pred = np.max(self.mfm_predictions)
            min_pred = np.min(self.mfm_predictions)
            norm_popularity = (popularity - min_pred) / (max_pred - min_pred) if max_pred > min_pred else 0
            
            if norm_popularity > 0.7:
                detailed_reasons.append("Muy popular entre la comunidad de moteros")
            elif norm_popularity > 0.5:
                detailed_reasons.append("Buena valoración general entre usuarios")
                
        # Agregar razones basadas en atributos específicos
        if moto_info is not None:
            # Destacar relación calidad-precio
            if 'precio' in moto_info and 'potencia' in moto_info and moto_info['precio'] > 0:
                value_ratio = moto_info['potencia'] / moto_info['precio']
                
                # Normalizar comparando con todas las motos
                all_value_ratios = []
                if hasattr(self, 'moto_features_raw'):
                    valid_motos = self.moto_features_raw[self.moto_features_raw['precio'] > 0]
                    if 'potencia' in valid_motos.columns:
                        all_value_ratios = (valid_motos['potencia'] / valid_motos['precio']).tolist()
                
                if all_value_ratios:
                    percentile = percentileofscore(all_value_ratios, value_ratio)
                    if percentile > 75:
                        detailed_reasons.append("Excelente relación potencia-precio")
                    elif percentile > 60:
                        detailed_reasons.append("Buena relación potencia-precio")
                        
            # Destacar características especiales
            if 'caracteristicas_especiales' in moto_info and isinstance(moto_info['caracteristicas_especiales'], str):
                especiales = moto_info['caracteristicas_especiales'].split(',')
                if especiales:
                    detailed_reasons.append(f"Incluye {especiales[0].strip()}")
                    
            # Destacar consumo si es eficiente
            if 'consumo' in moto_info:
                consumo = moto_info['consumo']
                if consumo < 4:  # Litros/100km
                    detailed_reasons.append(f"Muy eficiente: solo {consumo}L/100km")
                    
        # Limitar a máximo 3 razones
        return detailed_reasons[:3]

# Función auxiliar para percentil (usado en razones detalladas)
def percentileofscore(a, score):
    """
    Calcula el percentil de un valor en una lista.
    
    Args:
        a (list): Lista de valores
        score: Valor para calcular su percentil
        
    Returns:
        float: Percentil (0-100)
    """
    a = np.asarray(a)
    n = len(a)
    if n == 0:
        return 0
    
    a = np.sort(a)
    idx = np.searchsorted(a, score, side='right')
    return (idx / n) * 100


# Función para integrar con el resto del sistema
def get_best_recommendations(user_id, db_config, top_n=5, context=None):
    """
    Obtiene las mejores recomendaciones usando el algoritmo híbrido avanzado.
    
    Args:
        user_id: ID del usuario
        db_config: Configuración de la base de datos
        top_n: Número de recomendaciones a generar
        context: Contexto adicional para las recomendaciones
        
    Returns:
        list: Lista de recomendaciones
    """
    try:
        # Importar el recomendador híbrido
        from app.algoritmo.hybrid_recommender import HybridMotoRecommender
        
        # Crear instancia del recomendador
        recommender = HybridMotoRecommender(db_config)
        
        # Obtener recomendaciones
        recommendations = recommender.get_hybrid_recommendations(
            user_id=user_id,
            context=context,
            top_n=top_n
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error al obtener recomendaciones: {str(e)}")
        return []

def get_recommendations_with_fixed_adapter(user_id, db_config=None, top_n=5):
    """
    Obtiene recomendaciones usando el adaptador corregido.
    
    Args:
        user_id: ID del usuario
        db_config (dict, optional): Configuración de la base de datos
        top_n (int): Número de recomendaciones a generar
        
    Returns:
        list: Lista de recomendaciones
    """
    try:
        # Importar el adaptador corregido
        from moto_adapter_fixed import MotoRecommenderAdapter
        
        # Configuración por defecto si no se proporciona
        if db_config is None:
            db_config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': '22446688'
            }
        
        # Crear instancia del adaptador
        adapter = MotoRecommenderAdapter(
            uri=db_config.get('uri'),
            user=db_config.get('user'),
            password=db_config.get('password')
        )
        
        # Obtener recomendaciones
        return adapter.get_recommendations(user_id, top_n=top_n)
        
    except Exception as e:
        logger.error(f"Error al obtener recomendaciones: {str(e)}")
        return []

if __name__ == "__main__":
    # Ejemplo de uso para pruebas
    print("Ejecutando ejemplo de uso del adaptador corregido:")
    try:
        ejemplo_uso_adaptador_corregido()
        print("\nEjemplo ejecutado correctamente.")
    except Exception as e:
        print(f"\nError al ejecutar el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()
