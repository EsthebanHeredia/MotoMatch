"""
Rutas para recomendaciones de motos basadas en amigos.
Este módulo define las rutas para mostrar las recomendaciones generadas
cuando un usuario agrega a otro como amigo.
"""
from flask import Blueprint, render_template, redirect, url_for, session, jsonify, flash, current_app
import logging
from .utils import get_friend_recommendations, get_db_connection, login_required
from .friend_recommendations import get_friend_profile_recommendations

# Configurar logging
logger = logging.getLogger(__name__)

# Crear blueprint para las rutas de amigos
friend_routes = Blueprint('friend', __name__)

@friend_routes.route('/amigo-recomendaciones/<string:friend_username>')
def amigo_recomendaciones(friend_username):
    """
    Página de recomendaciones específicas basadas en un amigo.
    
    Args:
        friend_username (str): Nombre de usuario del amigo
    """
    # Verificar que el usuario tenga sesión activa
    if 'username' not in session:
        return redirect(url_for('main.login'))
    
    username = session.get('username')
    user_id = session.get('user_id')
    
    try:
        # Obtener el adaptador
        adapter = current_app.config.get('MOTO_RECOMMENDER')
        
        if not adapter:
            flash("El sistema de recomendaciones no está disponible en este momento.")
            return redirect(url_for('main.friends'))
        
        # Buscar el ID del amigo
        friend_id = None
        if hasattr(adapter, 'users_df') and adapter.users_df is not None:
            user_rows = adapter.users_df[adapter.users_df['username'] == friend_username]
            if not user_rows.empty:
                friend_id = user_rows.iloc[0].get('user_id')
        
        # Si no lo encontramos en el DataFrame, buscar en Neo4j
        if not friend_id and hasattr(adapter, '_ensure_neo4j_connection'):
            adapter._ensure_neo4j_connection()
            with adapter.driver.session() as neo4j_session:
                result = neo4j_session.run("""
                    MATCH (u:User {username: $username})
                    RETURN u.id as user_id
                """, username=friend_username)
                record = result.single()
                if record:
                    friend_id = record.get('user_id')
        
        if not friend_id:
            flash(f"No se pudo encontrar al usuario {friend_username}.")
            return redirect(url_for('main.friends'))
        
        # Obtener recomendaciones basadas en el perfil del amigo
        recommendations = get_friend_profile_recommendations(user_id, friend_id)
        
        # Renderizar la plantilla con las recomendaciones
        return render_template('amigo_recomendaciones.html',
                            username=username,
                            friend_username=friend_username,
                            recommendations=recommendations)
    
    except Exception as e:
        logger.error(f"Error al obtener recomendaciones del amigo {friend_username}: {str(e)}")
        flash("Ocurrió un error al cargar las recomendaciones.")
        return redirect(url_for('main.friends'))

@friend_routes.route('/api/amigo-recomendaciones/<string:friend_id>')
def api_amigo_recomendaciones(friend_id):
    """
    API para obtener recomendaciones basadas en un amigo.
    
    Args:
        friend_id (str): ID del amigo
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No hay sesión activa'})
    
    user_id = session.get('user_id')
    
    try:
        # Obtener recomendaciones basadas en el perfil del amigo
        recommendations = get_friend_profile_recommendations(user_id, friend_id)
        
        if recommendations:
            return jsonify({
                'success': True,
                'recommendations': recommendations
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No se pudieron generar recomendaciones'
            })
    
    except Exception as e:
        logger.error(f"Error en API de recomendaciones de amigo: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@friend_routes.route('/recomendaciones-amigos')
@login_required
def friend_recommendations_view():
    """
    Muestra todas las recomendaciones basadas en amigos del usuario.
    Incluye recomendaciones generadas por el algoritmo de propagación de etiquetas.
    """
    user_id = session.get('user_id')
    if not user_id:
        flash('Debes iniciar sesión para ver las recomendaciones', 'error')
        return redirect(url_for('login'))
      # Obtener los amigos del usuario
    connector = create_db_connector()
    if not connector:
        flash('No se pudo conectar a la base de datos', 'error')
        return redirect(url_for('dashboard'))
    
    friends = []
    try:
        with connector.driver.session() as db_session:
            result = db_session.run("""
                MATCH (u:User {id: $user_id})-[:FRIEND]->(f:User)
                RETURN f.id as friend_id, f.username as friend_username
            """, user_id=user_id)
            
            friends = [{"id": record["friend_id"], "username": record["friend_username"]} 
                      for record in result]
    except Exception as e:
        flash(f'Error al obtener la lista de amigos: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    
    # Obtener recomendaciones para cada amigo
    all_recommendations = {}
    for friend in friends:
        friend_id = friend["id"]
        friend_username = friend["username"]
        
        recommendations = get_friend_profile_recommendations(user_id, friend_id)
        if recommendations:
            all_recommendations[friend_username] = recommendations
    
    return render_template('friend_recommendations.html', 
                           all_recommendations=all_recommendations,
                           friends=friends)

def create_db_connector():
    """
    Helper function to create a database connector with proper parameters.
    """
    try:
        from app.algoritmo.utils import DatabaseConnector
        from flask import current_app
        
        neo4j_config = current_app.config.get('NEO4J_CONFIG', {})
        uri = neo4j_config.get('uri', 'bolt://localhost:7687')
        user = neo4j_config.get('user', 'neo4j')
        password = neo4j_config.get('password', '22446688')
        
        return DatabaseConnector(uri=uri, user=user, password=password)
    except Exception as e:
        logger.error(f"Error creating database connector: {str(e)}")
        return None
