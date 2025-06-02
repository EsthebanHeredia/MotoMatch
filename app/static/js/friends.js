document.addEventListener("DOMContentLoaded", () => {
    const botones = document.querySelectorAll(".friend-name");
    const popup = document.getElementById("popup");
    const closeBtn = document.getElementById("popup-close");
    const popupUsername = document.getElementById("popup-username");
    const popupMotosList = document.getElementById("popup-motos-list");
    
    // Configurar botones para amigos actuales
    botones.forEach(btn => {
        btn.addEventListener("click", () => {
            const username = btn.dataset.username;
            showUserDetails(username);
        });
    });
    
    // Función para mostrar detalles del usuario en el popup
    function showUserDetails(username) {
        popupUsername.textContent = username;
        popupMotosList.innerHTML = "";
        
        const motoFavorita = window.motosLikes[username];
        
        if (!motoFavorita) {
            const emptyMessage = document.createElement("p");
            emptyMessage.textContent = "Este usuario aún no ha dado like a ninguna moto.";
            emptyMessage.style.textAlign = "center";
            emptyMessage.style.fontStyle = "italic";
            popupMotosList.appendChild(emptyMessage);
        } else {
            const li = document.createElement("li");
            const motoName = document.createElement("span");
            motoName.textContent = motoFavorita;
            
            const likeBtn = document.createElement("button");
            likeBtn.classList.add("like-moto-btn");
            likeBtn.innerHTML = '<i class="fas fa-heart"></i> Me gusta';
            likeBtn.onclick = function() {
                this.innerHTML = '<i class="fas fa-heart"></i> ¡Te gusta!';
                this.style.backgroundColor = "#f97316";
                this.style.color = "#fff";
                this.disabled = true;
                
                // Animación de corazón
                const heart = document.createElement("span");
                heart.innerHTML = "❤️";
                heart.className = "flying-heart";
                document.body.appendChild(heart);
                
                setTimeout(() => {
                    document.body.removeChild(heart);
                }, 1000);
                
                // Aquí se podría implementar una llamada AJAX para guardar el "like" en la BD
            };
            
            li.appendChild(motoName);
            li.appendChild(likeBtn);
            popupMotosList.appendChild(li);
        }
        
        popup.classList.remove("hidden");
    }
    
    // Mejorar efectos visuales de los botones de agregar/eliminar amigos
    const addButtons = document.querySelectorAll(".add-friend-btn");
    addButtons.forEach(btn => {
        btn.addEventListener("mouseenter", () => {
            btn.style.transform = "scale(1.05)";
        });
        btn.addEventListener("mouseleave", () => {
            btn.style.transform = "scale(1)";
        });
        btn.addEventListener("click", () => {
            // Efecto visual al hacer clic
            btn.innerHTML = '<i class="fas fa-check"></i> Agregando...';
        });
    });
    
    const removeButtons = document.querySelectorAll(".remove-friend-btn");
    removeButtons.forEach(btn => {
        btn.addEventListener("mouseenter", () => {
            btn.style.transform = "scale(1.05)";
        });
        btn.addEventListener("mouseleave", () => {
            btn.style.transform = "scale(1)";
        });
        btn.addEventListener("click", () => {
            // Efecto visual al hacer clic
            btn.innerHTML = '<i class="fas fa-times"></i> Eliminando...';
        });
    });
    
    // Cerrar el popup
    closeBtn.addEventListener("click", () => {
        popup.classList.add("hidden");
    });
    
    popup.addEventListener("click", (e) => {
        if (e.target === popup) {
            popup.classList.add("hidden");
        }
    });
});