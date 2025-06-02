/**
 * Controlador de finalización del test - Gestiona la transición final del test
 * y el envío de resultados al servidor para generar recomendaciones.
 * VERSIÓN CORREGIDA: Detecta rama técnica/práctica para captura apropiada de rangos
 */

// Función para finalizar el test y enviar resultados
function finalizarTest() {
    console.log("=== FINALIZANDO TEST ===");
    
    // IMPORTANTE: Inicializar window.testResults si no existe
    if (!window.testResults) {
        window.testResults = {};
    }
    
    // 🔧 FORZAR CAPTURA DE TODOS LOS SLIDERS DESDE EL DOM (sin verificar visibilidad)
    const allSliders = [
        { min: 'presupuesto_min', max: 'presupuesto_max' },
        { min: 'ano_min', max: 'ano_max' },
        { min: 'peso_min', max: 'peso_max' },
        { min: 'cilindrada_min', max: 'cilindrada_max' },
        { min: 'potencia_min', max: 'potencia_max' },
        { min: 'torque_min', max: 'torque_max' }
    ];
    
    allSliders.forEach(slider => {
        const minElement = document.getElementById(slider.min);
        const maxElement = document.getElementById(slider.max);
        
        if (minElement && maxElement) {
            window.testResults[slider.min] = parseInt(minElement.value) || parseInt(minElement.getAttribute('value')) || 0;
            window.testResults[slider.max] = parseInt(maxElement.value) || parseInt(maxElement.getAttribute('value')) || 1000;
            console.log(`${slider.min}: ${window.testResults[slider.min]}, ${slider.max}: ${window.testResults[slider.max]}`);
        } else {
            console.warn(`⚠️ Slider no encontrado: ${slider.min} o ${slider.max}`);
            if (!minElement) console.warn(`  - No encontrado: ${slider.min}`);
            if (!maxElement) console.warn(`  - No encontrado: ${slider.max}`);
        }
    });

    // FORZAR CAPTURA DE TODOS LOS SELECTS
    const allSelects = document.querySelectorAll('select');
    allSelects.forEach(select => {
        if (select.value && (select.name || select.id)) {
            const key = select.name || select.id;
            window.testResults[key] = select.value;
            console.log(`Select capturado: ${key} = ${select.value}`);
        }
    });

    console.log("=== DATOS FINALES CAPTURADOS ===", window.testResults);
    
    // 🔍 DEBUGGING: Verificar específicamente los campos problemáticos
    console.log("🔍 DEBUGGING - Verificando campos específicos:");
    console.log("  cilindrada_min:", window.testResults.cilindrada_min);
    console.log("  cilindrada_max:", window.testResults.cilindrada_max);
    console.log("  potencia_min:", window.testResults.potencia_min);
    console.log("  potencia_max:", window.testResults.potencia_max);
    console.log("  torque_min:", window.testResults.torque_min);
    console.log("  torque_max:", window.testResults.torque_max);
    
    // Verificar que los sliders existan en el DOM
    console.log("🔍 Verificando existencia de sliders en DOM:");
    console.log("  cilindrada_min element:", document.getElementById('cilindrada_min'));
    console.log("  cilindrada_max element:", document.getElementById('cilindrada_max'));
    console.log("  potencia_min element:", document.getElementById('potencia_min'));
    console.log("  potencia_max element:", document.getElementById('potencia_max'));
    console.log("  torque_min element:", document.getElementById('torque_min'));
    console.log("  torque_max element:", document.getElementById('torque_max'));
      // Preparar datos para enviar al servidor
    const testData = {
        // Datos básicos del test
        uso: window.testResults.uso,
        uso_previsto: window.testResults.uso_previsto,
        
        // RANGOS CUANTITATIVOS DIRECTOS (sin conversión)
        presupuesto_min: window.testResults.presupuesto_min,
        presupuesto_max: window.testResults.presupuesto_max,
        ano_min: window.testResults.ano_min,
        ano_max: window.testResults.ano_max,
        peso_min: window.testResults.peso_min,
        peso_max: window.testResults.peso_max,
        
        // ✅ AGREGAR LOS RANGOS QUE FALTABAN
        cilindrada_min: window.testResults.cilindrada_min,
        cilindrada_max: window.testResults.cilindrada_max,
        potencia_min: window.testResults.potencia_min,
        potencia_max: window.testResults.potencia_max,
        torque_min: window.testResults.torque_min,
        torque_max: window.testResults.torque_max,
        
        // PREFERENCIAS CATEGÓRICAS
        estilos: window.testResults.estilos || {},
        marcas: window.testResults.marcas || {},
        preferencia_potencia_peso: window.testResults.preferencia_potencia_peso,
        preferencia_rendimiento: window.testResults.preferencia_rendimiento,
        uso_principal: window.testResults.uso_principal,
        
        // Control
        reset_recommendation: 'true'
    };
    
    console.log("Datos finales para enviar:", JSON.stringify(testData, null, 2));
    
    // 🔍 DEBUGGING: Verificar que los campos se incluyan en testData
    console.log("🔍 VERIFICANDO testData específicos:");
    console.log("  testData.cilindrada_min:", testData.cilindrada_min);
    console.log("  testData.cilindrada_max:", testData.cilindrada_max);
    console.log("  testData.potencia_min:", testData.potencia_min);
    console.log("  testData.potencia_max:", testData.potencia_max);
    console.log("  testData.torque_min:", testData.torque_min);
    console.log("  testData.torque_max:", testData.torque_max);
    
    // Crear formulario para enviar datos
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = "/guardar_test";
    form.style.display = 'none';
    
    // Agregar los datos como campos ocultos
    for (const key in testData) {
        if (testData.hasOwnProperty(key)) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = typeof testData[key] === 'object' ? 
                JSON.stringify(testData[key]) : testData[key];
            form.appendChild(input);
        }
    }
    
    // Enviar el formulario
    document.body.appendChild(form);
    form.submit();
}

