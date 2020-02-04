# Übersicht Autojailhouse 

## Flow 

Workflow:
   
```
      +---------------+
      | autojail init |
      +---------------+
               |
               | autojail.yml
               v
  +-----------------------------+
  | autojail extract (optional) |
  +-----------------------------+
               | board.yml
               |            | cells.yml
               v            v
   +---------------------------+
   |     autojail config       |<-------------+
   +---------------------------+              |new cells.yml
               |                     +------------------------------+
               | board.cell          |  autojail explore (optional) |
               | board_guest1.cell   +------------------------------+
               | board_guest...               |
               |                              |
               v                              |
   +---------------------------+              |
   | autojail  test (optional) |--------------+
   +---------------------------+
```

### autojail init

Initialisiert ein autojailhouse Projekt.

Eingaben:

- Kernel build directory
- Jailhouse git url
- Cross compiler
- Base architure (ARM oder ARM64)
- Board identifier oder ssh login      

Ausgaben: Projektkonfiguration  (autojail.yml)

### autojail extract
   
Eingaben: autojail.yml

Ausgaben: board.yml

Datenquellen:

- Device trees
- /proc
    * /iomem
    * ..
- Linux tools
    * lscpu
    * lspci
    * lshw
    * ...
- Optional
    * Microbenchmarks
    * Datenblätter [Google Dialogflow](https://ieeexplore.ieee.org/document/8876925)

Datenmodelle:

- Rohdaten/Plattformparameter: board.yml
- Beschreibung der Zellen: cells.yml
    * Manuell erzeugt
    * Enhält sämtliche nicht herleitbaren Informationen
    * Benötigte CPUs, Memory regions, ...
   
### autojail configure

Eingaben: board.yml, cells.yml, autojail.yml

Ausgaben: Konfiguriertes und gebautes Jailhouse Projekt


   
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
