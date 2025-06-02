/**
 * Script reorganizador del test - versión mínima
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Test reorganizer cargado');
    
    // Funcionalidad mínima para evitar errores
    if (typeof window.reorganizeTestQuestions === 'undefined') {
        window.reorganizeTestQuestions = function() {
            console.log('Reorganización de preguntas ejecutada');
        };
    }
});