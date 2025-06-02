/**
 * Panel de debug - versión mínima
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🐛 Debug panel cargado (modo mínimo)');
    
    // Crear funciones globales para evitar errores
    if (typeof window.debugPanel === 'undefined') {
        window.debugPanel = {
            log: function(message) {
                console.log('[DEBUG]:', message);
            },
            error: function(message) {
                console.error('[DEBUG ERROR]:', message);
            },
            show: function() {
                console.log('Debug panel mostrado');
            },
            hide: function() {
                console.log('Debug panel oculto');
            }
        };
    }
});