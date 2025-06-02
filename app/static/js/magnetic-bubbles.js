/**
 * MagneticBubbles - Componente interactivo para selección mediante burbujas
 * Versión corregida con interactividad restaurada
 */
class MagneticBubbles {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    
    // Aplicar pixel ratio para mejorar la resolución
    const pixelRatio = options.pixelRatio || window.devicePixelRatio || 1;
    if (pixelRatio > 1) {
      // Guardar tamaño actual del canvas
      const width = canvas.width;
      const height = canvas.height;
      
      // Establecer tamaño de canvas con alta resolución
      canvas.width = width * pixelRatio;
      canvas.height = height * pixelRatio;
      
      // Escalar el contexto para mantener tamaño visual pero aumentar resolución
      this.ctx.scale(pixelRatio, pixelRatio);
      
      // Establecer dimensiones CSS para mantener tamaño visual
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      
      console.log(`Canvas inicializado con ratio ${pixelRatio}: ${canvas.width}x${canvas.height} (visual: ${width}x${height})`);
    }
    
    // Opciones por defecto mejoradas
    this.options = {
      width: options.width || canvas.width / pixelRatio,
      height: options.height || canvas.height / pixelRatio,
      selectionMode: options.selectionMode || 'single',
      canvasBackground: options.canvasBackground || 'rgba(0, 0, 0, 0.8)',
      bubbleBaseColor: options.bubbleBaseColor || '#f97316',
      bubbleSelectedColor: options.bubbleSelectedColor || '#ea580c',
      textColor: options.textColor || '#ffffff',
      
      // Factores configurables para tamaño y comportamiento
      bubbleSizeFactor: options.bubbleSizeFactor || 0.12, // Factor relativo al tamaño del canvas
      minDistance: options.minDistance || 15, // Distancia mínima entre burbujas
      maxInitialVelocity: options.maxInitialVelocity || 3, // Velocidad inicial
      textScaleFactor: options.textScaleFactor || 1.0, // Factor de escala para texto
      friction: options.friction || 0.02, // Fricción para ralentizar movimiento
      attraction: options.attraction || 0.02, // Fuerza de atracción
    };
    
    // Datos de los items
    this.items = options.items || [];
    
    // Inicializar burbujas
    this.bubbles = [];
    this.initBubbles();
    
    // Estado de interacción
    this.mouse = { x: 0, y: 0, down: false };
    this.selectedBubble = null;
    this.hoveredBubble = null;
    this.isDragging = false;
    
    // Inicializar listeners - CRÍTICO para la interactividad
    this.initEventListeners();
    
    // Iniciar bucle de animación
    this.animate();
    
