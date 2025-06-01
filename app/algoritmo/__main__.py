"""
Punto de entrada principal para ejecutar los algoritmos de recomendación.
"""
from .pagerank import MotoPageRank
from .label_propagation import MotoLabelPropagation
from .moto_ideal import MotoIdealRecommender
from .advanced_hybrid import AdvancedHybridRecommender, get_best_recommendations
from .utils import DatabaseConnector, DataPreprocessor

def run_pagerank(db_config):
    """
    Ejecuta el algoritmo PageRank para encontrar las motos más populares.
    
    Args:
        db_config (dict): Configuración de la base de datos
        
    Returns:
        list: Lista de motos populares con sus puntuaciones
    """
    # Conectar a la base de datos
    connector = DatabaseConnector(
        uri=db_config.get('uri', 'bolt://localhost:7687'),
        user=db_config.get('user', 'neo4j'),
        password=db_config.get('password', 'password')
    )
    
    try:
        # Obtener datos de interacción
        interaction_df = connector.get_interaction_data()
        
        # Preparar datos para PageRank
        interactions = DataPreprocessor.prepare_interaction_data(interaction_df)
        
        # Inicializar y ejecutar PageRank
        pagerank = MotoPageRank()
        pagerank.build_graph(interactions)
        pagerank.run()
        
        # Obtener las motos más populares
        popular_motos = pagerank.get_popular_motos(top_n=10)
        
        return popular_motos
    finally:
        connector.close()

def run_label_propagation(db_config, user_id):
    """
    Ejecuta el algoritmo de propagación de etiquetas para recomendaciones de amigos.
    
    Args:
        db_config (dict): Configuración de la base de datos
        user_id: ID del usuario para el que se generan recomendaciones
        
    Returns:
        list: Lista de recomendaciones basadas en amigos
    """
    # Conectar a la base de datos
    connector = DatabaseConnector(
        uri=db_config.get('uri', 'bolt://localhost:7687'),
        user=db_config.get('user', 'neo4j'),
        password=db_config.get('password', 'password')
    )
    
    try:
        # Obtener datos de amistades y valoraciones
        friendship_df = connector.get_friendship_data()
        ratings_df = connector.get_ratings_data()
        
        # Convertir DataFrames a listas de tuplas
        friendships = list(friendship_df[['user_id', 'friend_id']].itertuples(index=False, name=None))
        user_ratings = list(ratings_df[['user_id', 'moto_id', 'rating']].itertuples(index=False, name=None))
        
        # Inicializar y ejecutar propagación de etiquetas
        label_prop = MotoLabelPropagation()
        label_prop.build_social_graph(friendships)
        label_prop.set_user_preferences(user_ratings)
        label_prop.propagate_labels()
        
        # Obtener recomendaciones para el usuario
        recommendations = label_prop.get_friend_recommendations(user_id, top_n=5)
        
        return recommendations
    finally:
        connector.close()

def run_moto_ideal(db_config, user_id):
    """
    Ejecuta el algoritmo para encontrar la moto ideal para un usuario.
    
    Args:
        db_config (dict): Configuración de la base de datos
        user_id: ID del usuario para el que se busca la moto ideal
        
    Returns:
        list: Lista de motos recomendadas con puntuaciones y razones
    """
    # Conectar a la base de datos
    connector = DatabaseConnector(
        uri=db_config.get('uri', 'bolt://localhost:7687'),
        user=db_config.get('user', 'neo4j'),
        password=db_config.get('password', 'password')
    )
    
    try:
        # Obtener datos necesarios
        user_df = connector.get_user_data()
        moto_df = connector.get_moto_data()
        ratings_df = connector.get_ratings_data()
        
        # Preprocesar datos
        user_df_processed = DataPreprocessor.encode_categorical(user_df)
        moto_df_processed = DataPreprocessor.normalize_features(
            DataPreprocessor.encode_categorical(moto_df),
            columns=['potencia', 'peso', 'cilindrada', 'precio']
        )
        
        # Inicializar el recomendador
        recommender = MotoIdealRecommender()
        recommender.load_data(user_df_processed, moto_df_processed, ratings_df)
        
        # Obtener recomendaciones
        recommendations = recommender.get_moto_ideal(user_id, top_n=5)
        
        return recommendations
    finally:
        connector.close()
        
