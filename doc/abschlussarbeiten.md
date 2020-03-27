# Abschlussarbeiten Autojail

## Basiskonfigurator für Jailhouse

Bearbeiter: Dennis Volm

Anforderung: Automatisierte konfiguration eines Basis-Jailhouse Systems unter 
Zuhilfenahme von durch Linux (/proc, /sys) bereitgestellte Basiskonfigurationen

## Konfiguration von Inter-Cell Konfiguration

Bearbeiter: ???

Anforderung: Definition und Entwicklung einer Konfigurationsbeschreibung Shared Memory und Netzwerkkonfiguration zwischen Jailhouse-Zellen

## Use-Case CODESYS SPS

Bearbeiter: Artur Plischke

Anforderung: 
- Portierung einer CODESYS-SPS Anwendung auf Raspberry PI 4B und Jailhouse
- Bewerten des Echtzeitverhaltens von CODESYS-SPS
- Bewertung der Folgenden Szenarien.
  1. Reines Linux-System
  2. Partitioniertes System mit extra Jailhouse-Cell für SPS Runtime 
  3. Reines Linux-System mit Preempt-RT patch
  4. SPS-Runtime in extra Jailhouse-Cell mit partitioniertem Cell
  