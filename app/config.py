"""
Configuración de la aplicación
"""
import os

# Configuración de Neo4j
NEO4J_CONFIG = {
    'uri': os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
    'user': os.environ.get('NEO4J_USER', 'neo4j'),
    'password': os.environ.get('NEO4J_PASSWORD', '22446688')
}

# Configuración de la aplicación
APP_CONFIG = {
    'DEBUG': True,
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'clave-super-secreta-motomatch'),
    'USE_MOCK_DATA': True  # Cambiar a False para usar datos reales
}

# Configuración para la recomendación
RECOMMENDATION_CONFIG = {
    # Parámetros para el recomendador avanzado
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

# Configuración general de la aplicación
APP_CONFIG = {
    # Número de resultados a mostrar en las recomendaciones
    'top_n_recommendations': 5,
    
    # Factor de diversidad para las recomendaciones (0-1)
    'diversity_factor': 0.3
}
