/**
 * Script para manejar la página de motos populares (PageRank)
 * Versión corregida - compatible con el HTML de populares
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔥 Inicializando página de motos populares...');
    
    // Configurar botones de like
    setupLikeButtons();
    
    // Configurar botón de actualizar ranking
    setupUpdateRankingButton();
    
    // Configurar efectos visuales
    setupVisualEffects();
});

function setupLikeButtons() {
    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // CORREGIDO: Usar moto_id en lugar de modelo
            const motoId = this.getAttribute('data-moto-id');
            const modelo = this.getAttribute('data-modelo');
            
            // DEBUG: Ver todos los atributos del botón
            console.log('🔍 DEBUG BOTÓN:', {
                motoId: motoId,
                modelo: modelo,
                allAttributes: Array.from(this.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', ')
            });
            
            // CORREGIDO: Buscar el span fuera del botón (en like-section)
            const likeSection = this.parentElement;
            const likeCountSpan = likeSection.querySelector('.like-count');
            
            if (!motoId) {
                console.error('❌ No se encontró el ID de la moto');
                showNotification('Error: No se pudo identificar la moto', 'error');
                return;
            }
            
            console.log(`🔄 Procesando like para moto: ${motoId} (${modelo})`);
            
            // Deshabilitar botón temporalmente
            this.disabled = true;
            this.style.opacity = '0.6';
            
            // CORREGIDO: Usar el endpoint que funciona
            fetch('/dar_like_moto', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                // CORREGIDO: Enviar moto_id
                body: JSON.stringify({ moto_id: motoId })
            })
            .then(response => {
                console.log('📡 Respuesta HTTP:', response.status, response.statusText);
                // NUEVO: Ver el contenido exacto de la respuesta
                return response.text(); // Cambiar temporalmente de .json() a .text()
            })
            .then(rawData => {
                console.log('📄 Respuesta RAW del servidor:', rawData);
                // Intentar parsear como JSON
                try {
                    const data = JSON.parse(rawData);
                    console.log('✅ Respuesta JSON parseada:', data);
                    
                    // Tu código existente aquí...
                    if (data.success) {
                        // CORREGIDO: Actualizar estado del botón según la respuesta
                        if (data.action === 'liked') {
                            this.classList.add('liked');
                            this.innerHTML = '<i class="fas fa-heart"></i> Te gusta';
                        } else if (data.action === 'unliked') {
                            this.classList.remove('liked');
                            this.innerHTML = '<i class="far fa-heart"></i> Me gusta';
                        }
                        
                        // CORREGIDO: Actualizar contador si está disponible
                        if (data.likes !== undefined && likeCountSpan) {
                            likeCountSpan.textContent = data.likes;
                        }
                        
                        // Mostrar notificación
                        showNotification(data.action === 'liked' ? '¡Like registrado!' : 'Like removido', 'success');
                    } else {
                        console.error('❌ Error del servidor:', data.error);
                        showNotification('Error: ' + (data.error || 'No se pudo procesar el like'), 'error');
                    }
                } catch (e) {
                    console.error('❌ Error parseando JSON:', e);
                    console.error('❌ Respuesta no válida:', rawData);
                    showNotification('Error: Respuesta del servidor no válida', 'error');
                }
            })
            .catch(error => {
                console.error('❌ Error en la petición:', error);
                showNotification('Error de conexión: ' + error.message, 'error');
            })
            .finally(() => {
                // CORREGIDO: Rehabilitar botón
                this.disabled = false;
                this.style.opacity = '1';
            });
        });
    });
}

function setupUpdateRankingButton() {
    const reloadBtn = document.getElementById('reload-btn');
    if (reloadBtn) {
        reloadBtn.addEventListener('click', function() {
            this.classList.add('pulse');
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Actualizando ranking...';
            
            // Efecto visual en las tarjetas
            const cards = document.querySelectorAll('.moto-card');
            cards.forEach((card, index) => {
                setTimeout(() => {
                    card.style.opacity = "0";
                    card.style.transform = "translateY(-20px) scale(0.95)";
                }, index * 100);
            });
            
            // Recargar página
            setTimeout(() => {
                window.location.href = '/populares?update_ranking=true';
            }, 800);
        });
    }
}

function setupVisualEffects() {
    // Animación de entrada para las tarjetas
    const cards = document.querySelectorAll('.moto-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.6s ease-out';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 150);
    });
}

// CORREGIDO: Notificaciones igual a moto_ideal
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    // Estilos integrados con el CSS del HTML
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        border-left: 4px solid #f97316;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        z-index: 1000;
        min-width: 200px;
        max-width: 250px;
        width: auto;
        white-space: nowrap;
    `;
    
    // Colores según tipo
    if (type === 'success') {
        notification.style.borderLeftColor = '#10b981';
    } else if (type === 'error') {
        notification.style.borderLeftColor = '#dc3545';
    }
    
    document.body.appendChild(notification);
    
    // Mostrar la notificación
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // Ocultar y eliminar la notificación después de un tiempo
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}