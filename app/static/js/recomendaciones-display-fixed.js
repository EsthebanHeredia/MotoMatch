/**
 * Script para gestionar las recomendaciones de motos
 * Versión simplificada y optimizada (31-Mayo-2025)
 */

document.addEventListener("DOMContentLoaded", () => {
    console.log("🏍️ Inicializando gestor de recomendaciones...");
    
    // Obtener datos de recomendaciones de múltiples fuentes
    let motosRecomendadas = [];
    
    // 1. Intentar desde window.motosRecomendadas 
    if (window.motosRecomendadas && Array.isArray(window.motosRecomendadas) && window.motosRecomendadas.length > 0) {
        console.log("✅ Recomendaciones desde window.motosRecomendadas:", window.motosRecomendadas.length);
        motosRecomendadas = window.motosRecomendadas;
    } 
    // 2. Intentar desde elemento JSON embebido
    else {
        const jsonElement = document.getElementById('recommendations-data');
        if (jsonElement && jsonElement.textContent) {
            try {
                const parsedData = JSON.parse(jsonElement.textContent);
                if (Array.isArray(parsedData) && parsedData.length > 0) {
                    console.log("✅ Recomendaciones desde JSON embebido:", parsedData.length);
                    motosRecomendadas = parsedData;
                }
            } catch (error) {
                console.error("❌ Error parseando JSON embebido:", error);
            }
        }
    }
    
    // 3. Buscar contenedor principal
    let gridContainer = document.querySelector('.grid-container');
    if (!gridContainer) {
        gridContainer = document.getElementById('main-grid');
    }
    
    if (!gridContainer) {
        console.error("❌ No se encontró contenedor para mostrar recomendaciones");
        // Intentar crear uno
        const mainContainer = document.querySelector('.main-container');
        if (mainContainer) {
            gridContainer = document.createElement('div');
            gridContainer.className = 'grid-container';
            gridContainer.id = 'main-grid';
            mainContainer.appendChild(gridContainer);
            console.log("✅ Contenedor creado dinámicamente");
        } else {
            return;
        }
    }
    
    // Limpiar contenedor principal
    gridContainer.innerHTML = '';
    
    // Procesar recomendaciones
    processRecommendations(motosRecomendadas, gridContainer);
});

