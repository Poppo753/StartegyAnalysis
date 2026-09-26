# Caso #4 — Sostituzione child_process con jszip (bulkDownloader.ts)

## 🔍 Analisi del Problema

### Codice originale (bulkDownloader.ts, linee 69-89)

```typescript
async function unzipFile(zipPath: string, targetDir: string): Promise<void> {
  const { exec } = await import('child_process');
  const { promisify } = await import('util');
  const execAsync = promisify(exec);

  const isWindows = process.platform === 'win32';

  if (isWindows) {
    await execAsync(
      `powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${targetDir}' -Force"`,
      { timeout: 60000 }
    );
  } else {
    await execAsync(`unzip -o "${zipPath}" -d "${targetDir}"`, { timeout: 60000 });
  }
}
```

### Bug/Problemi Identificati

#### Problema 1: Dipendenza da software esterno
- **Windows**: Richiede PowerShell con `Expand-Archive` (disponibile da PS 5.0+, ma non in Windows Server Core)
- **Linux**: Richiede il pacchetto `unzip` installato (non presente in container minimal Docker)
- **macOS**: Richiede `unzip` (generalmente presente ma non garantito)

#### Problema 2: Sicurezza — Command Injection
- Il percorso `zipPath` e `targetDir` sono interpolati direttamente nel comando shell
- Se un nome di file contiene caratteri speciali (`;`, `&&`, `|`, ecc.), può essere iniettato codice arbitrario
- **Esempio**: `zipPath = "foo; rm -rf /"` → comando pericoloso

#### Problema 3: Error handling fragile
- Se il comando fallisce, l'errore è un messaggio generico del processo figlio
- Non è facile catturare errori specifici (file non trovato, permessi, formato zip corrotto)

#### Problema 4: Prestazioni
- `exec` crea un nuovo processo, carica l'interprete shell, poi esegue il comando
- Per ogni giorno scaricato, viene creato un nuovo processo (potenzialmente decine)
- L'overhead di creazione processo è significativo rispetto alla decompressione

#### Problema 5: Cross-platform compatibility
- Non funziona su server Linux minimal (Docker senza `unzip`)
- Non funziona in ambienti sandboxed (AWS Lambda, Cloud Functions)
- Non funziona su Windows senza PowerShell

### Analisi Approfondita delle Alternative

#### Alternativa A — jszip (consigliata)
- Libreria TypeScript pura, nessuna dipendenza esterna
- Funziona ovunque ci sia Node.js
- **Pro**: Cross-platform, sicuro, nessun processo figlio, facile da usare
- **Contro**: Leggermente più lento per file molto grandi (>100MB)
- **Nota**: Le dimensioni dei file zip di aggTrades sono tipicamente 5-20MB — jszip è perfetto

#### Alternativa B — AdmZip
- Libreria zip nativa per Node.js
- **Pro**: Supporto vecchio, nessuna dipendenza esterna
- **Contro**: Non mantenuto attivamente, problemi di memoria con file grandi

#### Alternativa C — yauzl
- Libreria streaming zip per Node.js
- **Pro**: Molto efficiente in memoria, streaming nativo
- **Contro**: API più complessa, meno documentata

#### Alternativa D — node-stream-zip
- Streaming zip con supporto per crittografia
- **Pro**: Efficiente, streaming
- **Contro**: API più complessa, meno popolare

### Soluzione Scelta

**jszip** — La più popolare, ben mantenuta, facile da usare, con ottime performance per file di dimensioni moderate (5-20MB). Compatibilità cross-platform nativa.

### Impatto

- **Previene**: Crash su container Linux, command injection, dipendenza da software esterno
- **Rischio**: Basso — jszip è una libreria matura, ben testata
- **Test**: Verificare che i file zip vengano estratti correttamente
- **Dipendenza aggiuntiva**: `npm install jszip`