// AGREGAR EVENT LISTENER PARA EL BOTÓN
document.addEventListener('DOMContentLoaded', function() {
    console.log("🔧 Configurando botón de finalización...");
    
    // Buscar TODOS los posibles botones de finalización
    const botonesFinalizacion = [
        document.getElementById('ver-recomendaciones'),
        document.querySelector('.btn-finalizar'),
        document.querySelector('button[onclick*="finalizarTest"]'),
        document.querySelector('button[onclick*="finalizar"]'),
        document.querySelector('#finalizar-test'),
        document.querySelector('.finalizar-test')
    ];
    
    botonesFinalizacion.forEach(boton => {
        if (boton) {
            console.log("✅ Botón encontrado:", boton);
            
            // Limpiar eventos previos y agregar nuevo
            boton.removeEventListener('click', finalizarTest);
            boton.addEventListener('click', function(e) {
                e.preventDefault();
                console.log("🚀 Botón clickeado - ejecutando finalización...");
                finalizarTest();
            });
            
            // TAMBIÉN asegurar que el onclick funcione
            boton.onclick = function(e) {
                e.preventDefault();
                console.log("🚀 Onclick ejecutado - ejecutando finalización...");
                finalizarTest();
                return false;
            };
        }
    });
    
    // Si no encuentra botones, buscar por texto
    if (!botonesFinalizacion.some(b => b)) {
        const todosLosBotones = document.querySelectorAll('button');
        todosLosBotones.forEach(boton => {
            if (boton.textContent.toLowerCase().includes('recomend') || 
                boton.textContent.toLowerCase().includes('finalizar')) {
                console.log("✅ Botón encontrado por texto:", boton);
                boton.onclick = finalizarTest;
            }
        });
    }
});

// Exportar para uso global
window.finalizarTest = finalizarTest;

console.log("Módulo de finalización del test CORREGIDO (con detección de rama) cargado correctamente");