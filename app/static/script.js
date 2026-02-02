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