def run_advanced_hybrid(db_config, user_id, context=None):
    """
    Ejecuta el algoritmo híbrido avanzado para recomendaciones precisas.
    
    Args:
        db_config (dict): Configuración de la base de datos
        user_id: ID del usuario para el que se generan recomendaciones
        context (dict, optional): Datos contextuales (hora, ubicación, etc.)
        
    Returns:
        list: Lista de motos recomendadas con puntuaciones y razones
    """
    # Conectar a la base de datos
    connector = DatabaseConnector(
        uri=db_config.get('uri', 'bolt://localhost:7687'),
        user=db_config.get('user', 'neo4j'),
        password=db_config.get('password', 'password')
    )
    
    try:
        # Obtener datos necesarios
        user_df = connector.get_user_data()
        moto_df = connector.get_moto_data()
        ratings_df = connector.get_ratings_data()
        interaction_df = connector.get_interaction_data()
        
        # Configuración del recomendador avanzado
        config = {
            'learning_rate': 0.001,
            'regularization': 0.02,
            'embedding_size': 32,
            'hidden_layers': [64, 32],
            'epochs': 15,
            'batch_size': 32,
            'collaborative_weight': 0.35,
            'feature_weight': 0.45,
            'contextual_weight': 0.2,
            'model_path': 'models/'
        }
        
        # Inicializar el recomendador avanzado
        recommender = AdvancedHybridRecommender(config)
        
        # Cargar datos
        recommender.load_data(
            user_features=user_df,
            moto_features=moto_df,
            user_interactions=interaction_df,
            user_context=None  # Los datos contextuales se pasan en context
        )
        
        # Entrenar modelos
        recommender.train_models()
        
        # Obtener recomendaciones avanzadas
        recommendations = recommender.get_recommendations(
            user_id=user_id,
            context=context,
            top_n=5,
            diversity_factor=0.3
        )
        
        return recommendations
    except Exception as e:
        print(f"Error al ejecutar el recomendador avanzado: {str(e)}")
        return []
    finally:
        connector.close()

