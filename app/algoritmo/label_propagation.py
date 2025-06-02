"""
Algoritmo de Propagación de Etiquetas (Label Propagation) para recomendar motos
basado en las preferencias de los amigos del usuario.
"""
import numpy as np
import logging
import traceback
from collections import defaultdict

class MotoLabelPropagation:
    def __init__(self, max_iterations=20, alpha=0.2):
        """
        Inicializa el algoritmo de propagación de etiquetas para recomendaciones.
        
        Args:
            max_iterations (int): Número máximo de iteraciones
            alpha (float): Factor de retención (cuánto retiene cada nodo su valor original)
        """
        self.max_iterations = max_iterations
        self.alpha = alpha
        self.social_graph = None
        self.user_preferences = None
        self.propagated_scores = None
        self.logger = logging.getLogger(__name__)
        self.moto_features = {}  # Diccionario para almacenar características de motos
        self.moto_similarity_matrix = {}  # Matriz de similitud entre motos
    
    def build_social_graph(self, friendships):
        """
        Construye el grafo social basado en las relaciones de amistad.
        
        Args:
            friendships: Lista de tuplas (user_id, friend_id) que representan amistades
            
        Returns:
            dict: Grafo social como diccionario de adyacencia
        """
        self.social_graph = defaultdict(list)
        
        # Construye las conexiones entre usuarios
        for user_id, friend_id in friendships:
            # Asegurar que ambos IDs sean strings
            user_id, friend_id = str(user_id), str(friend_id)
            self.social_graph[user_id].append(friend_id)
            self.social_graph[friend_id].append(user_id)  # Las amistades son bidireccionales
            
        return self.social_graph
    
    def set_user_preferences(self, user_moto_preferences):
        """
        Establece las preferencias iniciales de los usuarios por diferentes motos.
        
        Args:
            user_moto_preferences: Lista de tuplas (user_id, moto_id, rating)
            
        Returns:
            dict: Matriz de preferencias usuario-moto
        """
        self.user_preferences = defaultdict(dict)
        
        for user_id, moto_id, rating in user_moto_preferences:
            # Asegurar que user_id sea string
            user_id = str(user_id)
            self.user_preferences[user_id][moto_id] = float(rating)
            
        return self.user_preferences
            
    def propagate_labels(self):
        """
        Ejecuta el algoritmo de propagación de etiquetas.
        
        Returns:
            dict: Preferencias propagadas para todos los usuarios
        """
        # No lanzar error si faltan estructuras, usar vacías
        if not hasattr(self, 'social_graph') or not self.social_graph:
            self.social_graph = defaultdict(list)
            
        if not hasattr(self, 'user_preferences') or not self.user_preferences:
            self.user_preferences = defaultdict(dict)
        
        # Inicializa las puntuaciones propagadas con las preferencias originales
        self.propagated_scores = defaultdict(dict)
        for user_id, moto_prefs in self.user_preferences.items():
            for moto_id, rating in moto_prefs.items():
                self.propagated_scores[user_id][moto_id] = rating
        
        # Lista de todas las motos para asegurarnos de que consideramos todas
        all_motos = set()
        for user_prefs in self.user_preferences.values():
            all_motos.update(user_prefs.keys())
        
        # Propagación iterativa
        for _ in range(self.max_iterations):
            new_scores = defaultdict(dict)
            
            # Para cada usuario
            for user_id in self.social_graph:
                friends = self.social_graph[user_id]
                
                # Conserva alpha de sus preferencias originales
                if user_id in self.user_preferences:
                    for moto_id, rating in self.user_preferences[user_id].items():
                        new_scores[user_id][moto_id] = self.alpha * rating
                
                # Agrega (1-alpha) de las preferencias de sus amigos
                if friends:
                    for friend_id in friends:
                        # Obtiene las preferencias propagadas del amigo
                        friend_prefs = self.propagated_scores.get(friend_id, {})
                        
                        for moto_id in all_motos:
                            if moto_id in friend_prefs:
                                # Acumula la contribución del amigo
                                new_scores[user_id][moto_id] = new_scores[user_id].get(moto_id, 0) + \
                                                             (1 - self.alpha) * friend_prefs[moto_id] / len(friends)
            
            # Actualiza los scores
            self.propagated_scores = new_scores
        
        return self.propagated_scores
    
    def get_friend_recommendations(self, user_id, top_n=5):
        """
        Obtiene recomendaciones para un usuario basadas en sus amigos.
        
        Args:
            user_id: ID del usuario para el que se generan recomendaciones
            top_n (int): Número de recomendaciones a generar
            
        Returns:
            list: Lista de tuplas (moto_id, score) ordenadas por puntuación
        """
        # Asegurar que user_id sea string
        user_id = str(user_id)
        
        try:
            if not self.propagated_scores:
                self.propagate_labels()
                
            if user_id not in self.propagated_scores:
                return []
                
            # Obtiene las motos que el usuario ya ha valorado
            rated_motos = set(self.user_preferences.get(user_id, {}).keys())
            
            # Filtra las motos que el usuario no ha valorado
            unrated_motos = [(moto_id, score) for moto_id, score in self.propagated_scores[user_id].items() 
                             if moto_id not in rated_motos]
            
            # Ordena por puntuación
            sorted_recs = sorted(unrated_motos, key=lambda x: x[1], reverse=True)
            
            return sorted_recs[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error generando recomendaciones para {user_id}: {str(e)}")
            return []
            
    def initialize_from_interactions(self, interactions_data):
        """Initialize the social graph and preferences from interaction data."""
        if not interactions_data or len(interactions_data) == 0:
            # Initialize empty structures
            self.social_graph = defaultdict(list)
            self.user_preferences = defaultdict(dict)
            self.propagated_scores = defaultdict(dict)
            return self
            
        # Extract user IDs and ensure they're strings
        users_in_data = list(set([str(i["user_id"]) for i in interactions_data]))
        self.logger.debug(f"Found {len(users_in_data)} users in interactions: {users_in_data}")
        
        # 1. Build social graph from interactions
        friendships = []
        
        # Group users by motorcycles they interacted with
        moto_to_users = defaultdict(list)
        for interaction in interactions_data:
            user_id = str(interaction["user_id"])
            moto_id = interaction["moto_id"]
            moto_to_users[moto_id].append(user_id)
        
        # Users who interacted with the same motorcycle form connections
        for moto_id, users in moto_to_users.items():
            if len(users) > 1:
                for i in range(len(users)):
                    for j in range(i+1, len(users)):
                        friendships.append((users[i], users[j]))
    
        # CRITICAL FIX: Create explicit friendships between ALL users in the data
        # This ensures the algorithm works even with no common motorcycles
        if len(users_in_data) >= 2:
            for i in range(len(users_in_data)):
                for j in range(i+1, len(users_in_data)):
                    pair = (users_in_data[i], users_in_data[j])
                    if pair not in friendships:
                        friendships.append(pair)
    
        # If we have no friends, create a synthetic friend and relationship
        if not friendships and interactions_data:
            main_user = str(interactions_data[0]["user_id"])
            synthetic_friend = f"synthetic_friend_{main_user}"
            friendships.append((main_user, synthetic_friend))
            
            # Also create a synthetic interaction for this friend
            synthetic_interaction = dict(interactions_data[0])
            synthetic_interaction["user_id"] = synthetic_friend
            synthetic_interaction["weight"] = 0.7  # Lower weight for synthetic data
            interactions_data.append(synthetic_interaction)
    
        # 2. Build the social graph from friendships
        self.social_graph = defaultdict(list)
        for user1, user2 in friendships:
            self.social_graph[user1].append(user2)
            self.social_graph[user2].append(user1)
    
        # 3. Set user preferences from interactions
        self.user_preferences = defaultdict(dict)
        for interaction in interactions_data:
            user_id = str(interaction["user_id"])
            moto_id = interaction["moto_id"]
            weight = float(interaction.get("weight", 1.0))
            self.user_preferences[user_id][moto_id] = weight
    
        # 4. Make sure EVERY user in the social graph has preferences
        for user_id in self.social_graph:
            if not self.user_preferences.get(user_id):
                # Copy preferences from a random user who has them
                for other_user, prefs in self.user_preferences.items():
                    if prefs:
                        for moto_id, weight in prefs.items():
                            # Create synthetic preference with lower weight
                            self.user_preferences[user_id][moto_id] = weight * 0.5
                        break
                        
        # 5. NUEVO: Recopilar características de las motos para recomendaciones basadas en contenido
        moto_features = []
        for interaction in interactions_data:
            moto_data = {
                'moto_id': interaction["moto_id"],
                'marca': interaction.get("marca", ""),
                'modelo': interaction.get("modelo", ""),
                'tipo': interaction.get("tipo", ""),
                'cilindrada': interaction.get("cilindrada", 0),
                'potencia': interaction.get("potencia", 0),
                'precio': interaction.get("precio", 0)
            }
            moto_features.append(moto_data)
        
        # Inicializar características de motos para recomendaciones basadas en contenido
        self.add_moto_features(moto_features)
        
        # 5. Run the label propagation algorithm
        try:
            self.propagate_labels()
        except Exception as e:
            self.logger.error(f"Error during label propagation: {str(e)}")
            traceback.print_exc()
            # Initialize empty scores as fallback
            self.propagated_scores = defaultdict(dict)
            # Copy user preferences to propagated scores as minimum fallback
            for user_id, prefs in self.user_preferences.items():
                for moto_id, weight in prefs.items():
                    self.propagated_scores[user_id][moto_id] = weight
    
        return self
    
    def get_recommendations(self, user_id, top_n=5):
        """
        Obtiene recomendaciones para un usuario basadas en el algoritmo de propagación
        y también en características similares a las motos que le gustan.
        
        Args:
            user_id: ID del usuario para el que se generan recomendaciones
            top_n (int): Número de recomendaciones a generar
            
        Returns:
            list: Lista de diccionarios {moto_id, score, note} ordenadas por puntuación
        """
        # Asegurar que user_id sea string
        user_id = str(user_id)
        print(f"DEBUG: Getting recommendations for user_id: {user_id}")
        
        try:
            # Ensure we have propagated scores
            if not self.propagated_scores:
                print("DEBUG: No propagated scores found, running propagation")
                self.propagate_labels()
            
            # Get all available motos from all users
            all_motos = set()
            for user_prefs in self.user_preferences.values():
                all_motos.update(user_prefs.keys())
            print(f"DEBUG: Found {len(all_motos)} total motos across all users")
            
            # Get motos the user has already rated
            rated_motos = set(self.user_preferences.get(user_id, {}).keys())
            print(f"DEBUG: User {user_id} has rated {len(rated_motos)} motos: {list(rated_motos)}")
            
            # NUEVO: Obtener también las motos ideales del usuario y sus amigos
            ideal_motos = self._get_ideal_motos(user_id)
            
            # Get friend's motos
            friends_motos = []
            for friend_id in self.social_graph.get(user_id, []):
                print(f"DEBUG: Checking motos from friend {friend_id}")
                for moto_id, score in self.user_preferences.get(friend_id, {}).items():
                    if moto_id not in rated_motos:
                        friends_motos.append({
                            "moto_id": moto_id, 
                            "score": score * 0.9,
                            "note": "A tu amigo le gusta esta moto"
                        })
            
            # Get unrated motos from propagated scores
            propagated_motos = []
            if user_id in self.propagated_scores:
                print(f"DEBUG: User {user_id} found in propagated scores")
                for moto_id, score in self.propagated_scores[user_id].items():
                    if moto_id not in rated_motos:
                        propagated_motos.append({
                            "moto_id": moto_id, 
                            "score": score,
                            "note": "Recomendada según tus conexiones sociales"
                        })
            else:
                print(f"DEBUG: User {user_id} NOT found in propagated scores")
                
            # NUEVO: Obtener recomendaciones basadas en motos similares a las que le gustan al usuario y sus amigos
            content_based_recs = self._get_content_based_recommendations(user_id, rated_motos, ideal_motos)
            
            # Combine all sources
            all_recommendations = propagated_motos + friends_motos + content_based_recs
            
            # If still no recommendations, use all available motos
            if not all_recommendations:
                print("DEBUG: No recommendations found, using all available motos")
                for moto_id in all_motos:
                    if moto_id not in rated_motos:
                        all_recommendations.append({
                            "moto_id": moto_id, 
                            "score": 0.5,
                            "note": "Podría interesarte"
                        })
            
            # IMPORTANT FIX: If user has already rated all available motos,
            # recommend the ones they might like based on propagation
            if not all_recommendations:
                print("DEBUG: User has rated all motos, recommending anyway based on propagation scores")
                # Recommend motos with propagated scores different from user's original ratings
                if user_id in self.propagated_scores:
                    for moto_id, prop_score in self.propagated_scores[user_id].items():
                        original_score = self.user_preferences[user_id].get(moto_id, 0)
                        if prop_score > original_score:
                            all_recommendations.append({
                                "moto_id": moto_id, 
                                "score": prop_score,
                                "note": "Based on your friends' preferences"
                            })
                
                # If still nothing, use the top rated motos from the user's own ratings
                if not all_recommendations:
                    print("DEBUG: Using user's own top rated motos as recommendations")
                    sorted_rated = sorted(
                        [(moto_id, score) for moto_id, score in self.user_preferences[user_id].items()],
                        key=lambda x: x[1],
                        reverse=True
                    )
                    for moto_id, score in sorted_rated[:top_n]:
                        all_recommendations.append({
                            "moto_id": moto_id, 
                            "score": score,
                            "note": "You already like this motorcycle"
                        })
            
            # Sort by score
            sorted_recs = sorted(all_recommendations, key=lambda x: x["score"], reverse=True)
            
            # Remove duplicates (keeping highest score)
            unique_recs = []
            seen_motos = set()
            for rec in sorted_recs:
                if rec["moto_id"] not in seen_motos:
                    unique_recs.append(rec)
                    seen_motos.add(rec["moto_id"])
            
            print(f"DEBUG: Generated {len(unique_recs)} recommendations")
            return unique_recs[:top_n]
            
        except Exception as e:
            print(f"DEBUG ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Special case - return the user's own rated motos as a last resort
            if user_id in self.user_preferences and self.user_preferences[user_id]:
                print("DEBUG: Using user's own ratings as fallback recommendations")
                fallback_recs = [
                    {"moto_id": moto_id, "score": score, "note": "From your likes"}
                    for moto_id, score in sorted(
                        self.user_preferences[user_id].items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:top_n]
                ]
                return fallback_recs
                
            return []
    
    def recommend(self, user_id, friend_id, interactions, top_n=5):
        """
        Genera recomendaciones específicas basadas en las interacciones entre un usuario y su amigo.
        
        Args:
            user_id (str): ID del usuario para el que se generan recomendaciones
            friend_id (str): ID del amigo
            interactions (list): Lista de diccionarios con interacciones {user_id, moto_id, weight}
            top_n (int): Número de recomendaciones a generar
            
        Returns:
            list: Lista de diccionarios con recomendaciones {moto_id, marca, modelo, score}
        """
        # Asegurar que user_id y friend_id sean strings
        user_id, friend_id = str(user_id), str(friend_id)
        
        # Inicializamos el algoritmo con las interacciones
        self.initialize_from_interactions(interactions)
        
        # Obtenemos recomendaciones para el usuario
        recommendations = self.get_recommendations(user_id, top_n)
        
        # Si no hay suficientes recomendaciones, intentamos extraer de las interacciones directas
        if len(recommendations) < top_n:
            # Extraemos las motos que le gustaron al amigo y que el usuario no ha valorado
            user_rated_motos = set()
            friend_liked_motos = []
            
            for interaction in interactions:
                if str(interaction['user_id']) == user_id:
                    user_rated_motos.add(interaction['moto_id'])
                elif str(interaction['user_id']) == friend_id:
                    friend_liked_motos.append({
                        'moto_id': interaction['moto_id'],
                        'score': float(interaction['weight']),
                        'marca': interaction.get('marca', "Recomendada"),
                        'modelo': interaction.get('modelo', "por tu amigo")
                    })
            
            # Filtramos las motos que el usuario ya ha valorado
            friend_recs = [moto for moto in friend_liked_motos 
                          if moto['moto_id'] not in user_rated_motos]
            
            # Ordenamos por score
            friend_recs = sorted(friend_recs, key=lambda x: x['score'], reverse=True)
            
            # Agregamos las recomendaciones del amigo que no estén ya en nuestras recomendaciones
            recommendation_ids = {rec['moto_id'] for rec in recommendations}
            for rec in friend_recs:
                if rec['moto_id'] not in recommendation_ids and len(recommendations) < top_n:
                    recommendations.append(rec)
                    recommendation_ids.add(rec['moto_id'])
        
        # Aseguramos que todas las recomendaciones tengan la misma estructura
        for rec in recommendations:
            if 'marca' not in rec:
                rec['marca'] = "Recomendada"
            if 'modelo' not in rec:
                rec['modelo'] = "para ti"
        
        return recommendations

    def add_moto_features(self, motos_list):
        """
        Agrega características de motos para calcular similitudes.
        
        Args:
            motos_list (list): Lista de diccionarios con datos de motos
            
        Returns:
            dict: Diccionario con características de motos
        """
        self.moto_features = {}
        for moto in motos_list:
            moto_id = moto.get('moto_id', moto.get('id', None))
            if moto_id:
                self.moto_features[moto_id] = {
                    'marca': str(moto.get('marca', '')).lower(),
                    'tipo': str(moto.get('tipo', '')).lower(),
                    'cilindrada': float(moto.get('cilindrada', 0) or 0),
                    'potencia': float(moto.get('potencia', 0) or 0),
                    'precio': float(moto.get('precio', 0) or 0)
                }
        
        # Calcular matriz de similitud entre motos
        self._calculate_moto_similarity()
        
        return self.moto_features
    
    def _calculate_moto_similarity(self):
        """
        Calcula la similitud entre todas las motos basándose en sus características.
        Esta matriz será usada para recomendar motos similares.
        """
        self.moto_similarity_matrix = {}
        
        if not self.moto_features:
            self.logger.warning("No hay características de motos para calcular similitudes")
            return
            
        # Para cada par de motos, calcular similitud
        moto_ids = list(self.moto_features.keys())
        
        for i, moto1_id in enumerate(moto_ids):
            self.moto_similarity_matrix[moto1_id] = {}
            
            for moto2_id in moto_ids:
                # No calcular similitud consigo misma (es siempre 1.0)
                if moto1_id == moto2_id:
                    self.moto_similarity_matrix[moto1_id][moto2_id] = 1.0
                    continue
                
                # Si ya calculamos la similitud inversa, usar el mismo valor
                if moto2_id in self.moto_similarity_matrix and moto1_id in self.moto_similarity_matrix[moto2_id]:
                    self.moto_similarity_matrix[moto1_id][moto2_id] = self.moto_similarity_matrix[moto2_id][moto1_id]
                    continue
                    
                # Calcular similitud
                sim = self._calculate_similarity(self.moto_features[moto1_id], self.moto_features[moto2_id])
                self.moto_similarity_matrix[moto1_id][moto2_id] = sim
    
    def _calculate_similarity(self, moto1, moto2):
        """
        Calcula la similitud entre dos motos basándose en sus características.
        
        Args:
            moto1 (dict): Características de la primera moto
            moto2 (dict): Características de la segunda moto
            
        Returns:
            float: Valor de similitud entre 0 y 1
        """
        similarity = 0.0
        weight_sum = 0.0
        
        # Similitud por marca (peso: 0.3)
        if moto1['marca'] == moto2['marca']:
            similarity += 0.3
            weight_sum += 0.3
        
        # Similitud por tipo (peso: 0.3)
        if moto1['tipo'] == moto2['tipo']:
            similarity += 0.3
            weight_sum += 0.3
            
        # Similitud por cilindrada (peso: 0.15)
        if moto1['cilindrada'] > 0 and moto2['cilindrada'] > 0:
            cil_ratio = min(moto1['cilindrada'], moto2['cilindrada']) / max(moto1['cilindrada'], moto2['cilindrada'])
            similarity += 0.15 * cil_ratio
            weight_sum += 0.15
            
        # Similitud por potencia (peso: 0.15)
        if moto1['potencia'] > 0 and moto2['potencia'] > 0:
            pot_ratio = min(moto1['potencia'], moto2['potencia']) / max(moto1['potencia'], moto2['potencia'])
            similarity += 0.15 * pot_ratio
            weight_sum += 0.15
            
        # Similitud por precio (peso: 0.1)
        if moto1['precio'] > 0 and moto2['precio'] > 0:
            price_ratio = min(moto1['precio'], moto2['precio']) / max(moto1['precio'], moto2['precio'])
            similarity += 0.1 * price_ratio
            weight_sum += 0.1
        
        # Normalizar si hay peso
        if weight_sum > 0:
            similarity /= weight_sum
            
        return similarity
    
    def find_similar_motos(self, moto_id, top_n=5):
        """
        Encuentra motos similares a una moto dada usando la matriz de similitud.
        
        Args:
            moto_id (str): ID de la moto para la que buscar similares
            top_n (int): Número de motos similares a devolver
            
        Returns:
            list: Lista de tuplas (moto_id, score) con las motos más similares
        """
        if not self.moto_similarity_matrix or moto_id not in self.moto_similarity_matrix:
            return []
            
        # Obtener todas las similitudes para esta moto
        similarities = [(other_id, sim) for other_id, sim in self.moto_similarity_matrix[moto_id].items()]
        
        # Ordenar por similitud descendente y devolver los top_n
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]
    
    def _get_ideal_motos(self, user_id):
        """
        Obtiene las motos ideales del usuario y sus amigos.
        Una moto ideal es aquella con puntuación alta (> 0.8).
        
        Args:
            user_id (str): ID del usuario
            
        Returns:
            list: Lista de IDs de motos ideales
        """
        ideal_motos = []
        
        # Obtener motos ideales del usuario (aquellas con puntuación alta)
        if user_id in self.user_preferences:
            for moto_id, score in self.user_preferences[user_id].items():
                if score > 0.8:  # Puntuación alta considera moto ideal
                    ideal_motos.append(moto_id)
        
        # Obtener motos ideales de los amigos del usuario
        for friend_id in self.social_graph.get(user_id, []):
            if friend_id in self.user_preferences:
                for moto_id, score in self.user_preferences[friend_id].items():
                    if score > 0.8 and moto_id not in ideal_motos:
                        ideal_motos.append(moto_id)
        
        return ideal_motos

    def _get_content_based_recommendations(self, user_id, rated_motos, ideal_motos, max_per_moto=3):
        """
        Genera recomendaciones basadas en características similares a las motos ideales
        y a las motos que le gustan al usuario y sus amigos.
        
        Args:
            user_id (str): ID del usuario
            rated_motos (set): Conjunto de IDs de motos ya valoradas por el usuario
            ideal_motos (list): Lista de IDs de motos ideales para el usuario y sus amigos
            max_per_moto (int): Número máximo de recomendaciones por moto referencia
            
        Returns:
            list: Lista de diccionarios con recomendaciones {moto_id, score, note}
        """
        content_based_recs = []
        seen_recommendations = set()
        
        if not self.moto_similarity_matrix:
            print("DEBUG: No similarity matrix available for content-based recommendations")
            return []
        
        # 1. Obtener recomendaciones basadas en motos ideales
        print(f"DEBUG: Finding similar motos to {len(ideal_motos)} ideal motos")
        for ideal_moto_id in ideal_motos:
            similar_motos = self.find_similar_motos(ideal_moto_id, top_n=max_per_moto)
            
            for similar_moto_id, sim_score in similar_motos:
                if similar_moto_id not in rated_motos and similar_moto_id not in seen_recommendations:
                    content_based_recs.append({
                        "moto_id": similar_moto_id,
                        "score": sim_score * 0.95,  # Ligera reducción para priorizar motos reales del usuario
                        "note": "Similar a una moto ideal para ti o tus amigos"
                    })
                    seen_recommendations.add(similar_moto_id)
        
        # 2. Obtener recomendaciones basadas en motos que le gustan al usuario
        if user_id in self.user_preferences:
            user_liked_motos = [(moto_id, score) for moto_id, score in self.user_preferences[user_id].items() 
                               if score > 0.6 and moto_id not in ideal_motos]
            
            print(f"DEBUG: Finding similar motos to {len(user_liked_motos)} liked motos")
            for liked_moto_id, user_score in user_liked_motos:
                similar_motos = self.find_similar_motos(liked_moto_id, top_n=max_per_moto)
                
                for similar_moto_id, sim_score in similar_motos:
                    if similar_moto_id not in rated_motos and similar_moto_id not in seen_recommendations:
                        content_based_recs.append({
                            "moto_id": similar_moto_id,
                            "score": sim_score * 0.85,  # Reducción para priorizar motos ideales
                            "note": "Similar a una moto que te gustó"
                        })
                        seen_recommendations.add(similar_moto_id)
        
        # 3. Obtener recomendaciones basadas en motos que les gustan a los amigos
        for friend_id in self.social_graph.get(user_id, []):
            if friend_id in self.user_preferences:
                friend_liked_motos = [(moto_id, score) for moto_id, score in self.user_preferences[friend_id].items()
                                     if score > 0.7 and moto_id not in ideal_motos]
                
                print(f"DEBUG: Finding similar motos to {len(friend_liked_motos)} motos liked by friend {friend_id}")
                for liked_moto_id, friend_score in friend_liked_motos:
                    similar_motos = self.find_similar_motos(liked_moto_id, top_n=2)  # Menos recomendaciones por moto de amigo
                    
                    for similar_moto_id, sim_score in similar_motos:
                        if similar_moto_id not in rated_motos and similar_moto_id not in seen_recommendations:
                            content_based_recs.append({
                                "moto_id": similar_moto_id,
                                "score": sim_score * 0.75,  # Reducción para priorizar motos del usuario
                                "note": "Similar a una moto que le gustó a tu amigo"
                            })
                            seen_recommendations.add(similar_moto_id)
        
        print(f"DEBUG: Generated {len(content_based_recs)} content-based recommendations")
        return content_based_recs
    
    def get_multi_friend_recommendations(self, user_id, friends_data, top_n=10):
        """
        Obtiene recomendaciones basadas en múltiples amigos considerando:
        - Motos ideales de amigos (peso alto)
        - Likes de amigos (peso medio)
        - Motos ideales del usuario (peso alto, para recomendar similares)
        - Likes del usuario (peso medio, para recomendar similares)
        
        Args:
            user_id (str): ID del usuario
            friends_data (list): Lista de dictionaries con datos de amigos
            top_n (int): Número de recomendaciones a retornar
            
        Returns:
            list: Lista de dictionaries con recomendaciones y atribución
        """
        self.logger.info(f"Generando recomendaciones multi-amigo para usuario {user_id}")
        
        try:
            # Inicializar scores de recomendaciones
            recommendation_scores = defaultdict(float)
            recommendation_sources = defaultdict(list)  # Para tracking de fuentes
              # Obtener motos ya valoradas/ideales del usuario para excluirlas
            user_motos = set()
            if (hasattr(self, 'user_preferences') and 
                self.user_preferences is not None and 
                user_id in self.user_preferences):
                user_motos.update(self.user_preferences[user_id].keys())
                
            # Obtener motos ideales del usuario desde Neo4j para también excluirlas
            try:
                from flask import current_app
                adapter = current_app.config.get('MOTO_RECOMMENDER')
                if adapter and hasattr(adapter, 'driver'):
                    with adapter.driver.session() as session:
                        # Motos ideales del usuario
                        user_ideal_result = session.run("""
                            MATCH (u:User {id: $user_id})-[:IDEAL]->(m:Moto)
                            RETURN m.id as moto_id
                        """, user_id=user_id)
                        
                        for record in user_ideal_result:
                            user_motos.add(record["moto_id"])
                        
                        # Motos con like del usuario
                        user_likes_result = session.run("""
                            MATCH (u:User {id: $user_id})-[r:INTERACTED]->(m:Moto)
                            WHERE r.type = 'like'
                            RETURN m.id as moto_id
                        """, user_id=user_id)
                        
                        for record in user_likes_result:
                            user_motos.add(record["moto_id"])
            except Exception as e:
                self.logger.warning(f"Error al obtener motos del usuario: {e}")
            
            # Procesar cada amigo
            for friend_data in friends_data:
                friend_id = friend_data.get('id', friend_data.get('friend_id'))
                friend_username = friend_data.get('username', friend_data.get('friend_username'))
                
                self.logger.info(f"Procesando amigo: {friend_username} ({friend_id})")
                
                try:
                    if adapter and hasattr(adapter, 'driver'):
                        with adapter.driver.session() as session:
                            # 1. MOTOS IDEALES DEL AMIGO (peso máximo: 3.0)
                            ideal_result = session.run("""
                                MATCH (u:User {id: $friend_id})-[:IDEAL]->(m:Moto)
                                RETURN m.id as moto_id, m.marca as marca, m.modelo as modelo,
                                       m.tipo as tipo, m.precio as precio, m.imagen as imagen
                            """, friend_id=friend_id)
                            
                            for record in ideal_result:
                                moto_id = record["moto_id"]
                                if moto_id not in user_motos:  # No recomendar motos que ya tiene el usuario
                                    recommendation_scores[moto_id] += 3.0
                                    recommendation_sources[moto_id].append({
                                        'type': 'ideal',
                                        'friend': friend_username,
                                        'weight': 3.0
                                    })
                                    self.logger.debug(f"Moto ideal de {friend_username}: {record['marca']} {record['modelo']}")
                            
                            # 2. LIKES DEL AMIGO (peso medio: 1.5)
                            likes_result = session.run("""
                                MATCH (u:User {id: $friend_id})-[r:INTERACTED]->(m:Moto)
                                WHERE r.type = 'like'
                                RETURN m.id as moto_id, m.marca as marca, m.modelo as modelo,
                                       m.tipo as tipo, m.precio as precio, m.imagen as imagen,
                                       r.weight as interaction_weight
                            """, friend_id=friend_id)
                            
                            for record in likes_result:
                                moto_id = record["moto_id"]
                                if moto_id not in user_motos:  # No recomendar motos que ya tiene el usuario
                                    interaction_weight = record.get("interaction_weight", 1.0)
                                    score = 1.5 * interaction_weight
                                    recommendation_scores[moto_id] += score
                                    recommendation_sources[moto_id].append({
                                        'type': 'like',
                                        'friend': friend_username,
                                        'weight': score
                                    })
                                    self.logger.debug(f"Like de {friend_username}: {record['marca']} {record['modelo']}")
                                    
                except Exception as e:
                    self.logger.error(f"Error procesando amigo {friend_username}: {e}")
                    continue
            
            # 3. RECOMENDACIONES BASADAS EN CONTENIDO SIMILAR
            # Obtener motos similares a las que le gustan al usuario y sus amigos
            content_recommendations = self._get_content_based_recommendations(
                user_id, user_motos, [], max_per_moto=2
            )
            
            for rec in content_recommendations:
                moto_id = rec["moto_id"]
                if moto_id not in user_motos:
                    recommendation_scores[moto_id] += rec["score"]
                    recommendation_sources[moto_id].append({
                        'type': 'content',
                        'friend': 'sistema',
                        'weight': rec["score"],
                        'note': rec.get("note", "Similar a tus preferencias")
                    })
            
            # Ordenar recomendaciones por score
            sorted_recommendations = sorted(
                recommendation_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Crear resultado final con detalles completos
            final_recommendations = []
            
            for moto_id, score in sorted_recommendations[:top_n]:
                try:
                    if adapter and hasattr(adapter, 'driver'):
                        with adapter.driver.session() as session:
                            moto_result = session.run("""
                                MATCH (m:Moto {id: $moto_id})
                                RETURN m.id as id, m.marca as marca, m.modelo as modelo,
                                       m.tipo as tipo, m.precio as precio, m.imagen as imagen,
                                       m.cilindrada as cilindrada, m.potencia as potencia
                            """, moto_id=moto_id)
                            
                            moto_record = moto_result.single()
                            if moto_record:
                                # Generar descripción de las fuentes
                                sources = recommendation_sources[moto_id]
                                source_text = self._generate_source_description(sources)
                                
                                final_recommendations.append({
                                    "moto_id": moto_id,
                                    "score": round(score, 2),
                                    "marca": moto_record["marca"],
                                    "modelo": moto_record["modelo"],
                                    "tipo": moto_record["tipo"],
                                    "precio": moto_record["precio"],
                                    "imagen": moto_record["imagen"],
                                    "cilindrada": moto_record["cilindrada"],
                                    "potencia": moto_record["potencia"],
                                    "source_description": source_text,
                                    "sources": sources
                                })
                except Exception as e:
                    self.logger.error(f"Error obteniendo detalles de moto {moto_id}: {e}")
                    continue
            
            self.logger.info(f"Generadas {len(final_recommendations)} recomendaciones para {user_id}")
            return final_recommendations
            
        except Exception as e:
            self.logger.error(f"Error en get_multi_friend_recommendations: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _generate_source_description(self, sources):
        """Genera descripción legible de las fuentes de recomendación"""
        if not sources:
            return "Recomendado por el sistema"
        
        # Contar tipos de fuentes
        ideal_friends = []
        like_friends = []
        content_sources = []
        
        for source in sources:
            if source['type'] == 'ideal':
                ideal_friends.append(source['friend'])
            elif source['type'] == 'like':
                like_friends.append(source['friend'])
            elif source['type'] == 'content':
                content_sources.append(source.get('note', 'Similar a tus preferencias'))
        
        # Construir descripción
        descriptions = []
        
        if ideal_friends:
            if len(ideal_friends) == 1:
                descriptions.append(f"Moto ideal de {ideal_friends[0]}")
            else:
                descriptions.append(f"Moto ideal de {', '.join(ideal_friends)}")
        
        if like_friends:
            if len(like_friends) == 1:
                descriptions.append(f"Le gustó a {like_friends[0]}")
            else:
                descriptions.append(f"Le gustó a {', '.join(like_friends[:2])}")
                if len(like_friends) > 2:
                    descriptions.append(f"y {len(like_friends) - 2} amigos más")
        
        if content_sources:
            descriptions.append("Similar a tus gustos")
        
        return " • ".join(descriptions) if descriptions else "Recomendado por el sistema"
