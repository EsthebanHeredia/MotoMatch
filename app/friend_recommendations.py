"""
Módulo para generar recomendaciones cuando un usuario agrega a otro como amigo.
Este módulo implementa funciones que utilizan el algoritmo de propagación de etiquetas
para recomendar motos ideales y motos con likes de otros usuarios.
"""
import logging
from flask import session, flash, render_template, redirect, url_for, jsonify, current_app
from .algoritmo.label_propagation import MotoLabelPropagation
from .utils import get_db_connection, get_friend_recommendations

# Configurar logging
logger = logging.getLogger(__name__)

def get_friend_profile_recommendations(user_id, friend_id):
    """
    Obtiene recomendaciones basadas en el perfil del nuevo amigo usando el algoritmo
    de propagación de etiquetas para generar recomendaciones personalizadas.
    
    Args:
        user_id (str): ID del usuario que agregó al amigo
        friend_id (str): ID del amigo agregado
        
    Returns:
        dict: Diccionario con la moto ideal y motos con likes del amigo, además de
              recomendaciones generadas por el algoritmo de propagación de etiquetas
    """
    try:
        # Obtener conexión a la base de datos
        connector = get_db_connection()
        if not connector:
            logger.error("No se pudo obtener conexión a la base de datos")
            return None
            
        # Obtener la moto ideal del amigo
        ideal_moto = get_friend_ideal_moto(friend_id, connector)
        
        # Obtener motos con likes del amigo
        liked_motos = get_friend_liked_motos(friend_id, connector)
        
        # Usar el algoritmo de propagación de etiquetas para generar recomendaciones
        label_propagation = MotoLabelPropagation()
        
        # Inicializar el algoritmo con los datos del grafo
        with connector.driver.session() as session:
            # Obtener todas las interacciones del usuario y su amigo
            result = session.run("""
                MATCH (u:User)-[r:INTERACTED]->(m:Moto)
                WHERE u.id IN [$user_id, $friend_id] AND r.type = 'like'
                RETURN u.id as user_id, m.id as moto_id, m.marca as marca, 
                       m.modelo as modelo, r.weight as weight
            """, user_id=user_id, friend_id=friend_id)
            
            # Preparar los datos para el algoritmo
            interactions = []
            for record in result:
                interactions.append({
                    'user_id': record['user_id'],
                    'moto_id': record['moto_id'],
                    'weight': record.get('weight', 1.0)
                })
            
            if interactions:
                # Ejecutar el algoritmo de propagación
                recommendations = label_propagation.recommend(
                    user_id=user_id,
                    friend_id=friend_id,
                    interactions=interactions,
                    top_n=5  # Limitar a 5 recomendaciones
                )
            else:
                recommendations = []
        
        return {
            'ideal_moto': ideal_moto,
            'liked_motos': liked_motos,
            'label_propagation_recommendations': recommendations
        }
    except Exception as e:
        logger.error(f"Error al obtener recomendaciones del amigo {friend_id}: {str(e)}")
        return None

