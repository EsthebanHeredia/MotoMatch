/**
 * Test de preferencias de motos - Lógica principal
 */

console.log('Inicializando Test de Preferencias de Motos...');

// Inicialización global de respuestas
window.respuestas = {
  estilos: {},
  marcas: {}
};

// Estado general del test
const testState = {
  currentStageIndex: 0,
  stageContainers: [],
  stageIndicators: [],
  testResults: {},
  completionCallback: null
};

// Etapas configurables del test - Reordenadas para coincidir con el HTML
const testStages = [
  {
    id: 'pregunta-1',
    key: 'estilos',
    title: 'Estilos de Moto',
    description: 'Selecciona los estilos de moto que más te interesan',
    type: 'selector'
  },
  {
    id: 'pregunta-2',
    key: 'marcas',
    title: 'Marcas Preferidas', 
    description: 'Selecciona tus marcas favoritas o las que más te interesan',
    type: 'selector'
  },
  {
    id: 'pregunta-4',
    key: 'presupuesto',
    title: 'Rango de Presupuesto',
    description: '¿Cuál es tu rango de presupuesto?',
    type: 'range'
  },
  {
    id: 'pregunta-5',
    key: 'ano',
    title: 'Rango de Años',
    description: '¿Qué rango de años prefieres?',
    type: 'range'
  },
  {
    id: 'pregunta-6',
    key: 'peso',
    title: 'Rango de Peso',
    description: '¿Qué rango de peso prefieres?',
    type: 'range'
  },
  {
    id: 'pregunta-7',
    key: 'preferencia_potencia_peso',
    title: 'Relación Potencia/Peso',
    description: '¿Prefieres una moto con mejor relación potencia/peso?',
    type: 'select'
  },
  {
    id: 'pregunta-8',
    key: 'preferencia_rendimiento',
    title: 'Rendimiento vs Economía',
    description: '¿Te interesa más rendimiento o economía?',
    type: 'select'
  },
  {
    id: 'pregunta-uso-principal',
    key: 'uso_principal',
    title: 'Uso Principal',
    description: '¿Cuál será el uso principal de tu moto?',
    type: 'select'
  }
];

// Opciones para cada pregunta
const testOptions = {
  preferencia_potencia_peso: [
    { id: 'alta', label: 'Alta relación potencia/peso (más deportiva)' },
    { id: 'media', label: 'Relación media potencia/peso (equilibrada)' },
    { id: 'baja', label: 'Baja relación potencia/peso (más relajada)' }
  ],
  preferencia_rendimiento: [
    { id: 'rendimiento', label: 'Rendimiento (potencia, velocidad, aceleración)' },
    { id: 'economia', label: 'Economía (bajo consumo, mantenimiento económico)' },
    { id: 'balance', label: 'Balance entre rendimiento y economía' }
  ],
  uso_principal: [
    { id: 'ciudad', label: 'Ciudad/Commuting' },
    { id: 'paseo', label: 'Paseo/Ocio' },
    { id: 'mixto', label: 'Uso Mixto' }
  ]
};

// Función para inicializar el test
function initializeTest() {
  console.log('Inicializando test...');
  
  const existingStages = document.querySelectorAll('.pregunta');
  
  // Recolectar contenedores y configurar indicadores
  if (existingStages.length > 0) {
    // Usar los contenedores existentes en el HTML
    testState.stageContainers = Array.from(existingStages);
    
    // Configurar indicadores (si existen)
    testState.stageIndicators = Array.from(document.querySelectorAll('.stage-indicator'));
    
    // Configurar botones de navegación
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    
    if (prevBtn) {
      prevBtn.addEventListener('click', navigateToPreviousStage);
    }
    
    if (nextBtn) {
      nextBtn.addEventListener('click', navigateToNextStage);
    }
    
    // Configurar listeners para selects
    setupSelectListeners();
    
    // Inicializar los selectores de contadores
    const estilosContainer = document.getElementById('estilos-canvas');
    const marcasContainer = document.getElementById('marcas-canvas');
    
    if (estilosContainer) {
      setupBubblesSelector('estilos', estilosContainer);
    }
    
    if (marcasContainer) {
      setupBubblesSelector('marcas', marcasContainer);
    }
    
    // Inicializar estado
    window.testResults = {};
    
    // Configurar la primera pregunta como activa
    if (testState.stageContainers.length > 0) {
      testState.stageContainers[0].classList.add('active');
      updateProgressBar(0, getVisibleStagesCount());
    }
    
    console.log('Test inicializado con éxito');
  } else {
    console.warn('No se encontraron elementos de pregunta para inicializar el test');
  }
}

