/**
 * Counter Selector - Componente para selección mediante contadores
 * Reemplazo para MagneticBubbles con interfaz más simple y consistente
 */
class CounterSelector {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      items: options.items || [],
      onChange: options.onChange || function() {}
    };
    
    // Estado de selecciones
    this.selections = {};
    
    // Renderizar interfaz inicial
    this.render();
  }
  
  // Renderizar toda la interfaz
  render() {
    // Limpiar contenedor
    this.container.innerHTML = '';
    this.container.className = 'counter-selector-container';
    
    // Crear lista de elementos
    const list = document.createElement('ul');
    list.className = 'counter-items-list';
    
    // Agregar cada elemento
    this.options.items.forEach(item => {
      const listItem = document.createElement('li');
      listItem.className = 'counter-item';
      listItem.dataset.id = item.id;
      
      // Mostrar etiqueta
      const label = document.createElement('span');
      label.className = 'counter-item-label';
      label.textContent = item.label;
      
      // Controles del contador
      const controls = document.createElement('div');
      controls.className = 'counter-controls';
      
      // Botón de disminuir
      const minusBtn = document.createElement('button');
      minusBtn.className = 'counter-btn counter-btn-minus';
      minusBtn.textContent = '-';
      minusBtn.disabled = true; // Inicialmente deshabilitado (contador en 0)
      
      // Valor del contador
      const valueDisplay = document.createElement('span');
      valueDisplay.className = 'counter-value';
      valueDisplay.textContent = '0';
      
      // Botón de aumentar
      const plusBtn = document.createElement('button');
      plusBtn.className = 'counter-btn counter-btn-plus';
      plusBtn.textContent = '+';
      
      // Agregar elementos al DOM
      controls.appendChild(minusBtn);
      controls.appendChild(valueDisplay);
      controls.appendChild(plusBtn);
      
      listItem.appendChild(label);
      listItem.appendChild(controls);
      list.appendChild(listItem);
      
      // Configurar eventos
      plusBtn.addEventListener('click', () => this.incrementCounter(item.id, valueDisplay, minusBtn, plusBtn));
      minusBtn.addEventListener('click', () => this.decrementCounter(item.id, valueDisplay, minusBtn, plusBtn));
    });
    
    this.container.appendChild(list);
  }
  
  // Incrementar contador
  incrementCounter(id, valueDisplay, minusBtn, plusBtn) {
    const currentValue = parseInt(valueDisplay.textContent) || 0;
    if (currentValue < 4) {
      const newValue = currentValue + 1;
      valueDisplay.textContent = newValue;
      minusBtn.disabled = false;
      
      if (newValue === 4) {
        plusBtn.disabled = true;
      }
      
      this.updateSelection(id, newValue);
    }
  }
  
  // Decrementar contador
  decrementCounter(id, valueDisplay, minusBtn, plusBtn) {
    const currentValue = parseInt(valueDisplay.textContent) || 0;
    if (currentValue > 0) {
      const newValue = currentValue - 1;
      valueDisplay.textContent = newValue;
      plusBtn.disabled = false;
      
      if (newValue === 0) {
        minusBtn.disabled = true;
        this.removeSelection(id);
      } else {
        this.updateSelection(id, newValue);
      }
    }
  }
  
  // Actualizar selección
  updateSelection(id, level) {
    // Encontrar el item correspondiente
    const item = this.options.items.find(item => item.id === id);
    if (!item) return;
    
    // Normalizar valor (0-4) a un valor para el algoritmo
    const value = item.value || 1.0;
    this.selections[id] = value * (level / 4);
    
    // Emitir evento de cambio
    this.emitChangeEvent();
  }
  
  // Eliminar selección
  removeSelection(id) {
    if (this.selections[id]) {
      delete this.selections[id];
      this.emitChangeEvent();
    }
  }
  
  // Emitir evento de cambio
  emitChangeEvent() {
    this.options.onChange(this.selections);
    
    // Mantener compatibilidad con el código existente
    const event = new CustomEvent('selection-changed', {
      detail: { selections: this.selections }
    });
    this.container.dispatchEvent(event);
  }
  
  // Obtener selecciones actuales
  getSelections() {
    return {...this.selections};
  }
  
  // Actualizar selecciones desde fuente externa
  updateSelections(selections) {
    if (!selections) return;
    
    this.selections = {...selections};
    
    // Actualizar la interfaz para reflejar las selecciones
    const listItems = this.container.querySelectorAll('.counter-item');
    listItems.forEach(item => {
      const id = item.dataset.id;
      const valueDisplay = item.querySelector('.counter-value');
      const minusBtn = item.querySelector('.counter-btn-minus');
      const plusBtn = item.querySelector('.counter-btn-plus');
      
      if (selections[id]) {
        // Encontrar el nivel (0-4) basado en el valor
        const itemObj = this.options.items.find(i => i.id === id);
        const baseValue = itemObj ? itemObj.value || 1.0 : 1.0;
        const level = Math.round((selections[id] / baseValue) * 4);
        
        valueDisplay.textContent = level;
        minusBtn.disabled = level === 0;
        plusBtn.disabled = level === 4;
      } else {
        valueDisplay.textContent = '0';
        minusBtn.disabled = true;
        plusBtn.disabled = false;
      }
    });
  }
}

// Exponer globalmente
window.CounterSelector = CounterSelector;