function processRecommendations(motosRecomendadas, container) {
    // Si no hay recomendaciones, mostrar mensaje
    if (!motosRecomendadas || motosRecomendadas.length === 0) {
        console.warn("⚠️ No hay recomendaciones para mostrar");
        container.innerHTML = `
            <div class="no-recommendations">
                <i class="fas fa-exclamation-circle"></i>
                <h3>No hay recomendaciones disponibles</h3>
                <p>Por favor completa el test de preferencias para obtener recomendaciones personalizadas.</p>
                <a href="/test" class="nav-button">Hacer el test</a>
            </div>
        `;
        return;
    }
    
    console.log(`🎯 Procesando ${motosRecomendadas.length} recomendaciones`);
    
    // Renderizar cada moto
    motosRecomendadas.forEach((moto, index) => {
        console.log(`📝 Procesando moto ${index + 1}:`, moto);
        
        const motoCard = document.createElement('div');
        motoCard.className = 'moto-card';
        motoCard.style.opacity = "0";
        motoCard.style.transform = "translateY(20px)";
        motoCard.style.transition = "all 0.5s ease";
        
        // Extraer datos con diferentes formatos posibles
        let motoData = {};
        
        // Si la moto es un objeto directo
        if (typeof moto === 'object' && moto !== null) {
            motoData = {
                moto_id: moto.moto_id || moto.id || index,
                marca: moto.marca || 'Marca Desconocida',
                modelo: moto.modelo || 'Modelo Desconocido',
                precio: moto.precio || 0,
                año: moto.anio || moto.año || moto.anyo || 'N/D',
                cilindrada: moto.cilindrada || 'N/D',
                potencia: moto.potencia || 'N/D',
                tipo: moto.tipo || moto.estilo || 'N/D',
                imagen: moto.imagen || '/static/images/default-moto.jpg',
                score: moto.score || 0,
                reasons: moto.reasons || moto.razones || ['Recomendación personalizada'],
                url: moto.URL || moto.url || moto.link || '#'
            };
        }
        
        // Formatear valores para mostrar
        const precioFormateado = motoData.precio ? `€${Number(motoData.precio).toLocaleString()}` : 'Precio no disponible';
        const cilindradaFormateada = motoData.cilindrada !== 'N/D' ? `${motoData.cilindrada} cc` : 'N/D';
        const potenciaFormateada = motoData.potencia !== 'N/D' ? `${motoData.potencia} CV` : 'N/D';
        const scoreFormateado = typeof motoData.score === 'number' ? Math.round(motoData.score * 100) : 0;
        
        // Asegurar que reasons es un array
        let reasons = [];
        if (Array.isArray(motoData.reasons)) {
            reasons = motoData.reasons;
        } else if (typeof motoData.reasons === 'string') {
            reasons = [motoData.reasons];
        } else {
            reasons = ['Recomendación personalizada basada en tus preferencias'];
        }
        
        // Crear HTML de la tarjeta
        motoCard.innerHTML = `
            <div class="moto-image-container">
                <img src="${motoData.imagen}" 
                     alt="$${motoData.modelo}" 
                     class="moto-img" 
                     onerror="this.src='/static/images/default-moto.jpg'; console.log('Error cargando imagen:', this.getAttribute('src'));">
            </div>
            
            <div class="moto-info">
                <h3 class="moto-title"> ${motoData.modelo}</h3>
                
                <div class="moto-specs">
                    <p><strong>Año:</strong> ${motoData.año}</p>
                    <p><strong>Tipo:</strong> ${motoData.tipo}</p>
                    <p><strong>Cilindrada:</strong> ${cilindradaFormateada}</p>
                    <p><strong>Potencia:</strong> ${potenciaFormateada}</p>
                    <p><strong>Precio:</strong> ${precioFormateado}</p>
                </div>
                
                <div class="match-score">
                    <span class="score-label">Coincidencia:</span>
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${scoreFormateado}%;"></div>
                    </div>
                    <span class="score-percentage">${scoreFormateado}%</span>
                </div>
                
                <div class="reasons-container">
                    <h4>¿Por qué te recomendamos esta moto?</h4>
                    <ul class="reasons-list">
                        ${reasons.map(reason => `<li><i class="fas fa-check-circle"></i> ${reason}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="moto-actions">
                    <button class="btn-moto-ideal" onclick="marcarComoIdeal('${motoData.moto_id}', '${motoData.marca}', '${motoData.modelo}')">
                        <i class="fas fa-star"></i> Moto Ideal
                    </button>
                    <button class="btn-favorita" data-moto-id="${motoData.moto_id}">
                        <i class="far fa-heart"></i> Me gusta
                    </button>
                    <button class="btn-detalles" onclick="window.open('${motoData.url}', '_blank')">
                        <i class="fas fa-info-circle"></i> Ver detalles
                    </button>
                </div>
            </div>
        `;
        
        // Añadir al contenedor
        container.appendChild(motoCard);
        
        // Animación de entrada escalonada
        setTimeout(() => {
            motoCard.style.opacity = "1";
            motoCard.style.transform = "translateY(0)";
        }, index * 150);
        
        // Event listener para botones de like - ACTUALIZADO para usar la misma lógica que populares.html
        motoCard.querySelector('.btn-favorita').addEventListener('click', function(e) {
            e.preventDefault();
            
            const motoId = this.getAttribute('data-moto-id');
            
            if (!motoId) {
                console.error('❌ No se encontró el ID de la moto');
                showNotification('Error: No se pudo identificar la moto', 'error');
                return;
            }
            
            console.log(`🔄 Procesando like para moto: ${motoId}`);
            
            // Deshabilitar botón temporalmente
            this.disabled = true;
            this.style.opacity = '0.6';
            
            // Enviar like usando la misma implementación que populares.html
            fetch('/dar_like_moto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ moto_id: motoId })
            })
            .then(response => response.json())
            .then(data => {
                console.log('📡 Respuesta del servidor:', data);
                
                if (data.success) {
                    // Toggle del estado del like basado en la respuesta o estado actual
                    const isCurrentlyLiked = this.classList.contains('liked');
                    
                    if (data.action === 'liked' || (!data.action && !isCurrentlyLiked)) {
                        this.classList.add('liked');
                        this.innerHTML = '<i class="fas fa-heart"></i> Te gusta';
                        showNotification('¡Like registrado!', 'success');
                    } else if (data.action === 'unliked' || (!data.action && isCurrentlyLiked)) {
                        this.classList.remove('liked');
                        this.innerHTML = '<i class="far fa-heart"></i> Me gusta';
                        showNotification('Like removido', 'success');
                    } else {
                        // Fallback para respuestas sin action
                        this.classList.add('liked');
                        this.innerHTML = '<i class="fas fa-heart"></i> Te gusta';
                        showNotification(data.message || '¡Like registrado!', 'success');
                    }
                } else {
                    showNotification('Error: ' + (data.error || 'Error desconocido'), 'error');
                }
            })
            .catch(error => {
                console.error('❌ Error:', error);
                showNotification('Error de conexión', 'error');
            })
            .finally(() => {
                this.disabled = false;
                this.style.opacity = '1';
            });
        });
    });
    
    console.log(`✅ ${motosRecomendadas.length} recomendaciones renderizadas correctamente`);
}

// Funciones para manejar acciones de las motos
function marcarComoIdeal(motoId, marca, modelo) {
    console.log(`⭐ Marcando moto ${motoId} (${marca} ${modelo}) como ideal`);
    
    // Buscar el botón para deshabilitar temporalmente
    const button = document.querySelector(`button[onclick*="${motoId}"][onclick*="marcarComoIdeal"]`);
    
    if (button) {
        // Deshabilitar botón temporalmente
        button.disabled = true;
        button.style.opacity = '0.6';
        
        // Cambiar texto temporalmente
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Marcando...';
    }
    
    // Enviar solicitud al servidor
    fetch('/marcar_moto_ideal', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            moto_id: motoId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Notificación de éxito usando showNotification
            showNotification(`¡${marca} ${modelo} marcada como tu moto ideal!`, 'success');
            
            // Cambiar el estilo del botón para indicar que está seleccionada
            if (button) {
                button.innerHTML = '<i class="fas fa-star"></i> ¡Moto Ideal!';
                button.classList.add('btn-ideal-selected');
                button.style.background = '#ffd700'; // Color dorado
                button.style.color = '#000';
                button.style.borderColor = '#ffd700';
                // Mantener deshabilitado para evitar clics múltiples
                button.disabled = true;
                button.style.opacity = '1';
            }
        } else {
            // Notificación de error usando showNotification
            showNotification(`Error: ${data.error}`, 'error');
            
            // Restaurar botón en caso de error
            if (button) {
                button.innerHTML = '<i class="fas fa-star"></i> Moto Ideal';
                button.disabled = false;
                button.style.opacity = '1';
            }
        }
    })
    .catch(error => {
        console.error('Error al marcar como ideal:', error);
        showNotification('Error al marcar la moto como ideal', 'error');
        
        // Restaurar botón en caso de error
        if (button) {
            button.innerHTML = '<i class="fas fa-star"></i> Moto Ideal';
            button.disabled = false;
            button.style.opacity = '1';
        }
    });
}

function verDetalles(motoId) {
    // Redirigir a página de detalles
    window.location.href = `/moto/${motoId}`;
}

// Función showNotification idéntica a populares.html
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Mostrar la notificación deslizándose desde la derecha
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Ocultar y eliminar la notificación después de 3 segundos
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}