// Función para actualizar la barra de progreso
function updateProgressBar(current, total) {
  const progressBar = document.getElementById('progress-bar');
  if (progressBar) {
    const percentage = (current / (total - 1)) * 100;
    progressBar.style.width = `${percentage}%`;
  }
}

// Configurar listeners para los elementos select
function setupSelectListeners() {
  const selects = document.querySelectorAll('.pregunta select');
  selects.forEach(select => {
    select.addEventListener('change', function() {
      const stageKey = this.closest('.pregunta').getAttribute('data-key');
      const value = this.value;
      
      // Guardar el valor en respuestas
      window.respuestas = window.respuestas || {};
      window.respuestas[stageKey] = value;
      
      // Guardar en testResults para coherencia
      window.testResults = window.testResults || {};
      window.testResults[stageKey] = value;
      
      // Si es uso_principal, guardar también como uso y uso_previsto
      if (stageKey === 'uso_principal') {
        window.respuestas.uso = value;
        window.respuestas.uso_previsto = value;
        window.testResults.uso = value;
        window.testResults.uso_previsto = value;
      }
      
      console.log(`Seleccionado ${stageKey}: ${value}`);
    });
  });
}

// Exponer la función globalmente para que la template pueda usarla
window.initializeTest = initializeTest;

// Modificar el listener DOMContentLoaded para evitar inicialización duplicada
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM cargado. La inicialización se manejará por la plantilla HTML');
  // No inicializamos aquí para evitar duplicación, ya que la plantilla llamará a initializeTest
});

// Depuración adicional al cargar la página
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM cargado en test.js');
  console.log('Elementos de pregunta:', document.querySelectorAll('.pregunta').length);
  console.log('Botones de navegación:', {
    prev: document.getElementById('prev-btn'),
    next: document.getElementById('next-btn')
  });
  
  // Revisar si CounterSelector está disponible
  setTimeout(function() {
    console.log('CounterSelector disponible:', typeof window.CounterSelector === 'function');
    console.log('recuperarTest disponible:', typeof window.recuperarTest === 'function');
  }, 1000);
  
  // Asegurar que los contenedores tengan tamaño adecuado
  const contenedores = ['estilos-canvas', 'marcas-canvas'];
  contenedores.forEach(id => {
    const contenedor = document.getElementById(id);
    if (contenedor) {
      contenedor.style.minHeight = '300px';
      contenedor.style.minWidth = '100%';
    }
  });
});

// Configurar el contenido específico para cada etapa
function setupStageContent(stage, container) {
  const optionsContainer = container.querySelector(`#options-${stage.id}`);
  
  if (!optionsContainer) {
    console.error(`No se encontró el contenedor de opciones para la etapa ${stage.id}`);
    return;
  }
  
  // Diferentes configuraciones según el tipo de etapa
  switch(stage.id) {
    case 'experiencia':
    case 'presupuesto':
    case 'uso_principal':
      // Usar opciones básicas para estos tipos
      setupBasicOptions(stage.id, optionsContainer);
      break;

    case 'estilos_preferidos':
      // Configurar selector de contadores para estilos
      setupBubblesSelector('estilos', optionsContainer);
      break;

    case 'marcas_preferidas':
      // Configurar selector de contadores para marcas
      setupBubblesSelector('marcas', optionsContainer);
      break;

    default:
      console.warn(`Tipo de etapa no reconocido: ${stage.id}`);
  }
}

// Configurar opciones básicas (botones simples)
function setupBasicOptions(optionType, container) {
  const options = testOptions[optionType];
  
  if (!options) {
    console.error(`No se encontraron opciones para ${optionType}`);
    return;
  }
  
  const optionsHTML = options.map(option => {
    return `
      <div class="option-card" data-value="${option.id}">
        <i class="${option.icon}"></i>
        <span>${option.label}</span>
      </div>
    `;
  }).join('');
  
  container.innerHTML = optionsHTML;
  
  // Añadir evento de selección
  container.querySelectorAll('.option-card').forEach(card => {
    card.addEventListener('click', (e) => {
      // Remover selección previa
      container.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
      
      // Marcar como seleccionado
      card.classList.add('selected');
      
      // Guardar valor seleccionado
      const value = card.getAttribute('data-value');
      if (optionType === 'uso_principal') {
        window.respuestas.uso_principal = value;
        window.testResults.uso_principal = value;
      } else {
        window.respuestas[optionType] = value;
        window.testResults[optionType] = value;
      }
      
      console.log(`Seleccionado ${optionType}: ${value}`);
    });
  });
}

