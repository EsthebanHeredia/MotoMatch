"""
Script para ejecutar la aplicación
"""

# Importar las pruebas
import os
import sys
import logging
import traceback
from flask import Flask, render_template, session, render_template_string, redirect, url_for, jsonify, request
from neo4j import GraphDatabase

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Agregar la ruta del proyecto al path para importaciones
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    """Función principal para ejecutar la aplicación"""
    logger.info("Iniciando aplicación MotoMatch con carga anticipada de datos...")
    
    # IMPORTANTE: Usar la función create_app en lugar de crear Flask directamente
    from app import create_app
    
    # Crear la aplicación usando la factory function
    app = create_app()
    
    # Context processor para fix de URLs
    @app.context_processor
    def inject_url_prefix():
        def url_for_with_prefix(endpoint, **kwargs):
            # If the endpoint doesn't contain a dot and it's not a static endpoint,
            # prepend 'main.' to it
            if '.' not in endpoint and endpoint != 'static':
                endpoint = 'main.' + endpoint
            return url_for(endpoint, **kwargs)
        
        return dict(url_for=url_for_with_prefix)
    
    # Configurar Neo4j específicamente
    neo4j_config = {
        'uri': 'bolt://localhost:7687',
        'user': 'neo4j',
        'password': '22446688'
    }
    
    app.config['NEO4J_CONFIG'] = neo4j_config
    
    # Configuración directa para el driver Neo4j
    app.config['NEO4J_URI'] = neo4j_config['uri']
    app.config['NEO4J_USER'] = neo4j_config['user']
    app.config['NEO4J_PASSWORD'] = neo4j_config['password']
    
    # IMPORTANTE: Desactivar completamente los datos mock
    app.config['USE_MOCK_DATA'] = False  # Nunca usar datos mock
    
    # Configuración de la sesión para que sea más estable
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora
    
    # Crear e inicializar el adaptador DESPUÉS de configurar la app
    try:
        from app.adapter_factory import create_adapter
        
        logger.info("🔧 Intentando crear adaptador de recomendaciones...")
        
        # Crear e inicializar el adaptador - cargará datos inmediatamente
        adapter = create_adapter(app)
        
        # FIX: Asegurar que el adaptador tenga logger
        if adapter and not hasattr(adapter, 'logger'):
            adapter.logger = logging.getLogger('MotoRecommenderAdapter')
            adapter.logger.setLevel(logging.INFO)
        
        # Registrar el adaptador en la aplicación
        app.config['MOTO_RECOMMENDER'] = adapter
        
        if adapter:
            logger.info("✅ Adaptador de recomendaciones creado exitosamente")
            
            # NUEVO: Inicializar el ranking de motos como instancia global
            from app.algoritmo.pagerank import MotoPageRank
            try:
                ranking = MotoPageRank()
                if hasattr(adapter, 'driver') and adapter.driver:
                    logger.info("🔄 Inicializando ranking de motos desde Neo4j...")
                    ranking.update_from_neo4j(adapter.driver)
                    app.config['MOTO_RANKING'] = ranking
                    logger.info("✅ Ranking de motos inicializado correctamente")
                else:
                    logger.warning("⚠️ No hay driver de Neo4j disponible para el ranking")
                    
            except Exception as ranking_error:
                logger.error(f"❌ Error inicializando ranking: {str(ranking_error)}")
                logger.error(traceback.format_exc())

        else:
            logger.warning("⚠️ No se pudo crear el adaptador de recomendaciones")
            
    except Exception as e:
        logger.error(f"❌ Error crítico en main: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    
    # DIAGNÓSTICO: Ver qué rutas están registradas
    with app.app_context():
        logger.info("=== TODAS LAS RUTAS REGISTRADAS ===")
        for rule in app.url_map.iter_rules():
            logger.info(f"🔍 RUTA: {rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")
        
        logger.info("=== BLUEPRINTS REGISTRADOS ===")
        for name, blueprint in app.blueprints.items():
            logger.info(f"🔍 BLUEPRINT: {name}")
    
    # Retornar la app para uso en servidores de producción
    return app

def run_server(app=None, suppress_warnings=False):
    """Ejecutar el servidor Flask con opciones de configuración"""
    if app is None:
        app = main()
    
    if suppress_warnings:
        # Suprimir advertencias del servidor de desarrollo
        import warnings
        warnings.filterwarnings('ignore', message='This is a development server.*')
        warnings.filterwarnings('ignore', message='.*WARNING.*development server.*')
        
        # Configurar logging de Werkzeug para suprimir advertencias
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.ERROR)
    
    # Lista de puertos alternativos para probar
    puertos = [5000, 8080, 3000, 8000, 4000, 5001]
    
    for puerto in puertos:
        try:
            logger.info(f"🌐 Intentando iniciar servidor en http://localhost:{puerto}")
            app.run(
                host='0.0.0.0',
                port=puerto,
                debug=True,
                threaded=True,
                use_reloader=False
            )
            # Si llega aquí, el servidor se inició correctamente
            break
        except OSError as e:
            if e.errno == 48 or "Address already in use" in str(e):  # 48 es "Address already in use"
                logger.warning(f"⚠️ Puerto {puerto} ocupado, intentando con el siguiente...")
                continue
            else:
                logger.error(f"Error al iniciar el servidor: {str(e)}")
                print(f"\n❌ Error al iniciar el servidor Flask: {str(e)}")
                break
        except Exception as e:
            logger.error(f"Error al iniciar el servidor: {str(e)}")
            print(f"\n❌ Error al iniciar el servidor Flask: {str(e)}")
            print("Verifica la configuración del servidor.")
            break
        except KeyboardInterrupt:
            logger.info("Servidor detenido por el usuario")
            print("\n✅ Servidor detenido correctamente")
            break
    else:
        logger.error("❌ No se pudo iniciar el servidor en ninguno de los puertos disponibles")
        print("\n❌ Error: Todos los puertos están ocupados. Intenta cerrar otras aplicaciones o especificar un puerto manualmente.")

def run_production_server():
    """Ejecutar el servidor en modo producción usando Waitress"""
    try:
        import waitress
        app = main()
        if app:
            # Lista de puertos alternativos para probar
            puertos = [5000, 8080, 3000, 8000, 4000, 5001]
            
            for puerto in puertos:
                try:
                    logger.info(f"🚀 Iniciando servidor de producción con Waitress en http://0.0.0.0:{puerto}")
                    waitress.serve(app, host='0.0.0.0', port=puerto)
                    break
                except OSError as e:
                    if e.errno == 48 or "Address already in use" in str(e):
                        logger.warning(f"⚠️ Puerto {puerto} ocupado, intentando con el siguiente...")
                        continue
                    else:
                        logger.error(f"Error al iniciar el servidor: {str(e)}")
                        break
            else:
                logger.error("❌ No se pudo iniciar el servidor en ninguno de los puertos disponibles")
    except ImportError:
        logger.warning("⚠️ Waitress no está instalado. Para usar un servidor de producción ejecute:")
        logger.warning("   pip install waitress")
        # Fallback to development server
        run_server(main(), suppress_warnings=True)

# Modify your if __name__ == "__main__" block:
if __name__ == "__main__":
    import sys
    
    # Check for production mode
    if len(sys.argv) > 1 and sys.argv[1] == "--production":
        run_production_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "--no-warnings":
        app = main()
        if app:
            run_server(app, suppress_warnings=True)
    else:
        # Original behavior
        app = main()
        if app:
            run_server(app, suppress_warnings=False)