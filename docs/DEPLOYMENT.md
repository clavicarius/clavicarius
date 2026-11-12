# Profile Project Cards – Deployment Guide

Dieses Dokument beschreibt, wie der automatisierte Profile-README-Generator eingerichtet und deployed wird.

## Übersicht

Der Generator ruft Metadaten ausgewählter öffentlicher GitHub-Repositories über die GitHub GraphQL API ab und generiert automatisch eine **native Markdown-Tabelle** mit Projektinformationen in der `README.md` des Profil-Repositories.

Die Aktualisierung erfolgt vollautomatisch über GitHub Actions und wird durch Push-Events oder manuelle Auslösung getriggert.

**Format:** Einfache Markdown-Tabelle mit Shields.io-Badges für Programmiersprachen. 100% GitHub-kompatibel.

---

## Komponenten

### 1. Konfiguration (`.github/projects.yml`)

Die zentralen Projekteinstellungen befinden sich in [.github/projects.yml](../.github/projects.yml):

```yaml
owner: clavicarius

projects:
  - repo: repository-name-1
  - repo: repository-name-2
  # weitere Repositories...

settings:
  show_language: true
```

**Repositorys hinzufügen/entfernen:**
- Einen Eintrag unter `projects:` hinzufügen oder löschen
- Der Workflow wird beim nächsten Push automatisch ausgelöst

**Settings konfigurieren:**

| Setting | Typ | Standard | Beschreibung |
|---------|-----|----------|-------------|
| `show_language` | Boolean | true | Programmiersprache als Shields.io-Badge anzeigen |

Die Markdown-Tabelle zeigt:
- **Projekt**: Repository-Name (verlinkt zu GitHub)
- **Description**: Volle Beschreibung des Repositories
- **Language**: Programmiersprache als Shields.io-Badge

### 2. Generator-Skript (`scripts/generate_readme.py`)

Das Python-Skript:
- Lädt die Konfiguration aus `.github/projects.yml`
- Ruft Repository-Metadaten über GraphQL ab (Name, Description, URL, primaryLanguage)
- Validiert, dass alle Repositories öffentlich sind
- Generiert eine native **Markdown-Tabelle** mit 3 Spalten:
  - **Project**: Repository-Name (verlinkt)
  - **Description**: Volle, unabgekürzte Beschreibung
  - **Language**: Programmiersprache als Shields.io-Badge
- Aktualisiert ausschließlich den Bereich zwischen `<!-- PROJECTS:START -->` und `<!-- PROJECTS:END -->`
- Schreibt die `README.md` nur bei Änderungen

**Generiertes Format:**
```markdown
| Project | Description | Language |
|---------|-------------|----------|
| [project-name](https://...) | Full description text | ![Python](https://img.shields.io/badge/-Python-333?style=flat) |
```

**Lokale Ausführung:**
```bash
# Token setzen
set GITHUB_GRAPHQL_TOKEN=<dein-token>

# Generator ausführen
python scripts/generate_readme.py
```

### 3. GitHub Actions Workflow (`.github/workflows/update-profile.yml`)

Der Workflow:
- Checked das Repository
- Installiert Python und Abhängigkeiten
- Führt den Generator aus
- Committed Änderungen automatisch
- Pusht die aktualisierte README

---

## Setup und Authentifizierung

### Anforderung: Fine-grained Personal Access Token

Der Generator benötigt einen GitHub Token mit Lesezugriff auf Repository-Metadaten.

#### Token erstellen:

1. **GitHub Einstellungen öffnen:**
   - [github.com/settings/tokens](https://github.com/settings/tokens)

2. **Fine-grained Personal Access Token (Classic Token wird nicht empfohlen):**
   - `Settings > Developer settings > Personal access tokens > Tokens (classic)`
   - Klick: "Generate new token (classic)"

3. **Token-Berechtigungen:**
   - ✅ `repo` (Vollzugriff auf Repositories)
   - Oder minimal: `public_repo` (nur öffentliche Repositories)

4. **Token kopieren und speichern** (wird nicht erneut angezeigt)

#### Secret im Repository konfigurieren:

1. **Im Profil-Repository:**
   - `Settings > Secrets and variables > Actions`

2. **Neues Secret hinzufügen:**
   - Name: `PROJECTS_TOKEN`
   - Value: `<dein-token>`

3. **Speichern**

Der Workflow liest das Secret als `secrets.PROJECTS_TOKEN` und übergibt es an das Skript als `GITHUB_GRAPHQL_TOKEN`.

---

## Trigger und Auslösung

### Automatische Trigger:

1. **Push auf `main` Branch**
   ```yaml
   on:
     push:
       branches:
         - main
   ```
   Der Workflow wird automatisch ausgelöst, wenn neue Commits auf `main` gepusht werden.

2. **Manuelle Auslösung**
   ```yaml
   workflow_dispatch:
   ```
   Der Workflow kann manuell über die GitHub-UI ausgelöst werden:
   - Repository > Actions > "Update profile projects" > "Run workflow"

### Workflow-Verhalten:

- Der Workflow prüft, ob `README.md` geändert wurde
- Nur bei Änderungen wird ein Commit erstellt und gepusht
- Keine Endlosschleife: GitHub Actions unterbindet automatisch Loops bei Standard-Token-Commits

---

## Erste Schritte

### 1. Repository lokal klonen:
```bash
git clone https://github.com/clavicarius/clavicarius.git
cd clavicarius
```

### 2. Python-Umgebung einrichten:
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
```

### 3. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

### 4. Token setzen und Generator testen:
```bash
set GITHUB_GRAPHQL_TOKEN=<dein-token>
python scripts/generate_readme.py
```

### 5. Repository Secret `PROJECTS_TOKEN` hinzufügen (siehe oben)

### 6. Push auf `main` oder manuelle Auslösung
Der Workflow wird automatisch ausgelöst und die `README.md` aktualisiert.

---

## Sicherheit

⚠️ **Wichtig:**
- Private Repository-Metadaten dürfen **niemals** in die öffentliche `README.md` gelangen
- Der Generator validiert, dass **nur PUBLIC repositories** veröffentlicht werden
- Das Skript **bricht ab**, wenn ein Repository nicht öffentlich ist
- Token-Wert wird **niemals** geloggt oder in Artefakten gespeichert
- HTML-Escaping schützt gegen XSS-Injection in Description-Texten

**Markdown-Tabelle:** Native GitHub-Rendering ohne Custom HTML/CSS, daher maximal sicher.

---

## Fehlerbehandlung

### Häufige Fehler:

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| `GITHUB_GRAPHQL_TOKEN is required` | Token nicht gesetzt | Token in Umgebungsvariable setzen oder Secret konfigurieren |
| `Repository was not found or is inaccessible` | Token hat keine Berechtigung | Token mit `repo` oder `public_repo` Scope neu erstellen |
| `only PUBLIC repositories may be published` | Repository ist privat | Repository auf PUBLIC setzen oder aus `projects.yml` entfernen |
| `expected exactly one ... MARKER` | README-Marker beschädigt | Marker `<!-- PROJECTS:START -->` und `<!-- PROJECTS:END -->` prüfen |

### Logs anschauen:

1. GitHub Repository > **Actions**
2. Letzten Workflow-Run anklicken
3. Job "update-readme" aufklappen
4. Schritt "Generate project cards" prüfen

---

## Tests lokal ausführen

Unit-Tests für das Generator-Skript:

```bash
python -m unittest discover -s tests -v
```

Tests prüfen:
- HTML-Escaping gegen Injection
- Marker-Handling
- Spaltenlayout-Berechnung
- Nicht-öffentliche Repository-Validierung

---

## Wartung und Erweiterung

### Weitere Repositories hinzufügen:
- `.github/projects.yml` bearbeiten
- Eintrag hinzufügen
- Push auf `main`
- Workflow wird automatisch ausgelöst

---

## Kontakt & Support

Bei Fragen oder Problemen:
- Workflow-Logs in GitHub Actions prüfen
- Lokalen Generator-Run mit detaillierten Fehlern durchführen
- `--help` Flag für Kommandozeilen-Optionen nutzen:
  ```bash
  python scripts/generate_readme.py --help
  ```