// Configurar selector de contadores para estilos y marcas
function setupBubblesSelector(type, container) {
  console.log(`Configurando selector de contadores para ${type}...`);
  
  if (!container) {
    console.error(`Contenedor para selección de ${type} no encontrado`);
    return;
  }
  
  // Limpiar el contenedor
  container.innerHTML = '';
  
  // Determinar opciones según el tipo
  let options = [];
  
  if (type === 'estilos') {
    options = [

      { id: 'naked', label: 'Naked', value: 1.0 },
      { id: 'sport', label: 'Deportiva', value: 1.0 },
      { id: 'scooter', label: 'Scooter', value: 1.0 },
      { id: 'trail', label: 'Adventure', value: 1.0 },
      { id: 'custom', label: 'Custom', value: 1.0 },
      { id: 'turismo', label: 'Touring', value: 1.0 },
      { id: 'supermotard', label: 'Supermoto', value: 1.0 },
      { id: 'electrica', label: 'Eléctrica', value: 1.0 },
      { id: 'enduro', label: 'Enduro', value: 1.0 },
      { id: 'quad-atv', label: 'Quad-atv', value: 1.0 },
      { id: 'cross', label: 'Cross', value: 1.0 },
      { id: 'infantil', label: 'Infantil', value: 1.0 }

    ];
  } else if (type === 'marcas') {
    options = [

      // Marcas japonesas principales
      { id: 'Honda', label: 'Honda', value: 1.0 },
      { id: 'Yamaha', label: 'Yamaha', value: 1.0 },
      { id: 'Suzuki', label: 'Suzuki', value: 1.0 },
      { id: 'Kawasaki', label: 'Kawasaki', value: 1.0 },

      // Marcas europeas principales
      { id: 'Ducati', label: 'Ducati', value: 1.0 },
      { id: 'BMW', label: 'BMW', value: 1.0 },
      { id: 'Triumph', label: 'Triumph', value: 1.0 },
      { id: 'KTM', label: 'KTM', value: 1.0 },
      { id: 'Husqvarna', label: 'Husqvarna', value: 1.0 },
      { id: 'GasGas', label: 'Gas Gas', value: 1.0 },
      { id: 'Aprilia', label: 'Aprilia', value: 1.0 },
      { id: 'MV Agusta', label: 'MV Agusta', value: 1.0 },
      { id: 'Moto Guzzi', label: 'Moto Guzzi', value: 1.0 },
      { id: 'Moto Guzzi', label: 'Moto Guzzi', value: 1.0 },
      { id: 'Benelli', label: 'Benelli', value: 1.0 },
      { id: 'MITT', label: 'MITT', value: 1.0 },
      { id: 'Bimota', label: 'Bimota', value: 1.0 },
      { id: 'Keeway', label: 'Keeway', value: 1.0 },
      { id: 'Piaggio', label: 'Piaggio', value: 1.0 },
      { id: 'Vespa', label: 'Vespa', value: 1.0 },

      // Marcas americanas
      { id: 'Harley-Davidson', label: 'Harley-Davidson', value: 1.0 },
      { id: 'Indian', label: 'Indian', value: 1.0 },

      // Marcas chinas/asiáticas
      { id: 'CFmoto', label: 'CFMoto', value: 1.0 },
      { id: 'KYMCO', label: 'Kymco', value: 1.0 },
      { id: 'Zontes', label: 'Zontes', value: 1.0 },
      { id: 'Voge', label: 'Voge', value: 1.0 },
      { id: 'SYM', label: 'SYM', value: 1.0 },

      // Marcas emergentes/otras
      { id: 'Royal Enfield', label: 'Royal Enfield', value: 1.0 }
      
    ];
  }
  
  // Inicializar CounterSelector con verificación
  if (typeof window.CounterSelector !== 'function') {
    console.error('Error crítico: CounterSelector no está disponible como función');
    
    // Mostrar un mensaje de error en el contenedor
    container.innerHTML = `
      <div class="error-message">
        <p>Error al cargar el componente de selección.</p>
        <button onclick="window.location.reload()">Recargar página</button>
      </div>
    `;
    return;
  }
  
  try {
    // Crear instancia del selector de contadores
    const counterSelector = new window.CounterSelector(container, {
      items: options,
      onChange: (selections) => {
        // Guardar selecciones en objeto global 'respuestas'
        window.respuestas = window.respuestas || {};
        window.respuestas[type] = selections;
        
        // También guardar en testResults para coherencia
        window.testResults = window.testResults || {};
        window.testResults[type] = selections;
        
        // Log para diagnóstico
        console.log(`Selecciones de ${type} actualizadas:`, selections);
      }
    });
    
    // Guardar referencia global para facilitar el acceso
    window[`${type}Selector`] = counterSelector;
    
    console.log(`Selector de contadores para ${type} inicializado correctamente`);
  } catch (error) {
    console.error(`Error al inicializar selector para ${type}:`, error);
    
    // Mostrar mensaje de error en el contenedor
    container.innerHTML = `
      <div class="error-message">
        <p>Error: ${error.message}</p>
        <button onclick="window.location.reload()">Recargar página</button>
      </div>
    `;
  }
}

