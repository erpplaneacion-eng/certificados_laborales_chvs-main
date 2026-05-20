// Variable global para el debounce
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    // Event listener para la búsqueda con debounce
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        // Limpiar timeout anterior
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        if (query.length < 2) {
            searchResults.classList.add('hidden');
            searchResults.innerHTML = '';
            return;
        }

        // Esperar 300ms antes de buscar
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    // Cerrar resultados si se hace click fuera
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add('hidden');
        }
    });
});

async function performSearch(query) {
    const searchResults = document.getElementById('searchResults');

    try {
        const response = await fetch(`/search?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
            console.error('Error en búsqueda, status:', response.status);
            return;
        }
        const results = await response.json();
        if (!Array.isArray(results)) {
            console.error('Respuesta inesperada del servidor:', results);
            return;
        }
        displayResults(results);
    } catch (error) {
        console.error('Error en búsqueda:', error);
    }
}

function displayResults(results) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = '';
    
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="no-results">No se encontraron resultados</div>';
    } else {
        results.forEach(person => {
            const div = document.createElement('div');
            div.className = 'result-item';
            div.innerHTML = `
                <span class="result-name">${person.nombre}</span>
                <span class="result-cedula">C.C. ${person.cedula}</span>
            `;
            div.onclick = () => selectPerson(person.cedula);
            searchResults.appendChild(div);
        });
    }
    
    searchResults.classList.remove('hidden');
}

function selectPerson(cedula) {
    const searchInput = document.getElementById('searchInput');
    const cedulaInput = document.getElementById('cedula');
    const searchResults = document.getElementById('searchResults');
    
    // Rellenar el campo de cédula
    cedulaInput.value = cedula;
    
    // Limpiar búsqueda
    searchInput.value = '';
    searchResults.classList.add('hidden');
    
    // Disparar la verificación
    verificarCedula();
}

async function verificarCedula() {
  const cedulaInput = document.getElementById('cedula');
  const infoCargo = document.getElementById('info-cargo');
  const cargoText = document.getElementById('cargo-text');
  const salarioGroup = document.getElementById('salario-manual-group');
  const submitBtn = document.getElementById('submitBtn');
  const cedula = cedulaInput.value.trim();
  
  // Limpiar estados anteriores
  infoCargo.classList.add('hidden');
  salarioGroup.classList.add('hidden');
  
  if (!cedula) {
    return;
  }

  try {
    // Deshabilitar botón mientras verifica
    submitBtn.disabled = true;
    submitBtn.textContent = 'Verificando...';
    
    const response = await fetch('/verificar-cedula', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'cedula=' + encodeURIComponent(cedula)
    });

    if (response.ok) {
      const data = await response.json();
      
      // Mostrar toda la sección de información
      infoCargo.classList.remove('hidden');
      cargoText.innerHTML = `<strong>Último cargo:</strong> ${data.ultimo_cargo}<br>
                            <strong>Contrato:</strong> ${data.contrato_activo ? 'Activo' : 'Finalizado'}`;
      
      const cargosConSalarioManual = ['MANIPULADORA ALIMENTOS', 'MANIPULADORA'];
      if (cargosConSalarioManual.includes(data.ultimo_cargo) && data.contrato_activo) {
        salarioGroup.classList.remove('hidden');
      }
      
      submitBtn.disabled = false;
      submitBtn.textContent = 'Generar Certificados';
    } else {
      const errorData = await response.json();
      alert('Error: ' + errorData.detail);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Generar Certificados';
    }
  } catch (error) {
    console.error('Error al verificar cédula:', error);
    alert('Error al verificar la cédula. Por favor, intente nuevamente.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Generar Certificados';
  }
}

// Función para cargar solicitudes recientes
async function cargarSolicitudesRecientes() {
  const container = document.getElementById('recentRequests');

  try {
    const response = await fetch('/solicitudes-recientes');
    const data = await response.json();

    if (data.solicitudes && data.solicitudes.length > 0) {
      container.innerHTML = '';

      data.solicitudes.forEach(solicitud => {
        const div = document.createElement('div');
        div.className = 'request-card';
        div.innerHTML = `
          <div class="request-info">
            <span class="folder-icon">📁</span>
            <div class="request-details">
              <strong>${solicitud['Nombre Completo']}_${solicitud['Cédula']}</strong>
              <span class="request-date">${solicitud['Fecha Procesamiento']}</span>
            </div>
          </div>
          <a href="${solicitud['URL Carpeta Drive']}" target="_blank" class="drive-link">🔗 Ver carpeta en Drive</a>
        `;
        container.appendChild(div);
      });
    } else {
      container.innerHTML = '<p class="no-requests">No hay solicitudes procesadas aún</p>';
    }
  } catch (error) {
    console.error('Error al cargar solicitudes recientes:', error);
    container.innerHTML = '<p class="error-requests">Error al cargar solicitudes</p>';
  }
}

// Cargar solicitudes al iniciar la página
document.addEventListener('DOMContentLoaded', () => {
  cargarSolicitudesRecientes();

  // Recargar cada 30 segundos
  setInterval(cargarSolicitudesRecientes, 30000);
});