def get_friend_ideal_moto(friend_id, connector):
    """
    Obtiene la moto ideal del amigo.
    
    Args:
        friend_id (str): ID del amigo
        connector: Conector a la base de datos
        
    Returns:
        dict: Información de la moto ideal o None si no tiene
    """
    try:
        # Consultar Neo4j para obtener la moto ideal del amigo
        with connector.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $friend_id})-[r:IDEAL|IDEAL_MOTO]->(m:Moto)
                RETURN m.id as moto_id, m.marca as marca, m.modelo as modelo, 
                       m.precio as precio, m.tipo as tipo, m.imagen as imagen,
                       r.reasons as reasons
            """, {"friend_id": friend_id})
            
            record = result.single()
            if record:
                # Convertir las razones de formato JSON a lista
                reasons = record.get('reasons', '[]')
                if isinstance(reasons, str):
                    import json
                    try:
                        reasons = json.loads(reasons)
                    except:
                        reasons = ["Moto ideal seleccionada por tu amigo"]
                
                return {
                    'moto_id': record.get('moto_id'),
                    'marca': record.get('marca', 'Desconocida'),
                    'modelo': record.get('modelo', 'Modelo desconocido'),
                    'precio': record.get('precio', 0),
                    'tipo': record.get('tipo', 'Estándar'),
                    'imagen': record.get('imagen', '/static/images/default-moto.jpg'),
                    'reasons': reasons
                }
        return None
    except Exception as e:
        logger.error(f"Error al obtener moto ideal del amigo {friend_id}: {str(e)}")
        return None

def get_friend_liked_motos(friend_id, connector, limit=5):
    """
    Obtiene las motos que le gustaron al amigo.
    
    Args:
        friend_id (str): ID del amigo
        connector: Conector a la base de datos
        limit (int): Número máximo de motos a retornar
        
    Returns:
        list: Lista de motos con likes del amigo
    """
    try:
        # Consultar Neo4j para obtener motos con likes del amigo
        with connector.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $friend_id})-[r:INTERACTED]->(m:Moto)
                WHERE r.type = 'like'
                RETURN m.id as moto_id, m.marca as marca, m.modelo as modelo, 
                       m.precio as precio, m.tipo as tipo, m.imagen as imagen,
                       r.weight as weight
                ORDER BY r.weight DESC, r.timestamp DESC
                LIMIT $limit
            """, friend_id=friend_id, limit=limit)
            
            liked_motos = []
            for record in result:
                liked_motos.append({
                    'moto_id': record.get('moto_id'),
                    'marca': record.get('marca', 'Desconocida'),
                    'modelo': record.get('modelo', 'Modelo desconocido'),
                    'precio': record.get('precio', 0),
                    'tipo': record.get('tipo', 'Estándar'),
                    'imagen': record.get('imagen', '/static/images/default-moto.jpg'),
                    'weight': record.get('weight', 1.0)
                })
            
            # Si no hay interacciones, buscar relaciones LIKES
            if not liked_motos:
                result = session.run("""
                    MATCH (u:User {id: $friend_id})-[r:LIKES]->(m:Moto)
                    RETURN m.id as moto_id, m.marca as marca, m.modelo as modelo, 
                           m.precio as precio, m.tipo as tipo, m.imagen as imagen
                    LIMIT $limit
                """, friend_id=friend_id, limit=limit)
                
                for record in result:
                    liked_motos.append({
                        'moto_id': record.get('moto_id'),
                        'marca': record.get('marca', 'Desconocida'),
                        'modelo': record.get('modelo', 'Modelo desconocido'),
                        'precio': record.get('precio', 0),
                        'tipo': record.get('tipo', 'Estándar'),
                        'imagen': record.get('imagen', '/static/images/default-moto.jpg'),
                        'weight': 1.0  # Valor predeterminado
                    })
            
            return liked_motos
    except Exception as e:
        logger.error(f"Error al obtener motos con likes del amigo {friend_id}: {str(e)}")
        return []

def generate_recommendations_notification(friend_username, recommendations):
    """
    Genera un mensaje con las recomendaciones basadas en el nuevo amigo.
    
    Args:
        friend_username (str): Nombre de usuario del amigo
        recommendations (dict): Diccionario con las recomendaciones
        
    Returns:
        str: Mensaje HTML formateado para mostrar en notificación
    """
    if not recommendations:
        return ""
        
    ideal_moto = recommendations.get('ideal_moto')
    liked_motos = recommendations.get('liked_motos', [])
    label_prop_recs = recommendations.get('label_propagation_recommendations', [])
    
    message = f"<div class='friend-recommendations'>"
    message += f"<h3>Recomendaciones basadas en tu nuevo amigo {friend_username}</h3>"
    
    if ideal_moto:
        message += f"<div class='ideal-moto-rec'>"
        message += f"<h4>Moto ideal de {friend_username}</h4>"
        message += f"<p>{ideal_moto['marca']} {ideal_moto['modelo']}</p>"
        
        # Agregar razones si están disponibles
        if ideal_moto.get('reasons'):
            message += "<ul class='reasons'>"
            for reason in ideal_moto['reasons'][:2]:  # Limitamos a 2 razones
                message += f"<li>{reason}</li>"
            message += "</ul>"
            
        message += "</div>"
    
    if liked_motos:
        message += f"<div class='liked-motos-rec'>"
        message += f"<h4>Motos que le gustaron a {friend_username}</h4>"
        message += "<ul class='liked-list'>"
        for moto in liked_motos[:3]:  # Limitamos a 3 motos
            message += f"<li>{moto['marca']} {moto['modelo']}</li>"
        message += "</ul>"
        message += "</div>"
    
    # Agregar recomendaciones basadas en propagación de etiquetas
    if label_prop_recs:
        message += f"<div class='label-prop-rec'>"
        message += f"<h4>Motos recomendadas para ti según tus gustos y los de {friend_username}</h4>"
        message += "<ul class='recommendation-list'>"
        for moto in label_prop_recs[:3]:  # Limitamos a 3 motos
            score = moto.get('score', 0)
            score_display = f" (Coincidencia: {int(score * 100)}%)" if score else ""
            message += f"<li>{moto.get('marca', 'Marca')} {moto.get('modelo', 'Modelo')}{score_display}</li>"
        message += "</ul>"
        message += "</div>"
    
    message += "<p><a href='/recomendaciones-amigos' class='view-more'>Ver todas las recomendaciones</a></p>"
    message += "</div>"
    
    return message