// Navegación a la etapa anterior
function navigateToPreviousStage() {
  const currentIndex = testState.currentStageIndex;
  if (currentIndex <= 0) return;
  
  // Obtener clave de la etapa actual para guardar datos
  const currentStage = testState.stageContainers[currentIndex];
  const currentKey = currentStage.getAttribute('data-key');
  
  // Guardar selecciones actuales si es un selector de contadores
  if (currentStage.getAttribute('data-type') === 'selector' || currentStage.getAttribute('data-type') === 'bubbles') {
    const counterSelector = window[`${currentKey}Selector`];
    if (counterSelector) {
      window.respuestas[currentKey] = counterSelector.getSelections();
      window.testResults[currentKey] = counterSelector.getSelections();
    }
  }
  
  // Guardar datos de selects
  const select = currentStage.querySelector('select');
  if (select && select.value) {
    window.respuestas[currentKey] = select.value;
    window.testResults[currentKey] = select.value;
  }
  
  // Ocultar etapa actual
  currentStage.classList.remove('active');
  
  // Buscar la etapa anterior visible
  let prevIndex = findPreviousVisibleStage(currentIndex);
  if (prevIndex !== -1 && prevIndex >= 0) {
    // Obtener la rama activa según la selección del usuario
    const ramaTecnicaActiva = document.getElementById('interesa_especificaciones')?.value === 'si';
    const ramaPracticaActiva = document.getElementById('interesa_especificaciones')?.value === 'no';
    
    // Ocultar TODAS las preguntas de ambas ramas primero
    document.querySelectorAll('.rama-tecnica, .rama-practica').forEach(p => {
      p.classList.remove('active');
    });
    
    // Si es una pregunta de rama, verificar que sea de la rama correcta
    const prevStage = testState.stageContainers[prevIndex];
    if (prevStage.classList.contains('rama-tecnica') && !ramaTecnicaActiva) {
      console.error('Error de navegación: Intentando mostrar pregunta técnica pero la rama técnica no está activa');
      return; // No continuar si hay incoherencia
    } else if (prevStage.classList.contains('rama-practica') && !ramaPracticaActiva) {
      console.error('Error de navegación: Intentando mostrar pregunta práctica pero la rama práctica no está activa');
      return; // No continuar si hay incoherencia
    }
    
    // Mostrar etapa anterior
    prevStage.classList.add('active');
    testState.currentStageIndex = prevIndex;
    
    // Actualizar barra de progreso
    updateProgressBar(prevIndex, getVisibleStagesCount());
    
    // Habilitar/deshabilitar botones según corresponda
    document.getElementById('prev-btn').disabled = (prevIndex === 0);
    document.getElementById('next-btn').disabled = false;
    
    // Restaurar texto del botón siguiente si no es la última etapa
    if (!isLastVisibleStage(prevIndex)) {
      document.getElementById('next-btn').innerHTML = 'Siguiente <i class="fas fa-arrow-right"></i>';
    }
  }
  
  // Verificar integridad después de la navegación
  setTimeout(verificarYRestaurarCanvas, 100, 'navegación previa');
}

// Función para encontrar la etapa anterior visible
function findPreviousVisibleStage(currentIndex) {
  let prevIndex = currentIndex - 1;
  
  while (prevIndex >= 0) {
    const stage = testState.stageContainers[prevIndex];
    if (!stage.hasAttribute('data-hidden')) {
      return prevIndex;
    }
    prevIndex--;
  }
  
  return -1;
}

