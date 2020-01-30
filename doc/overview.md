# Übersicht Autojailhouse 

## Flow 

### autojail init

   Initialisiert ein autojailhouse Projekt.

   Eingaben: 
      - kernel build directory
      - jailhouse git url
      - cross compiler
      - base architure (ARM oder ARM64)
      - board identifier oder ssh login      

   Ausgaben: Projektkonfiguration  (autojailhouse.yml)

### autojail extract
   
   Eingaben: autojailhouse.yml
   Ausgaben: board.yml

   
### autojail configure

   Eingaben: board.yml und cells.yml
   Ausgaben: Konfiguriertes und Gebautes jailhouse Projekt