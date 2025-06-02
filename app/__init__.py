from venv import logger
from flask import Flask
from neo4j import GraphDatabase
import os
import logging

from app.algoritmo.label_propagation import MotoLabelPropagation
from app.algoritmo.moto_ideal import MotoIdealRecommender
from app.algoritmo.pagerank import MotoPageRank
from .adapter_factory import create_adapter

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, 
                template_folder='templates',  # Ruta relativa dentro de app
                static_folder='static')

    # Clave secreta necesaria para usar sesiones (como guardar el usuario)
    app.secret_key = 'clave-super-secreta'
      # Cargar configuración de la base de datos
    app.config.from_pyfile('config.py')
    
    # Configuración básica
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Fix database connection issues
    fix_database_connection()
    
    # Inicializar conexión a Neo4j
    try:
        # Crear una conexión de prueba para verificar la configuración
        neo4j_config = app.config.get('NEO4J_CONFIG')
        driver = GraphDatabase.driver(
            neo4j_config['uri'],
            auth=(neo4j_config['user'], neo4j_config['password'])
        )
        # Verificar conexión
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        app.logger.info("Conexión a Neo4j establecida correctamente")
    except Exception as e:
        app.logger.error(f"Error al conectar con Neo4j: {str(e)}")
        # No interrumpimos la ejecución, pero registramos el error
      # Crear directorio para modelos si no existe
    model_path = os.path.join(app.root_path, 'algoritmo', app.config.get('RECOMMENDATION_CONFIG', {}).get('model_path', 'models/'))
    if not os.path.exists(model_path):
        os.makedirs(model_path)
          # Importar y registrar el blueprint principal
    try:
        # Primero intentar con routes_fixed (nuestro fallback seguro)
        from .routes_fixed import fixed_routes
        app.register_blueprint(fixed_routes)
        app.logger.info("Rutas corregidas registradas correctamente")
        
        # Registrar blueprint de recomendaciones de amigos
        try:
            from .friend_routes import friend_routes
            app.register_blueprint(friend_routes, url_prefix='/friend')
            app.logger.info("Rutas de recomendaciones de amigos registradas correctamente")
        except ImportError as e:
            app.logger.warning(f"No se pudo registrar el blueprint de amigos: {str(e)}")
        
        # Asegurar que las importaciones de utils estén disponibles
        try:
            from .utils import login_required
            app.logger.info("Utilidades cargadas correctamente")
        except ImportError as e:
            app.logger.warning(f"No se pudieron cargar algunas utilidades: {str(e)}")
        
        # # Comentamos temporalmente el registro de routes.py para evitar conflictos
        # try:
        #     from .routes import main
        #     app.register_blueprint(main, url_prefix='/main')
        #     app.logger.info("Rutas principales registradas como /main")
        # except ImportError as e:
        #     app.logger.warning(f"No se pudo registrar el blueprint principal: {str(e)}")
    except Exception as e:
        app.logger.critical(f"No se pudo registrar ningún blueprint: {e}")
    
    # Registrar función para cerrar la conexión a la base de datos
    try:
        from .utils import close_db_connection
        app.teardown_appcontext(close_db_connection)
    except ImportError as e:
        app.logger.error(f"Error al importar utils: {str(e)}")    # Inicializar el adaptador y guardarlo en app.config
    adapter = create_adapter(app)
    app.config['MOTO_RECOMMENDER'] = adapter
    
    # Registrar rutas actualizadas (nueva funcionalidad)
    try:
        from motos_recomendadas_route import register_motos_recomendadas_route
        # Obtener el blueprint principal (fixed_routes/main)
        for rule in app.url_map.iter_rules():
            if rule.endpoint.startswith('main.'):
                blueprint_name = rule.endpoint.split('.')[0]
                break
        
        # Encontrar y registrar las rutas actualizadas en el blueprint correcto
        for blueprint in app.blueprints.values():
            if blueprint.name == 'main':
                register_motos_recomendadas_route(blueprint)
                app.logger.info("Rutas de motos recomendadas registradas correctamente")
                break
    except Exception as e:
        app.logger.warning(f"No se pudieron registrar las rutas de motos recomendadas: {str(e)}")
    
    return app

class MotoRecommenderAdapter:
    def __init__(self, neo4j_config=None, use_mock_data=False):
        """
        Inicializa el adaptador con la configuración proporcionada.
        
        Args:
            neo4j_config (dict): Configuración para la conexión a Neo4j
            use_mock_data (bool): Si es True, usa datos mock en lugar de Neo4j
        """
        logger.info("Inicializando MotoRecommenderAdapter")
        
        self.use_mock_data = use_mock_data
        
        # Configuración Neo4j
        if neo4j_config:
            self.neo4j_uri = neo4j_config.get('uri', "bolt://localhost:7687")
            self.neo4j_user = neo4j_config.get('user', "neo4j")
            self.neo4j_password = neo4j_config.get('password', "22446688")
        else:
            # Intentar obtener configuración de Neo4j desde la aplicación
            if self.app.config.get('NEO4J_CONFIG'):
                neo4j_config = self.app.config['NEO4J_CONFIG']
                self.neo4j_uri = neo4j_config.get('uri', 'bolt://localhost:7687')
                self.neo4j_user = neo4j_config.get('user', 'neo4j')
                self.neo4j_password = neo4j_config.get('password', '22446688')
            else:
                # Configuración por defecto
                self.neo4j_uri = 'bolt://localhost:7687'
                self.neo4j_user = 'neo4j'
                self.neo4j_password = '22446688'
        
        self.driver = None
        
        # Datos
        self.users_df = None
        self.motos_df = None
        self.ratings_df = None
        
        # Inicializar algoritmos de recomendación correctamente
        self.pagerank = MotoPageRank()
        self.label_propagation = MotoLabelPropagation()
        self.moto_ideal = MotoIdealRecommender()
        
        # Conectar a Neo4j inmediatamente al inicializar
        self.connect_to_neo4j()
        
        # Cargar datos inmediatamente
        self.load_data()
def fix_database_connection():
    """
    Fix the database connection issues by modifying the DatabaseConnector class.
    """
    try:
        from app.algoritmo.utils import DatabaseConnector
        
        # Monkey patch the __init__ method to ensure it accepts keyword arguments
        original_init = DatabaseConnector.__init__
        
        def patched_init(self, *args, **kwargs):
            # Handle both positional and keyword arguments
            if kwargs and 'uri' in kwargs:
                # Called with keywords
                uri = kwargs.get('uri', 'bolt://localhost:7687')
                user = kwargs.get('user', 'neo4j')
                password = kwargs.get('password', '22446688')
                original_init(self, uri, user, password)
            elif len(args) == 3:
                # Called with 3 positional args (uri, user, password)
                original_init(self, *args)
            elif len(args) == 1 and isinstance(args[0], str):
                # Called with just URI
                original_init(self, args[0], 'neo4j', '22446688')
            else:
                # Default fallback
                original_init(self, 'bolt://localhost:7687', 'neo4j', '22446688')
        
        # Apply the monkey patch
        DatabaseConnector.__init__ = patched_init
        
        return True
    except Exception as e:
        import logging
        logging.error(f"Failed to patch DatabaseConnector: {str(e)}")
        return False