// Navegación a la siguiente etapa
function navigateToNextStage() {
  const currentIndex = testState.currentStageIndex;
  
  // Obtener clave de la etapa actual para guardar datos
  const currentStage = testState.stageContainers[currentIndex];
  const stageKey = currentStage.getAttribute('data-key');
  
  // Guardar selecciones actuales si es un selector de contadores
  if (currentStage.getAttribute('data-type') === 'selector' || currentStage.getAttribute('data-type') === 'bubbles') {
    const counterSelector = window[`${stageKey}Selector`];
    if (counterSelector) {
      window.respuestas[stageKey] = counterSelector.getSelections();
      window.testResults[stageKey] = counterSelector.getSelections();
    }
  }
  
  // Guardar datos de selects
  const select = currentStage.querySelector('select');
  if (select && select.value) {
    window.respuestas[stageKey] = select.value;
    window.testResults[stageKey] = select.value;
  }
  
  // Guardar datos de inputs (presupuesto)
  const inputs = currentStage.querySelectorAll('input');
  if (inputs.length > 0) {
    inputs.forEach(input => {
      if (input.name && input.value) {
        window.respuestas[input.name] = input.value;
        window.testResults[input.name] = input.value;
      }
    });
  }
  
  // Ocultar etapa actual
  currentStage.classList.remove('active');
  
  // Buscar la siguiente etapa visible
  let nextIndex = findNextVisibleStage(currentIndex);
  if (nextIndex !== -1 && nextIndex < testState.stageContainers.length) {
    // Obtener la rama activa según la selección del usuario
    const ramaTecnicaActiva = document.getElementById('interesa_especificaciones')?.value === 'si';
    const ramaPracticaActiva = document.getElementById('interesa_especificaciones')?.value === 'no';
    
    // Ocultar TODAS las preguntas de ambas ramas primero
    document.querySelectorAll('.rama-tecnica, .rama-practica').forEach(p => {
      p.classList.remove('active');
    });
    
    // Si es una pregunta de rama, verificar que sea de la rama correcta
    const nextStage = testState.stageContainers[nextIndex];
    if (nextStage.classList.contains('rama-tecnica') && !ramaTecnicaActiva) {
      console.error('Error de navegación: Intentando mostrar pregunta técnica pero la rama técnica no está activa');
      return; // No continuar si hay incoherencia
    } else if (nextStage.classList.contains('rama-practica') && !ramaPracticaActiva) {
      console.error('Error de navegación: Intentando mostrar pregunta práctica pero la rama práctica no está activa');
      return; // No continuar si hay incoherencia
    }
    
    // Mostrar siguiente etapa
    nextStage.classList.add('active');
    testState.currentStageIndex = nextIndex;
    
    // Actualizar barra de progreso
    updateProgressBar(nextIndex, getVisibleStagesCount());
    
    // Habilitar/deshabilitar botones según corresponda
    document.getElementById('prev-btn').disabled = false;
    document.getElementById('next-btn').disabled = false;
    
    // Si es la última etapa visible, cambiar texto del botón
    if (isLastVisibleStage(nextIndex)) {
      document.getElementById('next-btn').innerHTML = 'Finalizar <i class="fas fa-check"></i>';
    } else {
      document.getElementById('next-btn').innerHTML = 'Siguiente <i class="fas fa-arrow-right"></i>';
    }
  } else {
    // No hay más etapas, mostrar modal de finalización
    showCompletionModal();
  }
    // Verificar integridad después de la navegación
  setTimeout(verificarYRestaurarCanvas, 100, 'navegación siguiente');
  
  // Verificar si es la última pregunta de la rama activa para mostrar el botón de finalización
  if (isLastVisibleStage(testState.currentStageIndex)) {
    document.getElementById('next-btn').innerHTML = 'Finalizar <i class="fas fa-check"></i>';
    console.log('Llegando al final del test, mostrando botón de finalización');
  }
}

// Función para encontrar la siguiente etapa visible
function findNextVisibleStage(currentIndex) {
  let nextIndex = currentIndex + 1;
  
  while (nextIndex < testState.stageContainers.length) {
    const stage = testState.stageContainers[nextIndex];
    if (!stage.hasAttribute('data-hidden')) {
      return nextIndex;
    }
    nextIndex++;
  }
  
  return -1;
}

