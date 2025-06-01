"""
Factory for creating and initializing the recommendation adapter
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import traceback

# Configurar logging
logger = logging.getLogger(__name__)

# Asegurar que los módulos son encontrados
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from moto_adapter_fixed import MotoRecommenderAdapter

# Add the _ensure_neo4j_connection method to the adapter if it doesn't exist
def ensure_neo4j_connection_patch(adapter):
    """Patch the adapter with _ensure_neo4j_connection method if it doesn't have it"""
    if not hasattr(adapter, '_ensure_neo4j_connection'):
        def _ensure_neo4j_connection(self):
            """Asegura que hay una conexión activa a Neo4j o intenta reconectar."""
            try:
                if not self.driver:
                    logger.warning("No hay un driver de Neo4j, intentando conectar...")
                    return self.connect_to_neo4j()
                
                # Probar la conexión existente
                with self.driver.session() as session:
                    try:
                        result = session.run("RETURN 'Conexión verificada' as mensaje")
                        message = result.single()["mensaje"]
                        logger.debug(f"Neo4j conexión verificada: {message}")
                        return True
                    except Exception as session_error:
                        logger.warning(f"Error con la sesión actual: {str(session_error)}. Reconectando...")
                        self.driver.close()
                        self.driver = None
                        return self.connect_to_neo4j()
            except Exception as e:
                logger.error(f"Error al verificar conexión Neo4j: {str(e)}")
                return False
        
        # Add the method to the adapter
        import types
        adapter._ensure_neo4j_connection = types.MethodType(_ensure_neo4j_connection, adapter)
        logger.info("Added _ensure_neo4j_connection method to adapter")

def create_adapter(app=None, use_mock_data=False):
    """
    Crea y configura un adaptador de recomendación para la aplicación.
    
    Args:
        app: Aplicación Flask (opcional)
        use_mock_data: Si es True, usa datos simulados en lugar de conectar a Neo4j
        
    Returns:
        MotoRecommenderAdapter: Instancia configurada del adaptador
    """
    neo4j_config = None
    
    # Obtener configuración de Neo4j desde la aplicación
    if app and app.config.get('NEO4J_CONFIG'):
        neo4j_config = app.config.get('NEO4J_CONFIG')
        app.logger.info(f"Creating adapter with Neo4j config: {neo4j_config}, use_mock_data={use_mock_data}")
    
    # Si se especificó usar datos simulados, no intentar conexión a Neo4j
    if use_mock_data:
        try:
            from moto_adapter_fixed import MotoRecommenderAdapter
            adapter = MotoRecommenderAdapter()  # Sin parámetros de conexión
            adapter.use_mock_data = True
            app.logger.info("Usando adaptador con datos simulados")
            return adapter
        except ImportError as e:
            app.logger.error(f"No se pudo importar MotoRecommenderAdapter: {e}")
            return None
    
    # Intentar crear el adaptador con conexión a Neo4j
    try:
        from moto_adapter_fixed import MotoRecommenderAdapter
        
        # Extraer los parámetros individuales del diccionario neo4j_config
        if neo4j_config:
            uri = neo4j_config.get('uri', 'bolt://localhost:7687')
            user = neo4j_config.get('user', 'neo4j')
            password = neo4j_config.get('password', '22446688')
            
            # Crear el adaptador con parámetros individuales
            adapter = MotoRecommenderAdapter(
                uri=uri,
                user=user, 
                password=password
            )
        else:
            # Si no hay configuración, usar valores predeterminados
            adapter = MotoRecommenderAdapter()
        
        # Establecer flag de datos simulados
        adapter.use_mock_data = use_mock_data
        return adapter
        
    except Exception as e:
        if app:
            app.logger.error(f"Error creating adapter: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
            app.logger.error("La aplicación requiere Neo4j. No se creará un adaptador de respaldo.")
        return None