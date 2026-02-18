function onFormSubmit(e) {
  Logger.log("🔔 trigger onFormSubmit ACTIVADO");
  
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Solicitud Certificados");
  
  // DETERMINAR LA FILA EXACTA
  // Usamos el objeto de evento 'e' para saber exactamente qué fila se acaba de llenar.
  // Si se corre manualmente (sin evento), usamos la última fila como fallback.
  var row = (e && e.range) ? e.range.getRow() : sheet.getLastRow();
  
  Logger.log("📝 Procesando fila: " + row);

  // Obtener valores de la fila específica
  var cedula = sheet.getRange(row, 3).getValue(); // Columna C
  var estado = sheet.getRange(row, 17).getValue(); // Columna Q
  
  Logger.log("🔍 Datos capturados:");
  Logger.log("   - Cédula: " + cedula);
  Logger.log("   - Estado actual: '" + estado + "'");

  // Solo procesar si el estado está vacío
  if (estado === "" || estado === null) {
    Logger.log("🚀 Estado vacío. Iniciando envío al servidor...");
    
    var url = "https://certificadoslaboraleschvs-main-production.up.railway.app/procesar-solicitud";

    var payload = {
      "cedula": String(cedula),
      "fila": row
    };

    var options = {
      "method": "post",
      "payload": payload,
      "muteHttpExceptions": true
    };

    try {
      Logger.log("📡 Enviando POST a: " + url);
      var response = UrlFetchApp.fetch(url, options);
      var responseCode = response.getResponseCode();
      var responseText = response.getContentText();
      
      Logger.log("📥 Respuesta del servidor recibida (Código: " + responseCode + ")");

      if (responseCode === 200) {
        Logger.log("✅ Solicitud procesada exitosamente por el servidor");
        
        try {
          var jsonResponse = JSON.parse(responseText);
          
          // 1. Marcar como procesada en la columna Q (17)
          sheet.getRange(row, 17).setValue("Procesada");
          Logger.log("✍️ Columna Q marcada como 'Procesada' en la fila " + row);
          
          // 2. Registrar en el Historial si existe
          var historialSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Historial_Procesamiento");
          if (historialSheet) {
            var fechaActual = Utilities.formatDate(new Date(), "GMT-5", "dd/MM/yyyy HH:mm:ss");
            historialSheet.appendRow([
              fechaActual,
              jsonResponse.cedula,
              jsonResponse.nombre,
              jsonResponse.folder_url,
              jsonResponse.certificados_generados
            ]);
            Logger.log("✅ Registro agregado exitosamente al historial");
          }
        } catch (parseError) {
          Logger.log("⚠️ Error al procesar respuesta JSON: " + parseError);
          sheet.getRange(row, 17).setValue("Procesada (Error Log)");
        }
        
      } else {
        Logger.log("⚠️ El servidor devolvió un error: " + responseCode);
        Logger.log("📄 Detalle del error: " + responseText);
        sheet.getRange(row, 17).setValue("Error HTTP " + responseCode);
      }
    } catch (error) {
      Logger.log("❌ ERROR FATAL al conectar con el servidor: " + error.toString());
      sheet.getRange(row, 17).setValue("Error: " + error.toString().substring(0, 50));
    }
  } else {
    Logger.log("⏩ La fila " + row + " ya tiene un estado ('" + estado + "'). Se omite el procesamiento.");
  }
  
  Logger.log("🏁 Fin del proceso onFormSubmit");
}

  function pruebaManualCedulaConLogs() {
    Logger.log("========================================");
    Logger.log("🚀 INICIANDO PRUEBA DE SOLICITUD");
    Logger.log("========================================");

    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Solicitud Certificados");

    // Agregar una fila de prueba
    var fechaActual = new Date();
    var filaTest = sheet.getLastRow() + 1;

    Logger.log("📝 Creando fila de prueba...");
    Logger.log("   - Número de fila: " + filaTest);

    // Escribir datos de prueba
    sheet.getRange(filaTest, 1).setValue(Utilities.formatDate(fechaActual, "GMT-5", "dd/MM/yyyy HH:mm:ss"));
    sheet.getRange(filaTest, 3).setValue("1114480905");
    sheet.getRange(filaTest, 17).setValue("");

    Logger.log("✅ Fila creada exitosamente");
    Logger.log("   - Columna A (Fecha): " + sheet.getRange(filaTest, 1).getValue());
    Logger.log("   - Columna C (Cédula): " + sheet.getRange(filaTest, 3).getValue());
    Logger.log("   - Columna Q (Estado): '" + sheet.getRange(filaTest, 17).getValue() + "'");

    Logger.log("");
    Logger.log("🔄 PREPARANDO PETICIÓN HTTP");
    Logger.log("========================================");

    var url = "https://certificadoslaboraleschvs-main-production.up.railway.app/procesar-solicitud";
    Logger.log("📍 URL: " + url);

    var payload = {
      "cedula": "1114480905",
      "fila": filaTest
    };

    Logger.log("📦 Payload enviado:");
    Logger.log(JSON.stringify(payload, null, 2));

    var options = {
      "method": "post",
      "payload": payload,
      "muteHttpExceptions": true
    };

    Logger.log("");
    Logger.log("📡 ENVIANDO PETICIÓN...");
    Logger.log("========================================");

    try {
      var startTime = new Date().getTime();
      var response = UrlFetchApp.fetch(url, options);
      var endTime = new Date().getTime();
      var duration = endTime - startTime;

      Logger.log("⏱️ Tiempo de respuesta: " + duration + "ms");
      Logger.log("");

      var responseCode = response.getResponseCode();
      var responseText = response.getContentText();
      var headers = response.getHeaders();

      Logger.log("📥 RESPUESTA RECIBIDA");
      Logger.log("========================================");
      Logger.log("🔢 Código HTTP: " + responseCode);
      Logger.log("");
      Logger.log("📋 Headers:");
      for (var key in headers) {
        Logger.log("   - " + key + ": " + headers[key]);
      }
      Logger.log("");
      Logger.log("📄 Body completo:");
      Logger.log(responseText);
      Logger.log("");

      // Intentar parsear como JSON
      try {
        var jsonResponse = JSON.parse(responseText);
        Logger.log("✅ Respuesta parseada como JSON:");
        Logger.log(JSON.stringify(jsonResponse, null, 2));
        Logger.log("");

        if (jsonResponse.status === "success") {
          Logger.log("🎉 ÉXITO - Certificados generados");
          Logger.log("   - Nombre: " + jsonResponse.nombre);
          Logger.log("   - Cédula: " + jsonResponse.cedula);
          Logger.log("   - Certificados: " + jsonResponse.certificados_generados);
          Logger.log("   - URL Carpeta: " + jsonResponse.folder_url);

          // Actualizar Sheet con los datos recibidos
          Logger.log("");
          Logger.log("📝 ACTUALIZANDO GOOGLE SHEET");
          Logger.log("========================================");

          // Actualizar estado en columna Q
          sheet.getRange(filaTest, 17).setValue("Procesada");
          Logger.log("✅ Columna Q actualizada a 'Procesada'");

          // Agregar a historial (si existe la hoja)
          try {
            var historialSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Historial_Procesamiento");
            if (historialSheet) {
              var fechaActual = Utilities.formatDate(new Date(), "GMT-5", "dd/MM/yyyy HH:mm:ss");
              historialSheet.appendRow([
                fechaActual,
                jsonResponse.cedula,
                jsonResponse.nombre,
                jsonResponse.folder_url,
                jsonResponse.certificados_generados
              ]);
              Logger.log("✅ Registro agregado al historial");
            } else {
              Logger.log("⚠️ La hoja 'Historial_Procesamiento' no existe");
            }
          } catch (histError) {
            Logger.log("⚠️ Error al escribir en historial: " + histError);
          }

        } else if (jsonResponse.status === "error") {
          Logger.log("❌ ERROR reportado por la app");
          Logger.log("   - Error: " + jsonResponse.error);
          sheet.getRange(filaTest, 17).setValue("Error: " + jsonResponse.error);
        }

      } catch (parseError) {
        Logger.log("⚠️ No se pudo parsear como JSON");
        Logger.log("   - Error: " + parseError);
      }

      Logger.log("");
      Logger.log("========================================");
      Logger.log("📊 VERIFICANDO ESTADO FINAL EN SHEET");
      Logger.log("========================================");

      SpreadsheetApp.flush();
      var estadoFinal = sheet.getRange(filaTest, 17).getValue();
      Logger.log("   - Estado en columna Q: '" + estadoFinal + "'");

      if (responseCode === 200) {
        Logger.log("");
        Logger.log("✅✅✅ PRUEBA COMPLETADA EXITOSAMENTE ✅✅✅");
      } else {
        Logger.log("");
        Logger.log("⚠️⚠️⚠️ PRUEBA COMPLETADA CON ERRORES ⚠️⚠️⚠️");
      }

    } catch (error) {
      Logger.log("");
      Logger.log("❌❌❌ ERROR FATAL ❌❌❌");
      Logger.log("========================================");
      Logger.log("Mensaje: " + error.message);
      Logger.log("Stack: " + error.stack);
      Logger.log("");

      // Marcar en Sheet
      try {
        sheet.getRange(filaTest, 17).setValue("Error: " + error.message);
      } catch (e) {
        Logger.log("No se pudo actualizar Sheet: " + e);
      }
    }

    Logger.log("");
    Logger.log("========================================");
    Logger.log("🏁 FIN DE LA PRUEBA");
    Logger.log("========================================");
  }