// Función para verificar si es la última etapa visible
function isLastVisibleStage(index) {
  return findNextVisibleStage(index) === -1;
}

// Función para contar etapas visibles
function getVisibleStagesCount() {
  return Array.from(testState.stageContainers).filter(stage => {
    return !stage.hasAttribute('data-hidden');
  }).length;
}

// Mostrar modal de finalización
function showCompletionModal() {
  // Transferir datos de selectores al testResults
  window.testResults = window.testResults || {};
  
  // Asegurar que las selecciones de contadores se transfieran
  if (window.respuestas && window.respuestas.estilos) {
    window.testResults.estilos = window.respuestas.estilos;
  }
  
  if (window.respuestas && window.respuestas.marcas) {
    window.testResults.marcas = window.respuestas.marcas;
  }
  
  // Asegurar que uso_principal se transfiera
  const usoPrincipalSelect = document.getElementById('uso_principal-select');
  if (usoPrincipalSelect && usoPrincipalSelect.value) {
    const usoValue = usoPrincipalSelect.value;
    window.testResults.uso_principal = usoValue;
    window.testResults.uso = usoValue;
    window.testResults.uso_previsto = usoValue;
  }
  
  // Usar el modal existente en el HTML en lugar de crearlo
  const modal = document.getElementById('completion-modal');
  if (!modal) {
    console.error('Modal de finalización no encontrado en el HTML');
    return;
  }
  
  // Asegurar que el botón del modal llame a la función correcta
  const finishButton = modal.querySelector('button');
  if (finishButton) {
    // Limpiar listeners existentes
    const newButton = finishButton.cloneNode(true);
    finishButton.parentNode.replaceChild(newButton, finishButton);
    
    // Añadir nuevo listener
    newButton.addEventListener('click', () => {
      // Asegurar que los datos de uso se incluyan en el envío final
      const testData = {
        ...window.testResults,
        uso: window.testResults.uso_principal || window.testResults.uso || '',
        uso_previsto: window.testResults.uso_principal || window.testResults.uso_previsto || ''
      };
      
      if (typeof testState.completionCallback === 'function') {
        testState.completionCallback(testData);
      } else {
        console.log('Test finalizado. Datos:', testData);
      }
    });
  }
  
  // Mostrar modal
  modal.style.display = 'flex';
}

// Reemplazar estas funciones para que usen CounterSelector en lugar de burbujas

function inicializarSoloEstilos() {
  setupBubblesSelector('estilos', document.getElementById('estilos-canvas'));
}

function inicializarSoloMarcas() {
  setupBubblesSelector('marcas', document.getElementById('marcas-canvas'));
}

// También añadir esta función para verificar y restaurar el estado
function verificarYRestaurarCanvas(origen) {
  const estilosCanvas = document.getElementById('estilos-canvas');
  const marcasCanvas = document.getElementById('marcas-canvas');
  
  if (estilosCanvas) {
    setupBubblesSelector('estilos', estilosCanvas);
  }
  
  if (marcasCanvas) {
    setupBubblesSelector('marcas', marcasCanvas);
  }
  
  console.log(`Canvas restaurados desde: ${origen}`);
}

// Eliminar las funciones de ramificación que ya no se usan
function hideAllBranchQuestions() {
  // Esta función ya no se usa, pero la mantenemos vacía por compatibilidad
  console.log('La ramificación ya no está en uso');
}

// Llamar a esta función al inicio
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(hideAllBranchQuestions, 100);
});

// Exponer funciones globalmente para que sean accesibles desde otros scripts
window.inicializarSoloEstilos = inicializarSoloEstilos;
window.inicializarSoloMarcas = inicializarSoloMarcas;
window.verificarYRestaurarCanvas = verificarYRestaurarCanvas;

// Añadir el manejador para uso_principal
document.addEventListener('DOMContentLoaded', function() {
  const usoPrincipalSelect = document.getElementById('uso_principal-select');
  
  if (usoPrincipalSelect) {
    usoPrincipalSelect.addEventListener('change', function() {
      const value = this.value;
      
      // Actualizar en ambos objetos globales
      window.respuestas = window.respuestas || {};
      window.respuestas.uso_principal = value;
      window.respuestas.uso = value;
      window.respuestas.uso_previsto = value;
      
      window.testResults = window.testResults || {};
      window.testResults.uso_principal = value;
      window.testResults.uso = value;
      window.testResults.uso_previsto = value;
      
      console.log('Uso principal actualizado:', value);
    });
  }
});
