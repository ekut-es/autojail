# Übersicht Autojailhouse 

## Flow 

### autojail init

   Initialisiert ein autojailhouse Projekt.

   Eingaben: 
      - Kernel build directory
      - Jailhouse git url
      - Cross compiler
      - Base architure (ARM oder ARM64)
      - Board identifier oder ssh login      

   Ausgaben: Projektkonfiguration  (autojailhouse.yml)

### autojail extract
   
   Eingaben: autojailhouse.yml
   Ausgaben: board.yml
   
   Datenquellen:
      - Device trees
      - Linux tools
         * lscpu
         * lspci
         * lshw
         * ...
      - Optional
         * Microbenchmarks
         * [Google Dialogflow](https://ieeexplore.ieee.org/document/8876925)

   Datenmodelle:
      - Rohdaten/Plattformparameter: board.yml
      - Beschreibung der Zellen: cells.yml
         * Manuell erzeugt
         * Enhält sämtliche nicht herleitbaren Informationen
         * Benötigte CPUs, Memory regions, ...
   
### autojail configure

   Eingaben: board.yml und cells.yml
   Ausgaben: Konfiguriertes und gebautes Jailhouse Projekt
   
   Worflow:
   
```
       autojail extract 
               | board.yaml
               | cells.yml
               v
   +---------------------------+
   | Generierung Konfiguration |<--+
   +---------------------------+   |
               |                   |
               | config.c          | Feedback
               |                   |
               v                   |
   +-------------------------+     |
   | Valiedierung/Evaluation |-----+
   +-------------------------+
               |
               |
               v
  +--------------------------+
  | Optimierte Konfiguration |
  +--------------------------+
```
   
#### Ansätze

   Regelbasierter Ansatz:
      - Auf Basis bestehender Jailhouse Konfigurationen
      - Identifikation und Berücksichtigung von Metainformationen
      - Feedbackmechanismus
         * Zur Erzeugung optimierter Konfigurationen
         * Regelbasiert

   Maschinelles Lernen/Hybridverfahren:
      - Generierung von Konfigurationen mittels regelbasiertem Ansatz
      - Supervised learning mittels Feedbackmechanismus