    // Indicar que la inicialización se completó correctamente
    console.log(`MagneticBubbles inicializado con ${this.bubbles.length} burbujas`);
  }
  
  // Inicializar burbujas con mejor distribución
  initBubbles() {
    const centerX = this.options.width / 2;
    const centerY = this.options.height / 2;
    
    // Calcular radio dinámicamente según el número de elementos
    const numItems = this.items.length;
    const minDimension = Math.min(this.options.width, this.options.height);
    
    // Calcular radio para distribución, ajustando según número de elementos
    const radius = minDimension * 0.35 * (1 + (numItems > 10 ? 0.2 : 0));
    
    // Crear burbujas con tamaño basado en el factor configurado
    this.items.forEach((item, index) => {
      // Distribuir en círculo con ángulo basado en el índice
      const angle = (index / numItems) * Math.PI * 2;
      
      // Añadir algo de variación al radio para evitar superposición
      const variationFactor = 0.85 + 0.3 * Math.random();
      const distance = radius * variationFactor;
      
      // Posición inicial con desplazamiento para que no todas estén en el mismo punto
      const x = centerX + Math.cos(angle) * distance;
      const y = centerY + Math.sin(angle) * distance;
      
      // Velocidad inicial más baja para movimiento más controlado
      const vx = (Math.random() - 0.5) * this.options.maxInitialVelocity;
      const vy = (Math.random() - 0.5) * this.options.maxInitialVelocity;
      
      // Tamaño basado en la dimensión mínima del canvas y factor configurable
      // Ajustar tamaño inversamente proporcional al número de elementos
      const sizeFactor = this.options.bubbleSizeFactor * (1 - (numItems > 8 ? 0.1 * (numItems-8)/8 : 0));
      const bubbleRadius = minDimension * sizeFactor;
      
      // Crear la burbuja con las nuevas propiedades
      this.bubbles.push({
        id: item.id,
        label: item.label,
        value: item.value || 1.0,
        x: x,
        y: y,
        vx: vx,
        vy: vy,
        radius: bubbleRadius,
        selected: false,
        selectionLevel: 0, // Para selección gradual
        hovered: false,
        originalRadius: bubbleRadius // Guardar radio original
      });
    });
  }
  
  // Inicializar los listeners de eventos para interacción con el canvas
  initEventListeners() {
    // IMPORTANTE: Usamos this.canvas, no document, para capturar eventos solo en este canvas
    
    // Mouse move
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = (e.clientX - rect.left);
      this.mouse.y = (e.clientY - rect.top);
      
      // Verificar hover
      let hoveredBubble = null;
      for (const bubble of this.bubbles) {
        const distance = Math.sqrt(
          Math.pow(this.mouse.x - bubble.x, 2) + 
          Math.pow(this.mouse.y - bubble.y, 2)
        );
        
        if (distance < bubble.radius) {
          hoveredBubble = bubble;
          break;
        }
      }
      
      // Actualizar estado de hover
      this.bubbles.forEach(bubble => {
        bubble.hovered = (bubble === hoveredBubble);
      });
      
      this.hoveredBubble = hoveredBubble;
      
      // Si estamos arrastrando, mover la burbuja seleccionada
      if (this.isDragging && this.selectedBubble) {
        this.selectedBubble.x = this.mouse.x;
        this.selectedBubble.y = this.mouse.y;
        this.selectedBubble.vx = 0;
        this.selectedBubble.vy = 0;
      }
    });
    
    // Mouse down - CRUCIAL para detectar clics
    this.canvas.addEventListener('mousedown', (e) => {
      e.preventDefault(); // Prevenir comportamiento predeterminado
      this.mouse.down = true;
      
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = (e.clientX - rect.left);
      this.mouse.y = (e.clientY - rect.top);
      
      // Verificar si hay una burbuja bajo el cursor
      let clickedBubble = null;
      for (const bubble of this.bubbles) {
        const distance = Math.sqrt(
          Math.pow(this.mouse.x - bubble.x, 2) + 
          Math.pow(this.mouse.y - bubble.y, 2)
        );
        
        if (distance < bubble.radius) {
          clickedBubble = bubble;
          break;
        }
      }
      
      // Si hay una burbuja, seleccionarla
      if (clickedBubble) {
        this.toggleSelection(clickedBubble);
        this.selectedBubble = clickedBubble;
        this.isDragging = true;
      } else {
        // Si se hace clic en el fondo, crear un "empujón" a todas las burbujas
        for (const bubble of this.bubbles) {
          const dx = bubble.x - this.mouse.x;
          const dy = bubble.y - this.mouse.y;
          const distance = Math.sqrt(dx*dx + dy*dy);
          
          // Aplicar fuerza inversamente proporcional a la distancia
          const force = 10 / (distance + 1);
          const angle = Math.atan2(dy, dx);
          
          bubble.vx += Math.cos(angle) * force;
          bubble.vy += Math.sin(angle) * force;
        }
      }
    });
    
    // Mouse up
    this.canvas.addEventListener('mouseup', (e) => {
      e.preventDefault(); // Prevenir comportamiento predeterminado
      this.mouse.down = false;
      this.isDragging = false;
      this.selectedBubble = null;
    });
    
    // Touch events para dispositivos móviles - CRUCIAL para móviles
    this.canvas.addEventListener('touchstart', (e) => {
      e.preventDefault(); // Prevenir scroll
      const touch = e.touches[0];
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = (touch.clientX - rect.left);
      this.mouse.y = (touch.clientY - rect.top);
      this.mouse.down = true;
      
      // Verificar si se tocó una burbuja
      let touchedBubble = null;
      for (const bubble of this.bubbles) {
        const distance = Math.sqrt(
          Math.pow(this.mouse.x - bubble.x, 2) + 
          Math.pow(this.mouse.y - bubble.y, 2)
        );
        
        if (distance < bubble.radius) {
          touchedBubble = bubble;
          break;
        }
      }
      
      if (touchedBubble) {
        this.toggleSelection(touchedBubble);
      } else {
        // Si se toca el fondo, crear un "empujón" a todas las burbujas
        for (const bubble of this.bubbles) {
          const dx = bubble.x - this.mouse.x;
          const dy = bubble.y - this.mouse.y;
          const distance = Math.sqrt(dx*dx + dy*dy);
          
          // Aplicar fuerza inversamente proporcional a la distancia
          const force = 10 / (distance + 1);
          const angle = Math.atan2(dy, dx);
          
          bubble.vx += Math.cos(angle) * force;
          bubble.vy += Math.sin(angle) * force;
        }
      }
    });
    
    this.canvas.addEventListener('touchmove', (e) => {
      e.preventDefault(); // Prevenir scroll
      const touch = e.touches[0];
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = (touch.clientX - rect.left);
      this.mouse.y = (touch.clientY - rect.top);
    });
    
    this.canvas.addEventListener('touchend', (e) => {
      e.preventDefault(); // Prevenir comportamiento predeterminado
      this.mouse.down = false;
    });
    
    // Listener para redimensionamiento
    window.addEventListener('resize', () => {
      this.handleResize();
    });
  }
  
  // Alternar selección de una burbuja
  toggleSelection(bubble) {
    if (this.options.selectionMode === 'single') {
      // En modo single, desseleccionar todas excepto la actual
      this.bubbles.forEach(b => {
        b.selected = (b === bubble);
      });
      
      // Emitir evento con solo esta burbuja seleccionada
      const selections = bubble.selected ? { [bubble.id]: bubble.value } : {};
      this.emitSelectionChangedEvent(selections);
    } else {
      // En modo múltiple, alternar esta burbuja y modificar nivel de selección
      if (!bubble.selected) {
        bubble.selected = true;
        bubble.selectionLevel = 0.25; // 1/4
      } else {
        bubble.selectionLevel += 0.25; // Aumentar en 1/4
        if (bubble.selectionLevel > 1) {
          bubble.selectionLevel = 0;
          bubble.selected = false;
        }
      }
      
      // Compilar todas las selecciones actuales
      const selections = {};
      this.bubbles.forEach(b => {
        if (b.selected) {
          selections[b.id] = b.value * b.selectionLevel * 4; // Normalizar a 0-1
        }
      });
      
      this.emitSelectionChangedEvent(selections);
    }
  }
  
  // Resto del código igual...
  
  // Dibujar todas las burbujas
  draw() {
    // Limpiar canvas con el color de fondo
    this.ctx.fillStyle = this.options.canvasBackground;
    this.ctx.fillRect(0, 0, this.options.width, this.options.height);
    
    // Dibujar cada burbuja
    for (const bubble of this.bubbles) {
      this.drawBubble(bubble);
    }
  }
  
  // Método mejorado para dibujar las burbujas con diseño moderno y elegante
  drawBubble(bubble) {
    const ctx = this.ctx;
    
    // Determinar colores base según estado
    const baseColor = this.options.bubbleBaseColor || '#f97316';
    const selectedColor = this.options.bubbleSelectedColor || '#ea580c';
    
    // Calcular tamaño según estado (seleccionado/hover)
    const normalRadius = bubble.radius;
    const hoverScale = bubble.hovered ? 1.05 : 1.0;
    const selectionScale = bubble.selected ? (1.0 + bubble.selectionLevel * 0.1) : 1.0;
    const finalRadius = normalRadius * hoverScale * selectionScale;
    
    // Determinar colores
    let fillColor;
    if (bubble.selected) {
      // Color para estado seleccionado - más intenso según nivel
      const intensity = 0.7 + (bubble.selectionLevel * 0.3);
      const r = Math.min(255, Math.round(parseInt(selectedColor.substr(1, 2), 16) * intensity));
      const g = Math.min(255, Math.round(parseInt(selectedColor.substr(3, 2), 16) * intensity));
      const b = Math.min(255, Math.round(parseInt(selectedColor.substr(5, 2), 16) * intensity));
      fillColor = `rgb(${r}, ${g}, ${b})`;
    } else {
      // Color para estado normal
      fillColor = bubble.hovered ? selectedColor : baseColor;
    }
    
    // Dibujar círculo principal
    ctx.beginPath();
    ctx.arc(bubble.x, bubble.y, finalRadius, 0, Math.PI * 2);
    
    // Relleno con gradiente sutil
    const gradient = ctx.createLinearGradient(
      bubble.x, bubble.y - finalRadius, 
      bubble.x, bubble.y + finalRadius
    );
    
    // Colores de gradiente más sutiles
    if (bubble.selected) {
      gradient.addColorStop(0, fillColor);
      gradient.addColorStop(1, this.adjustColor(fillColor, -15)); // Ligeramente más oscuro abajo
    } else {
      gradient.addColorStop(0, this.adjustColor(fillColor, 10)); // Ligeramente más claro arriba
      gradient.addColorStop(1, fillColor);
    }
    
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // Borde más elegante
    ctx.strokeStyle = bubble.selected ? 
                    "rgba(255, 255, 255, 0.5)" : 
                    "rgba(255, 255, 255, 0.2)";
    ctx.lineWidth = bubble.selected ? 1.5 : 0.5;
    ctx.stroke();
    
    // Texto con mejor legibilidad
    const fontSize = Math.max(12, Math.min(16, finalRadius * 0.45 * this.options.textScaleFactor));
    ctx.font = `${bubble.selected ? 'bold' : ''} ${fontSize}px "Segoe UI", -apple-system, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    
    // Texto con sombra sutil para mejor legibilidad
    ctx.fillStyle = this.options.textColor || "#ffffff";
    
    // Sombra muy sutil solo si es necesaria para legibilidad
    if (this.getBrightness(fillColor) > 150) { // Color claro necesita sombra para legibilidad
      ctx.shadowColor = "rgba(0, 0, 0, 0.3)";
      ctx.shadowBlur = 2;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 1;
    } else {
      ctx.shadowBlur = 0;
    }
    
    ctx.fillText(bubble.label, bubble.x, bubble.y);
    ctx.shadowBlur = 0;
    
    // Indicador de nivel de selección - minimalista
    if (bubble.selected && bubble.selectionLevel > 0) {
      const levels = 4; // 4 niveles posibles
      const activeLevel = Math.ceil(bubble.selectionLevel * levels);
      const indicatorSize = 3;
      const spacing = 6;
      const totalWidth = (levels * indicatorSize) + ((levels-1) * spacing);
      const startX = bubble.x - totalWidth/2 + indicatorSize/2;
      const y = bubble.y + finalRadius * 0.7;
      
      for (let i = 0; i < levels; i++) {
        ctx.beginPath();
        const x = startX + (i * (indicatorSize + spacing));
        ctx.rect(x - indicatorSize/2, y - indicatorSize/2, indicatorSize, indicatorSize);
        
        if (i < activeLevel) {
          ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
        } else {
          ctx.fillStyle = "rgba(255, 255, 255, 0.3)";
        }
        ctx.fill();
      }
    }
  }
  
  // Función auxiliar para ajustar el brillo de un color
  adjustColor(color, amount) {
    // Extraer componentes RGB
    let r, g, b;
    
    if (color.startsWith('#')) {
      r = parseInt(color.substr(1, 2), 16);
      g = parseInt(color.substr(3, 2), 16);
      b = parseInt(color.substr(5, 2), 16);
    } else {
      // Intentar con formato rgb
      const match = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (match) {
        r = parseInt(match[1]);
        g = parseInt(match[2]);
        b = parseInt(match[3]);
      } else {
        return color; // No se pudo analizar el color
      }
    }
    
    // Ajustar componentes
    r = Math.max(0, Math.min(255, r + amount));
    g = Math.max(0, Math.min(255, g + amount));
    b = Math.max(0, Math.min(255, b + amount));
    
    return `rgb(${r}, ${g}, ${b})`;
  }
  
  // Función para calcular el brillo de un color (0-255)
  getBrightness(color) {
    // Extraer componentes RGB
    let r, g, b;
    
    if (color.startsWith('#')) {
      r = parseInt(color.substr(1, 2), 16);
      g = parseInt(color.substr(3, 2), 16);
      b = parseInt(color.substr(5, 2), 16);
    } else {
      // Intentar con formato rgb
      const match = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (match) {
        r = parseInt(match[1]);
        g = parseInt(match[2]);
        b = parseInt(match[3]);
      } else {
        return 128; // Valor por defecto si no se puede analizar
      }
    }
    
    // Fórmula estándar para calcular brillo perceptivo
    return (r * 299 + g * 587 + b * 114) / 1000;
  }
  
  // Bucle de animación principal
  animate() {
    this.update();
    this.draw();
    requestAnimationFrame(() => this.animate());
  }

  // Emitir evento de cambio de selección
  emitSelectionChangedEvent(selections) {
    const event = new CustomEvent('selection-changed', {
      detail: { selections: selections }
    });
    this.canvas.dispatchEvent(event);
  }
  
  // Obtener selecciones actuales
  getSelections() {
    const selections = {};
    this.bubbles.forEach(bubble => {
      if (bubble.selected) {
        selections[bubble.id] = bubble.value * bubble.selectionLevel * 4; // Normalizar a 0-1
      }
    });
    return selections;
  }
  
  // Actualizar selecciones desde fuente externa
  updateSelections(selections) {
    if (!selections) return;
    
    // Resetear todas las burbujas primero
    this.bubbles.forEach(bubble => {
      bubble.selected = false;
      bubble.selectionLevel = 0;
    });
    
    // Aplicar las selecciones proporcionadas
    for (const id in selections) {
      const selectionValue = selections[id];
      const bubble = this.bubbles.find(b => b.id === id);
      
      if (bubble) {
        bubble.selected = true;
        bubble.selectionLevel = selectionValue / bubble.value / 4; // Convertir a escala 0-1
      }
    }
    
    // Forzar redibujado
    this.draw();
  }
  
  // Actualizar posiciones y velocidades de las burbujas
  update() {
    for (let i = 0; i < this.bubbles.length; i++) {
      const bubble = this.bubbles[i];
      
      // Saltar actualización si estamos arrastrando esta burbuja
      if (this.isDragging && bubble === this.selectedBubble) continue;
      
      // Aplicar velocidad a la posición
      bubble.x += bubble.vx;
      bubble.y += bubble.vy;
      
      // Aplicar fricción para ralentizar
      bubble.vx *= (1 - this.options.friction);
      bubble.vy *= (1 - this.options.friction);
      
      // MEJORADO: Rebote en los bordes del canvas con mayor elasticidad
      const restitution = 0.9; // Coeficiente de restitución (elasticidad del rebote)
      
      if (bubble.x - bubble.radius < 0) {
        bubble.x = bubble.radius + 1; // Evitar que quede atrapada en el borde
        bubble.vx = Math.abs(bubble.vx) * restitution;
      } else if (bubble.x + bubble.radius > this.options.width) {
        bubble.x = this.options.width - bubble.radius - 1;
        bubble.vx = -Math.abs(bubble.vx) * restitution;
      }
      
      if (bubble.y - bubble.radius < 0) {
        bubble.y = bubble.radius + 1;
        bubble.vy = Math.abs(bubble.vy) * restitution;
      } else if (bubble.y + bubble.radius > this.options.height) {
        bubble.y = this.options.height - bubble.radius - 1;
        bubble.vy = -Math.abs(bubble.vy) * restitution;
      }
      
      // Aplicar una fuerza hacia el centro si está muy lejos
      const centerX = this.options.width / 2;
      const centerY = this.options.height / 2;
      const dx = centerX - bubble.x;
      const dy = centerY - bubble.y;
      const distanceToCenter = Math.sqrt(dx*dx + dy*dy);
      
      if (distanceToCenter > this.options.width * 0.4) {
        bubble.vx += (dx / distanceToCenter) * this.options.attraction;
        bubble.vy += (dy / distanceToCenter) * this.options.attraction;
      }
      
      // MEJORADO: Prevenir solapamiento entre burbujas con mejor física
      for (let j = i + 1; j < this.bubbles.length; j++) {
        const otherBubble = this.bubbles[j];
        
        // Saltar si estamos arrastrando la otra burbuja
        if (this.isDragging && otherBubble === this.selectedBubble) continue;
        
        const dx = otherBubble.x - bubble.x;
        const dy = otherBubble.y - bubble.y;
        const distance = Math.sqrt(dx*dx + dy*dy);
        const minDistance = bubble.radius + otherBubble.radius;
        
        // Si hay colisión, aplicar rebote con física mejorada
        if (distance < minDistance) {
          // Calcular la profundidad de la colisión
          const angle = Math.atan2(dy, dx);
          const overlap = minDistance - distance;
          
          // Calcular vectores unitarios de dirección
          const nx = dx / distance;
          const ny = dy / distance;
          
          // Factor de corrección para evitar solapamiento completo
          const correctionFactor = 0.7; // Más alto = separación más fuerte
          
          // Mover las burbujas para evitar superposición con más fuerza
          const moveX = nx * overlap * 0.5 * correctionFactor;
          const moveY = ny * overlap * 0.5 * correctionFactor;
          
          if (!(this.isDragging && bubble === this.selectedBubble)) {
            bubble.x -= moveX;
            bubble.y -= moveY;
          }
          
          if (!(this.isDragging && otherBubble === this.selectedBubble)) {
            otherBubble.x += moveX;
            otherBubble.y += moveY;
          }
          
          // MEJORADO: Aplicar velocidad con conservación de momento e impulso
          const bounceForce = 0.25; // Aumentado para más rebote
          
          // Aplicar impulso a ambas burbujas en direcciones opuestas
          if (!(this.isDragging && bubble === this.selectedBubble)) {
            bubble.vx -= nx * bounceForce;
            bubble.vy -= ny * bounceForce;
            
            // Pequeña perturbación aleatoria para evitar burbujas "pegadas"
            bubble.vx += (Math.random() - 0.5) * 0.05;
            bubble.vy += (Math.random() - 0.5) * 0.05;
          }
          
          if (!(this.isDragging && otherBubble === this.selectedBubble)) {
            otherBubble.vx += nx * bounceForce;
            otherBubble.vy += ny * bounceForce;
            
            // Pequeña perturbación aleatoria para evitar burbujas "pegadas"
            otherBubble.vx += (Math.random() - 0.5) * 0.05;
            otherBubble.vy += (Math.random() - 0.5) * 0.05;
          }
        }
      }
    }
  }
  
  // Método para manejar redimensionamiento
  handleResize() {
    // Guardar selecciones actuales
    const currentSelections = this.getSelections();
    
    // Obtener nuevas dimensiones del contenedor
    if (this.canvas.parentElement) {
      const rect = this.canvas.parentElement.getBoundingClientRect();
      const newWidth = rect.width;
      const newHeight = rect.height;
      
      // No hacer nada si las dimensiones son muy pequeñas
      if (newWidth < 50 || newHeight < 50) return;
      
      console.log(`Redimensionando canvas: ${this.options.width}x${this.options.height} -> ${newWidth}x${newHeight}`);
      
      // Ratios de cambio para mantener posiciones relativas
      const ratioX = newWidth / this.options.width;
      const ratioY = newHeight / this.options.height;
      
      // Actualizar dimensiones del canvas
      this.canvas.style.width = `${newWidth}px`;
      this.canvas.style.height = `${newHeight}px`;
      
      // Calcular nuevo tamaño con pixel ratio para alta resolución
      const pixelRatio = window.devicePixelRatio || 1;
      this.canvas.width = newWidth * pixelRatio;
      this.canvas.height = newHeight * pixelRatio;
      
      // Actualizar opciones
      this.options.width = newWidth;
      this.options.height = newHeight;
      
      // Escalar contexto para mantener calidad
      this.ctx.scale(pixelRatio, pixelRatio);
      
      // Reposicionar burbujas
      this.bubbles.forEach(bubble => {
        bubble.x *= ratioX;
        bubble.y *= ratioY;
        
        // Recalcular tamaño de las burbujas
        const minDimension = Math.min(newWidth, newHeight);
        const numItems = this.bubbles.length;
        const sizeFactor = this.options.bubbleSizeFactor * (1 - (numItems > 8 ? 0.1 * (numItems-8)/8 : 0));
        bubble.radius = minDimension * sizeFactor;
        bubble.originalRadius = bubble.radius;
      });
      
      // Restaurar selecciones
      this.updateSelections(currentSelections);
    }
  }
}

// Exponer globalmente
window.MagneticBubbles = MagneticBubbles;

// Añadir detector de redimensionamiento de ventana para todas las instancias
window.addEventListener('resize', function() {
  if (window.estilosBubbles && typeof window.estilosBubbles.handleResize === 'function') {
    window.estilosBubbles.handleResize();
  }
  if (window.marcasBubbles && typeof window.marcasBubbles.handleResize === 'function') {
    window.marcasBubbles.handleResize();
  }
});

console.log("MagneticBubbles cargado correctamente. Clase disponible globalmente.");