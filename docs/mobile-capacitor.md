# GridCheck Mobile Shell (Capacitor)

## Zielbild

GridCheck bleibt primaer eine Next.js-/PWA-Anwendung. Der native Anteil ist bewusst ein duennes Capacitor-Shell, das
die bestehende Web-App auf Android und iOS laedt, ohne Routing, API-Proxy oder PWA-Verhalten umzubauen.

Diese Richtung passt zum aktuellen Stand:

- Next.js App Router bleibt die einzige Frontend-Laufbahn.
- Manifest, Service Worker und Offline-Seite bleiben aktiv fuer Web/PWA.
- Der Site-Marker-Flow kann im nativen Shell GPS und Kamera bevorzugt ueber Capacitor ansprechen.
- Fachlogik bleibt unveraendert im Backend/Web-Frontend.

## Enthaltene Vorbereitung

- `frontend/capacitor.config.ts`
  - `appId`: `de.gridcheck.mobile`
  - `webDir`: `frontend/native-shell`
  - optionaler Remote-Load ueber `CAPACITOR_SERVER_URL`
  - StatusBar-/Keyboard-Basiskonfiguration
- `frontend/native-shell/index.html`
  - bewusste Fallback-Seite, falls noch keine echte PWA-URL gesetzt ist
- `frontend/.env.capacitor.example`
  - Beispiel fuer die native Shell-Konfiguration
- `frontend/package.json`
  - Capacitor-Abhaengigkeiten plus `native:*`-Skripte
- `frontend/lib/mobile/capacitor.ts`
  - kleine Laufzeithilfe fuer Native-Erkennung, GPS, Kamera, Status Bar und Keyboard

## Native Build-Basis erzeugen

### 1. Frontend-Abhaengigkeiten installieren

Fuer die hier vorbereitete Capacitor-8-Toolchain wird Node.js 22+ fuer die nativen `cap`-Kommandos benoetigt.

```powershell
cd .\frontend
npm install
```

### 2. Native Shell-ENV setzen

Empfohlen ist eine erreichbare HTTPS-URL der bestehenden GridCheck-PWA, z. B. Staging:

```powershell
Copy-Item .\.env.capacitor.example .\.env.capacitor.local
$env:CAPACITOR_SERVER_URL="https://staging.example.gridcheck.de"
$env:CAPACITOR_ALLOW_INSECURE_HTTP="0"
```

Hinweise:

- Fuer reale Geraete sollte `CAPACITOR_SERVER_URL` auf eine von Android/iOS erreichbare URL zeigen.
- `localhost` funktioniert auf physischen Geraeten nicht.
- Unsichere HTTP-URLs nur fuer rein lokale Emulator-/LAN-Tests und nur bewusst ueber `CAPACITOR_ALLOW_INSECURE_HTTP=1`.

### 3. Plattformprojekte anlegen

```powershell
npm run native:add:android
npm run native:add:ios
```

### 4. Konfiguration und Plugins in die Plattformen syncen

```powershell
npm run native:sync
```

### 5. Native IDEs oeffnen

```powershell
npm run native:open:android
npm run native:open:ios
```

## Site-Marker-Flow im nativen Shell

Die bestehende mobile Feldaufnahme bleibt dieselbe Seite `/site-markers`.

Zusatz im nativen Laufzeitmodus:

- GPS-Button nutzt bevorzugt den Capacitor-Geolocation-Pfad
- Fotoaufnahme kann Kamera/Galerie ueber Capacitor oeffnen
- klassischer Browser-/PWA-Pfad ueber `navigator.geolocation` und Datei-Input bleibt erhalten
- PWA-Install-Prompts werden im nativen Shell bewusst unterdrueckt

Damit bleibt ein einziger Flow fuer Web, PWA und spaetere Store-Apps erhalten.

## Verifikation

Nach `npm install` sollten mindestens diese Checks laufen:

```powershell
cd .\frontend
npm run lint
npm run build
npm run native:doctor
npm run native:sync
```

Wenn Android/iOS bereits angelegt sind, danach zusaetzlich in Android Studio bzw. Xcode einmal lokal bauen.

## Was noch extern fehlt

Diese Punkte sind bewusst nicht im Repo loesbar und bleiben nachgelagert:

- Apple Developer Team / Bundle Signing / Provisioning Profiles
- Android Keystore / Signaturen / Play App Signing
- finale Staging-/Produktiv-Domain fuer `CAPACITOR_SERVER_URL`
- Store-Metadaten, Datenschutztexte, Screenshots, Age Rating
- ggf. MDM-/Enterprise-Verteilung, falls nicht ueber Stores ausgerollt wird

## Was absichtlich nicht gemacht wurde

- kein Umbau auf Static Export
- kein nativer Vollausbau mit eigenem Navigations- oder State-Layer
- keine Duplizierung von Backend-, Billing- oder Monetarisierungslogik
- keine Behauptung lokaler Offline-Synchronisation fuer Uploads ohne Verbindung
