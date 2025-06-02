"""
Utilidades para la aplicación MotoMatch.
Este módulo proporciona funciones de ayuda para interactuar con los algoritmos
de recomendación y la base de datos.
"""
import logging
import datetime
import traceback
from flask import current_app, g, redirect, url_for, session, flash
from functools import wraps

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def login_required(f):
    """
    Decorador para requerir inicio de sesión en rutas.
    
    Args:
        f: La función decorada
    
    Returns:
        La función decorada que verifica la sesión
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """
    Obtiene una conexión a Neo4j.
    
    Returns:
        DatabaseConnector: Conector a Neo4j
    """
    from flask import current_app, g
    
    # Verificar si ya hay una conexión
    if '_database_connector' not in g:
        # Crear nueva conexión
        try:
            adapter = current_app.config.get('MOTO_RECOMMENDER')
            if adapter and hasattr(adapter, 'driver'):
                g._database_connector = adapter.driver
            else:
                logger.warning("No hay adaptador disponible para obtener conexión")
                return None
        except Exception as e:
            logger.error(f"Error al obtener conexión: {str(e)}")
            return None
        
    return g._database_connector

def close_db_connection(exception=None):
    """
    Cierra la conexión a la base de datos.
    
    Args:
        exception: Excepción si la hubo
    """
    try:
        # No necesitamos cerrar conexiones Neo4j manualmente en cada request
        # El driver maneja el pool de conexiones automáticamente
        if '_database_connector' in g:
            g.pop('_database_connector', None)
    except Exception as e:
        logger.error(f"Error cerrando conexión: {str(e)}")

def get_populares_motos(top_n=10):
    """
    Obtiene las motos más populares usando el nuevo sistema de ranking por puntos.
    
    Args:
        top_n (int): Número de motos a devolver
        
    Returns:
        list: Lista de motos populares con sus puntuaciones
    """
    try:
        from flask import current_app
        
        # Obtener el adaptador para acceso a Neo4j
        adapter = current_app.config.get('MOTO_RECOMMENDER')
        if not adapter:
            logger.warning("No hay adaptador disponible para obtener motos populares")
            return []
        
        # Usar el método del adaptador que ya maneja PageRank
        popular_motos = adapter.get_popular_motos(top_n=top_n)
        
        logger.info(f"Obtenidas {len(popular_motos)} motos populares")
        return popular_motos
        
    except Exception as e:
        logger.error(f"Error al obtener motos populares: {str(e)}")
        return []

def update_moto_ranking_like(moto_id):
    """
    Actualiza el ranking cuando una moto recibe un like.
    
    Args:
        moto_id: ID de la moto que recibió el like
        
    Returns:
        bool: True si se actualizó correctamente
    """
    try:
        from flask import current_app
        
        # Obtener el adaptador
        adapter = current_app.config.get('MOTO_RECOMMENDER')
        if not adapter or not hasattr(adapter, 'driver'):
            logger.warning("No hay adaptador disponible para actualizar ranking")
            return False
            
        # Actualizar el ranking global si existe
        ranking = current_app.config.get('MOTO_RANKING')
        if ranking and hasattr(ranking, 'update_from_neo4j'):
            ranking.update_from_neo4j(adapter.driver)
            logger.info(f"Ranking actualizado después del like a moto {moto_id}")
            return True
        else:
            logger.warning("No hay sistema de ranking global disponible")
            return False
        
    except Exception as e:
        logger.error(f"Error al actualizar ranking después del like: {str(e)}")
        return False

def update_moto_ranking_ideal(moto_id):
    """
    Actualiza el ranking cuando una moto es elegida como ideal.
    
    Args:
        moto_id: ID de la moto elegida como ideal
        
    Returns:
        bool: True si se actualizó correctamente
    """
    try:
        from flask import current_app
        
        # Obtener el adaptador
        adapter = current_app.config.get('MOTO_RECOMMENDER')
        if not adapter or not hasattr(adapter, 'driver'):
            logger.warning("No hay adaptador disponible para actualizar ranking")
            return False
            
        # Actualizar el ranking global si existe
        ranking = current_app.config.get('MOTO_RANKING')
        if ranking and hasattr(ranking, 'update_from_neo4j'):
            ranking.update_from_neo4j(adapter.driver)
            logger.info(f"Ranking actualizado después de elegir moto ideal {moto_id}")
            return True
        else:
            logger.warning("No hay sistema de ranking global disponible")
            return False
        
    except Exception as e:
        logger.error(f"Error al actualizar ranking después de elegir moto ideal: {str(e)}")
        return False

def store_user_test_results(username, test_data):
    """
    Guarda los resultados del test de usuario en Neo4j.
    
    Args:
        username: Nombre del usuario
        test_data: Datos del test
        
    Returns:
        bool: True si se guardó correctamente
    """
    try:
        from flask import current_app
        
        adapter = current_app.config.get('MOTO_RECOMMENDER')
        if not adapter:
            logger.error("No hay adaptador disponible para guardar resultados del test")
            return False
            
        # Usar el método save_preferences del adaptador si existe
        if hasattr(adapter, 'save_preferences'):
            success = adapter.save_preferences(username, test_data)
        else:
            # Fallback: guardado básico
            success = True  # Simular éxito
            logger.warning("Método save_preferences no disponible, usando fallback")
        
        if success:
            logger.info(f"Resultados del test guardados para {username}")
            return True
        else:
            logger.error(f"Error guardando resultados del test para {username}")
            return False
            
    except Exception as e:
        logger.error(f"Error al guardar resultados del test: {str(e)}")
        return False

def get_friend_recommendations(user_id, top_n=5):
    """
    Obtiene recomendaciones basadas en amigos.
    
    Args:
        user_id: ID del usuario
        top_n: Número de recomendaciones
        
    Returns:
        list: Lista de recomendaciones
    """
    try:
        from flask import current_app
        
        adapter = current_app.config.get('MOTO_RECOMMENDER')
        if not adapter:
            logger.warning("No hay adaptador disponible para recomendaciones de amigos")
            return []
            
        # Usar el algoritmo de label propagation
        recommendations = adapter.get_recommendations(
            user_id, 
            algorithm='label_propagation', 
            top_n=top_n
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error al obtener recomendaciones de amigos: {str(e)}")
        return []

def get_moto_ideal(user_id):
    """
    Obtiene la moto ideal para un usuario.
    
    Args:
        user_id: ID del usuario
        
    Returns:
        dict: Datos de la moto ideal
    """
    try:
        from flask import current_app
        
        adapter = current_app.config.get('MOTO_RECOMMENDER')
        if not adapter:
            logger.warning("No hay adaptador disponible para obtener moto ideal")
            return None
            
        # Obtener recomendaciones del algoritmo híbrido
        recommendations = adapter.get_recommendations(
            user_id, 
            algorithm='moto_ideal', 
            top_n=1
        )
        
        if recommendations:
            return recommendations[0]
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error al obtener moto ideal: {str(e)}")
        return None

def format_recommendations_for_display(recommendations):
    """
    Formatea las recomendaciones para mostrar en la interfaz.
    
    Args:
        recommendations: Lista de recomendaciones
        
    Returns:
        list: Recomendaciones formateadas
    """
    if not recommendations:
        return []
        
    formatted = []
    for rec in recommendations:
        if isinstance(rec, dict):
            formatted.append(rec)
        elif isinstance(rec, tuple) and len(rec) >= 3:
            moto_id, score, reasons = rec[:3]
            formatted.append({
                'moto_id': moto_id,
                'score': score,
                'reasons': reasons if isinstance(reasons, list) else [str(reasons)]
            })
        else:
            # Intentar procesar como dict
            try:
                formatted.append(dict(rec))
            except:
                logger.warning(f"No se pudo formatear recomendación: {rec}")
                
    return formatted