def run_moto_ideal_with_ranges(db_config, user_id, user_preferences=None):
    """
    Ejecuta el algoritmo para encontrar la moto ideal usando rangos directos del test.
    
    Args:
        db_config (dict): Configuración de la base de datos
        user_id: ID del usuario para el que se busca la moto ideal
        user_preferences (dict): Preferencias del usuario con rangos cuantitativos
        
    Returns:
        list: Lista de motos recomendadas con puntuaciones y razones
    """
    connector = DatabaseConnector(
        uri=db_config.get('uri', 'bolt://localhost:7687'),
        user=db_config.get('user', 'neo4j'),
        password=db_config.get('password', 'password')
    )
    
    try:
        # Obtener datos necesarios
        user_df = connector.get_user_data()
        moto_df = connector.get_moto_data()
        ratings_df = connector.get_ratings_data()
        
        # Si se proporcionaron preferencias con rangos, aplicar filtros cuantitativos
        if user_preferences and moto_df is not None:
            print(f"Aplicando filtros de rangos para usuario {user_id}")
            
            # FILTRAR MOTOS POR RANGOS CUANTITATIVOS
            filtered_motos = moto_df.copy()
            
            # Filtro por presupuesto
            if 'presupuesto_min' in user_preferences and 'presupuesto_max' in user_preferences:
                min_budget = user_preferences['presupuesto_min']
                max_budget = user_preferences['presupuesto_max']
                if 'precio' in filtered_motos.columns:
                    filtered_motos = filtered_motos[
                        (filtered_motos['precio'] >= min_budget) & 
                        (filtered_motos['precio'] <= max_budget)
                    ]
                    print(f"Filtrado por presupuesto {min_budget}-{max_budget}: {len(filtered_motos)} motos")
            
            # Filtro por cilindrada
            if 'cilindrada_min' in user_preferences and 'cilindrada_max' in user_preferences:
                min_cc = user_preferences['cilindrada_min']
                max_cc = user_preferences['cilindrada_max']
                if 'cilindrada' in filtered_motos.columns:
                    filtered_motos = filtered_motos[
                        (filtered_motos['cilindrada'] >= min_cc) & 
                        (filtered_motos['cilindrada'] <= max_cc)
                    ]
                    print(f"Filtrado por cilindrada {min_cc}-{max_cc}cc: {len(filtered_motos)} motos")
            
            # Filtro por potencia
            if 'potencia_min' in user_preferences and 'potencia_max' in user_preferences:
                min_hp = user_preferences['potencia_min']
                max_hp = user_preferences['potencia_max']
                if 'potencia' in filtered_motos.columns:
                    filtered_motos = filtered_motos[
                        (filtered_motos['potencia'] >= min_hp) & 
                        (filtered_motos['potencia'] <= max_hp)
                    ]
                    print(f"Filtrado por potencia {min_hp}-{max_hp}CV: {len(filtered_motos)} motos")
            
            # Filtro por torque (si existe en los datos)
            if 'torque_min' in user_preferences and 'torque_max' in user_preferences:
                min_torque = user_preferences['torque_min']
                max_torque = user_preferences['torque_max']
                if 'torque' in filtered_motos.columns:
                    filtered_motos = filtered_motos[
                        (filtered_motos['torque'] >= min_torque) & 
                        (filtered_motos['torque'] <= max_torque)
                    ]
                    print(f"Filtrado por torque {min_torque}-{max_torque}Nm: {len(filtered_motos)} motos")
            
            # Filtro por peso (si existe en los datos)
            if 'peso_min' in user_preferences and 'peso_max' in user_preferences:
                min_weight = user_preferences['peso_min']
                max_weight = user_preferences['peso_max']
                if 'peso' in filtered_motos.columns:
                    filtered_motos = filtered_motos[
                        (filtered_motos['peso'] >= min_weight) & 
                        (filtered_motos['peso'] <= max_weight)
                    ]
                    print(f"Filtrado por peso {min_weight}-{max_weight}kg: {len(filtered_motos)} motos")
            
            print(f"Motos restantes después de filtros: {len(filtered_motos)}")
            
            # Si el filtrado dejó muy pocas motos, relajar algunos criterios
            if len(filtered_motos) < 3:
                print("Muy pocas motos encontradas, relajando criterios...")
                # Usar solo filtros de presupuesto y cilindrada (más importantes)
                filtered_motos = moto_df.copy()
                
                if 'presupuesto_min' in user_preferences and 'precio' in filtered_motos.columns:
                    # Ampliar rango de presupuesto un 50%
                    min_budget = user_preferences['presupuesto_min'] * 0.7
                    max_budget = user_preferences['presupuesto_max'] * 1.5
                    filtered_motos = filtered_motos[
                        (filtered_motos['precio'] >= min_budget) & 
                        (filtered_motos['precio'] <= max_budget)
                    ]
                
                if 'cilindrada_min' in user_preferences and 'cilindrada' in filtered_motos.columns:
                    # Ampliar rango de cilindrada
                    min_cc = max(50, user_preferences['cilindrada_min'] - 100)
                    max_cc = user_preferences['cilindrada_max'] + 200
                    filtered_motos = filtered_motos[
                        (filtered_motos['cilindrada'] >= min_cc) & 
                        (filtered_motos['cilindrada'] <= max_cc)
                    ]
                
                print(f"Motos después de relajar criterios: {len(filtered_motos)}")
        else:
            filtered_motos = moto_df
        
        # Preprocesar datos
        user_df_processed = DataPreprocessor.encode_categorical(user_df)
        moto_df_processed = DataPreprocessor.normalize_features(
            DataPreprocessor.encode_categorical(filtered_motos),
            columns=['potencia', 'peso', 'cilindrada', 'precio']
        )
        
        # Inicializar el recomendador
        recommender = MotoIdealRecommender()
        recommender.load_data(user_df_processed, moto_df_processed, ratings_df)
        
        # Obtener recomendaciones
        recommendations = recommender.get_moto_ideal(user_id, top_n=5)
        
        # Agregar información sobre los rangos usados en las razones
        enhanced_recommendations = []
        for moto_id, score, reasons in recommendations:
            # Encontrar la moto en el dataset original para agregar info de rangos
            if moto_id in filtered_motos.index:
                moto_info = filtered_motos.loc[moto_id]
                range_reasons = []
                
                # Agregar razones específicas de rangos
                if user_preferences:
                    if 'presupuesto_min' in user_preferences and 'precio' in moto_info:
                        price = moto_info['precio']
                        range_reasons.append(f"Precio Q{price:,} dentro de tu rango Q{user_preferences['presupuesto_min']:,}-Q{user_preferences['presupuesto_max']:,}")
                    
                    if 'cilindrada_min' in user_preferences and 'cilindrada' in moto_info:
                        cc = moto_info['cilindrada']
                        range_reasons.append(f"Cilindrada {cc}cc en tu rango {user_preferences['cilindrada_min']}-{user_preferences['cilindrada_max']}cc")
                    
                    if 'potencia_min' in user_preferences and 'potencia' in moto_info:
                        hp = moto_info['potencia']
                        range_reasons.append(f"Potencia {hp}CV en tu rango {user_preferences['potencia_min']}-{user_preferences['potencia_max']}CV")
                
                # Combinar razones originales con razones de rangos
                all_reasons = reasons + range_reasons
                enhanced_recommendations.append((moto_id, score, all_reasons))
            else:
                enhanced_recommendations.append((moto_id, score, reasons))
        
        return enhanced_recommendations
    finally:
        connector.close()

