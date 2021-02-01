# blaulichtSMS Einsatzmonitor TV Controller

## Beschreibung

Das Projekt ist eine Python 3 Anwendung des [blaulichtSMS Einsatzmonitor](https://blaulichtsms.net/einsatz-monitor/). Folgende Features sind enthalten:

- Anzeigen des blaulichtSMS Einsatzmonitor Dashboards auf einem HDMI CEC fähigen Gerät
- Einschalten des HDMI CEC Gerätes beim Eintreffen eines neuen Alarms oder wahlweise auch bei neuen Informationen und Ausschalten des Gerätes nach einer vorgegebenen Zeit
- Senden des Logs eines Tages per Mail
- Senden einer Mail beim Auftreten eines Fehlers bzw. bei dessen Behebung

Für das Versenden von Mails ist ein Gmail Account erforderlich.

Zur Kommunikation mit dem blaulichtSMS Einsatzmonitor wird die [Dashboard API](https://github.com/blaulichtSMS/docs/blob/master/dashboard_api_v1.md) verwendet.

Die Applikation ist entwickelt für Raspberry Pi in Kombination mit [Raspbian Stretch Desktop](https://www.raspberrypi.org/downloads/raspbian/). Für andere Systeme muss der Source Code angepasst werden.

## Abhängigkeiten

Folgende Bibliotheken werden benötigt:

- APT Packete:
  - cec-utils
  - libcec4-dev
- Pip Packete:
  - pyyaml
  - cec

Zum Installieren der Äbhängigkeiten folgenden Befehle ausführen:

```bash
sudo apt install cec-utils libcec4-dev
pip3 install --system pyyaml cec
```

Um Python Packete systemweit mit `pip3 install --system` installieren zu können muss der User der die Installation ausführt in der Gruppe _staff_ sein. Ein User kann zu dieser Gruppe mit:

```bash
sudo adduser <username> staff
```

hinzugefügt werden.

## Installation

Zuerst muss via

```bash
python3 configure.py
```

die Anwendung konfiguriert werden. Bei der Konfiguration werden folgende Informationen abgefragt:

- blaulichtSMS Einsatzmonitor Login Daten
- Ob blaulichtSMS Informationen auch beachtet werden sollen
- Dauer nachdem das HDMI CEC Gerät nach einem Alarm wieder ausgeschaltet werden soll
- Der System Username unter welchem die Applikation ausgeführt werden soll
- Ob das Versenden von Mail Benachrichtigungen (Log des Tages um Mitternacht, Auftritt eines Fehlers und deren Behebung, Start der Applikation) erwünscht ist und falls ja
  - Die Gmail Login Daten
  - Die Empfänger des Logs

Nachdem die Konfiguration abgeschlossen ist können im File `config.ini` fortgeschrittenere Einstellungen vorgenommen werden. Das Versenden des Logs kann mit dem Attribut `send_log` im File `logging_config.yaml` eingestellt werden.

Anschließend erfolgt die Installation via

```bash
sudo ./INSTALL
```

Der Source Code im aktuellen Verzeichnis wird für die Ausführung verwendet. Es ist daher sinnvoll den Code in sein finales Verzeichnis zu verschieben bevor die Installation erfolgt.

## Deinstalltion

Die Deinstallation erfolgt mit

```bash
sudo ./UNINSTALL
```

Danach kann das Verzeichnis mit der Applikation gelöscht werden.

## Verwendung

Bei der Installation wird ein Systemd Service eingerichtet über welchen die Anwendung kontrolliert werden kann.

Der Service wird beim Systemstart standardmäßig mitgestartet. Um den Autostart einzustellen kann

```bash
sudo systemctl enable/disable alarmmonitor
```

verwendet werden.

Nach der Installation ist der Service gestartet.

```bash
sudo systemctl start/stop alarmmonitor
```

startet bzw. stoppt den Service. Mit

```bash
sudo systemctl status alarmmonitor
```

kann der Status des Services abgefragt werden.

Die Applikation kann auch unabhängig von Systemd verwendet werden. Zum eigenständigen Starten reicht

```bash
python3 main.py
```

## Log

Zusätzlich zum Versenden des Logs einmal pro Tag per Mail, findet man im Verzeichnis `./log`die Logfiles der letzten 7 Tage.

## Test

Das Packet `tests` enthält einen Systemtest.
Dieser Test simuliert mit Hilfe eines Mocks der blaulichtSMS Dashboard API eine Alarmierung.

Konkret sollte sich der Test folgendermaßen verhalten:

- Starten des _alarmmonitor_ Services. Während des Starts wird das HDMI Gerät ausgeschaltet.
- 6 Abfragen der Mock API alle 10 Sekunden, die in keinen aktiven Alarmen resultieren.
- Nach der 6. Abfrage liefert die Mock API einen aktiven Alarm.
  Das HDMI Gerät wird eingeschaltet und der Einsatzmonitor eingezeigt.
- Nach einer Minute sind keine Alarme aktiv und das HDMI Gerät wird ausgeschaltet.
- Weitere Abfragen die keine aktiven Alarme zurückgeben.
- Anzeigen einer Zusammenfassung des Tests mit der Anzahl der Fehler und Warnungen und dem Pfad des abgespeicherten Logs.

Zum Ausführen des Systemtests muss die Environment Variable **PYTHONPATH** das Root Verzeichnis der Applikation enthalten.
Diese kann mit `export PYTHONPATH=<absoluter_pfad_applikation_root>` gesetzt werden.

Danach kann mit

```bash
python3 tests/systemtest.py
```

der Systemtest gestartet werden. Die Ausführung des Tests kann nur vom Root Verzeichnis der Applikation gestartet werden.

## HDMI Geräte Steuerung

Die Steuerung eines HDMI Gerätes erfolgt mittels HDMI CEC. Für diese Steuerung sind zwei Modi implementiert.
Eine Implemetierung verwendet [Pulse-Eight libCEC](https://github.com/Pulse-Eight/libcec) direkt,
die andere verwendet die Python bindings der libCEC von [trainmain419](https://github.com/trainman419/python-cec).
Wird _python-cec_ via _pip_ installiert handelt es sich um Version 0.2.6.
Bei dieser Version schlägt manchmal die Initialisierung fehl.
Daher kann man auf die direkte Verwendung der _libCEC_ umstellen.

Welche Implementierung verwendet wird kann in der `config.ini` festgelegt werden:

```python
# libCEC
cec_mode = 1

# python-cec
cec_mode = 2
```

Installiert man _python-cec_ direkt vom source code, ist Version 0.2.7 aktuell.
Ob das Initalisierungproblem darin behoben ist wurde nicht getestet.

### libCEC Shell Befehle

Mit folgenden Befehlen kann ein HDMI CEC Gerät via libCEC direkt von einer Shell gesteuert werden:

```bash
# list known devices
cec-client -l

# scan for devices
echo "scan" | cec-client -s -d 1

# put device 0 to on
echo "on 0" | cec-client -s -d 1

# put device 0 to standby
echo "standby 0" | cec-client -s -d 1

# change source to current
echo "as" | cec-client -s -d 1
```

Einzelne Befehle via `cec-client` an den TV schicken hat sich in manchen Fällen als nicht verlässlich heraus gestellt.
Für mehrere Commands einfach den `cec-client` wie folgt starten:

```bash
# -d defines the debug level, see hdmiceccontroller.py
cec-client -d 4
# show available commands
help
```

Folgende Kommandos sind in unseren Tests verfügbar:

```txt
================================================================================
Available commands:

[tx] {bytes}              transfer bytes over the CEC line.
[txn] {bytes}             transfer bytes but don't wait for transmission ACK.
[on] {address}            power on the device with the given logical address.
[standby] {address}       put the device with the given address in standby mode.
[la] {logical address}    change the logical address of the CEC adapter.
[p] {device} {port}       change the HDMI port number of the CEC adapter.
[pa] {physical address}   change the physical address of the CEC adapter.
[as]                      make the CEC adapter the active source.
[is]                      mark the CEC adapter as inactive source.
[osd] {addr} {string}     set OSD message on the specified device.
[ver] {addr}              get the CEC version of the specified device.
[ven] {addr}              get the vendor ID of the specified device.
[lang] {addr}             get the menu language of the specified device.
[pow] {addr}              get the power status of the specified device.
[name] {addr}             get the OSD name of the specified device.
[poll] {addr}             poll the specified device.
[lad]                     lists active devices on the bus
[ad] {addr}               checks whether the specified device is active.
[at] {type}               checks whether the specified device type is active.
[sp] {addr}               makes the specified physical address active.
[spl] {addr}              makes the specified logical address active.
[volup]                   send a volume up command to the amp if present
[voldown]                 send a volume down command to the amp if present
[mute]                    send a mute/unmute command to the amp if present
[self]                    show the list of addresses controlled by libCEC
[scan]                    scan the CEC bus and display device info
[mon] {1|0}               enable or disable CEC bus monitoring.
[log] {1 - 31}            change the log level. see cectypes.h for values.
[ping]                    send a ping command to the CEC adapter.
[bl]                      to let the adapter enter the bootloader, to upgrade
                          the flash rom.
[r]                       reconnect to the CEC adapter.
[h] or [help]             show this help.
[q] or [quit]             to quit the CEC test client and switch off all
                          connected CEC devices.
================================================================================
```

## Danksagungen

[r00tat](https://github.com/r00tat) danke für die libCEC Implementierung, die Alarmüberprüfung
bei mehreren Alarmen und die Inkludierung der blaulichtSMS Infos.

## Lizenz

Dieses Projekt ist unter der MIT License veröffentlicht. (siehe [LICENSE](LICENSE))

## Zusätzlich empfohlene Maßnahmen

Zusätzlich zur Anwendung selbst sind hier noch weitere sinnvolle Maßnahmen gelistet.

### Wartung im lokalen Netzwerk:

- ssh Zugang
- VNC Server

### Wartung über das Internet:

- ssh Zugang über [remot3.it](https://www.remot3.it/web/index.html) oder mittels Port Forwarding

### "Fehlerfreie" Anzeige:

- Installieren von _unclutter_ zum Ausblenden des Mauszeigers:

  ```bash
  sudo apt install unclutter
  echo "@unclutter -d :0" >> ~/.config/lxsession/LXDE-pi/autostart
  ```

  Nach einem Neustart wird der Mauszeiger nach 5 Sekunden Inaktivität ausgeblendet.

- Installieren von _xscreensaver_ zum Deaktivieren des Bildschirm schonens. Eine Beschreibung findet man auf [raspberrypi.org](https://www.raspberrypi.org/documentation/configuration/screensaver.md)
- Bei Problemen mit der Erkennung des HDMI Gerätes aktivieren von HDMI Hotplug wie [hier](https://github.com/Pulse-Eight/libcec#raspberry-pi) beschrieben.

### Sicherheit

- Installieren von _unattended-upgrades_ via

  ```bash
  sudo apt install unattended-upgrades
  ```

  zum automatischen Installieren von Sicherheitsupdates.

- Ändern des Standard-Benutzers, erlauben von SSH nur mit Schlüsseln, installieren einer Firewall und von fail2ban wie [hier](https://www.raspberrypi.org/documentation/configuration/security.md) beschrieben.

  **Achtung:** Um auf Netzwerkgeräte zugreifen zu können muss ein User in der _netdev_ Gruppe sein. Um auf den HDMI Controller zugreifen zu können muss ein User in der Gruppe _video_ sein.

- Die Konfigurationsdateien und die Logdateien enthalten sensible Daten und sollten nur berechtigte User lesbar sein.

  Folgendes Berechtigungsschema ist für den User, welcher bei der Konfiguration festgelegt wird, sinnvoll:

  ```bash
  sudo chown -R <username>:<usergroup> .
  sudo find . -type f -exec chmod 640 {} \;
  sudo chmod 740 INSTALL UNINSTALL
  sudo chmod 644 LICENSE README.md
  ```

## Getestetes System

Die Funktionalität der Anwendung ist mit folgenden Komponenten getestet:

- Raspberry Pi 3b
- Raspberry Pi Zero W
- Raspbian Raspbian Desktop [Download](https://downloads.raspberrypi.org/raspbian_latest)
- Samsung TV LE40B530P7W

## Fragen und Probleme

Für Fragen und Probleme (Bugs, Feature requests, ...) bitte ein [Issue erstellen](https://github.com/stg93/blaulichtsms_einsatzmonitor_tv_controller/issues/new).