if __name__ == "__main__":
    # Configuración de ejemplo
    db_config = {
        'uri': 'bolt://localhost:7687',
        'user': 'neo4j',
        'password': '22446688'
    }
    
    # Ejemplo de uso con rangos
    user_id = "user123"
    user_preferences = {
        'presupuesto_min': 15000,
        'presupuesto_max': 50000,
        'cilindrada_min': 250,
        'cilindrada_max': 750,
        'potencia_min': 25,
        'potencia_max': 100,
        'experiencia': 'intermedio',
        'uso': 'mixto'
    }
    
    print("Motos más populares:")
    popular_motos = run_pagerank(db_config)
    for moto_id, score in popular_motos:
        print(f"  - Moto {moto_id}: {score:.4f}")
    
    print("\nRecomendaciones basadas en amigos:")
    friend_recs = run_label_propagation(db_config, user_id)
    for moto_id, score in friend_recs:
        print(f"  - Moto {moto_id}: {score:.4f}")
        
    print(f"\nMoto ideal para el usuario (con rangos directos del test):")
    ideal_motos = run_moto_ideal_with_ranges(db_config, user_id, user_preferences)
    for moto_id, score, reasons in ideal_motos:
        print(f"  - Moto {moto_id}: {score:.4f}")
        print(f"    Razones: {', '.join(reasons)}")
        
    print("\nRecomendaciones con algoritmo híbrido avanzado:")
    advanced_recs = run_advanced_hybrid(db_config, user_id)
    for moto_id, score, reasons in advanced_recs:
        print(f"  - Moto {moto_id}: {score:.4f}")
        print(f"    Razones: {', '.join(reasons)}")
