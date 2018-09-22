
# blaulichtSMS Einsatzmonitor TV Controller

## Beschreibung
Das Projekt ist eine Python 3 Anwendung des [blaulichtSMS Einsatzmonitor](https://blaulichtsms.net/einsatz-monitor/). Folgende Features sind enthalten:

* Anzeigen des blaulichtSMS Einsatzmonitor Dashboards auf einem HDMI CEC fähigen Gerätes
* Einschalten des HDMI CEC Gerätes beim Eintreffen eines neuen Alarms und Ausschalten des Gerätes nach einer vorgegebenen Zeit
* Senden des Logs eines Tages per Mail (für das Versenden ist ein Gmail Account erforderlich)

Zur Kommunikation mit dem blaulichtSMS Einsatzmonitor wird die [Dashboard API](https://github.com/blaulichtSMS/docs/blob/master/dashboard_api_v1.md) verwendet.

Die Applikation ist entwickelt für Raspberry Pi in Kombination mit Raspbian Stretch. Für andere Systeme muss der Source Code angepasst werden.

## Abhängigkeiten
Folgende Bibliotheken werden benötigt:
* APT Packete:
	* cec-utils
	* libcec4-dev
* Pip Packete:
	* yaml
	* cec

Zum Installieren der Äbhängigkeiten folgenden Befehle ausführen:
```bash
sudo apt install cec-utils libcec4-dev
pip3 install yaml cec
```

Die Anzeige des blaulichtSMS Einstazmonitor Dashboards erfolgt im Chromium Browser, welcher standardmäßig auf Raspbian installiert ist. Das Einloggen in das Dashboard im Chromium Browser erfolgt nicht automatisch. Daher muss der Login einmal manuell in Chromium erfolgen. Bisher scheint es so, dass dieses manuelle Login nicht abläuft und somit nicht wiederholt werden muss.

## Installation
Zuerst muss via

```bash
python3 configure.py
```

die Anwendung konfiguriert werden. Bei der Konfiguration werden folgende Informationen abgefragt:

* blaulichtSMS Einsatzmonitor Login Daten
* Dauer nachdem das HDMI CEC Gerät nach einem Alarm wieder ausgeschaltet werden soll
* Der System Usernamen unter welchem die Applikation ausgeführt werden soll
* Ob das Versenden des Logs per Mail einmal am Tag erwünscht ist und falls ja
	* Die Gmail Login Daten
	* Die Empfänger des Logs

Nachdem die Konfiguration abgeschlossen ist können im File `config.ini` fortgeschrittenere Einstellungen vorgenommen werden. Das Versenden des Logs kann mit dem Attribut `send_log` im File `logging_config.yaml` eingestellt werden.

Anschließend erfolgt die Installation via

```bash
./INSTALL
```

Der Source Code im aktuellen Verzeichnis wird für die Ausführung verwendet. Es ist daher sinnvoll den Code in sein finales Verzeichnis zu verschieben bevor die Installation erfolgt.

## Deinstalltion
Die Deinstallation erfolgt mit
```bash
./UNINSTALL
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
```bash
sudo python3 test.py
```

führt einen Test mit folgenden Verhalten durch:

* Starten der Anzeige des blaulichtSMS Einsatzmonitor Dashboards
* Senden einer Abfrage an den blaulichtSMS Einsatzmonitor
* Einschalten des HDMI Gerätes
* Ausschalten des HDMI Gerätes nach 5 Minuten

Während das HDMI Gerät eingeschaltet ist sollte das blaulichtSMS Einsatzmonitor Dashboard darauf sichtbar sein. Das Laden des Dashboards dauert am Anfang etwas.

Am Ende wird eine Zusammenfassung des Tests angezeigt.

## Lizenz
Dieses Projekt ist unter der MIT License veröffentlicht. (siehe [LICENSE](LICENSE))

## Zusätzlich empfohlene Maßnahmen
Zusätzlich zur Anwendung selbst sind hier noch weitere sinnvolle Maßnahmen gelistet.

### Wartung im lokalen Netzwerk:
* ssh Zugang
* VNC Server

### Wartung über das Internet:
* ssh Zugang über [remot3.it](https://www.remot3.it/web/index.html)

### "Fehlerfreie" Anzeige:
* Installieren von *unclutter* zum Ausblenden des Mauszeigers:
  ```bash
  sudo apt install unclutter
  echo "@unclutter -d :0" >> ~/.config/lxsession/LXDE-pi/autostart
  ```

  Nach einem Neustart wird der Mauszeiger nach 5 Sekunden Inaktivität ausgeblendet.
* Installieren von *xscreensaver* zum Deaktivieren des Bildschirm schonens. Eine Beschreibung findet man auf [raspberrypi.org](https://www.raspberrypi.org/documentation/configuration/screensaver.md)
* Bei Problemen mit der Erkennung des HDMI Gerätes aktivieren von HDMI Hotplug wie [hier](https://github.com/Pulse-Eight/libcec#raspberry-pi) beschrieben.

### Sicherheit
* Installieren von *unattended-upgrades* via

  ```bash
  sudo apt install unattended-upgrades
  ```

  zum automatischen Installieren von Sicherheitsupdates.
* Ändern des Standard-Benutzers und Abfrage des Passwortes für die Verwendung von `sudo` wie [hier](https://www.raspberrypi.org/documentation/configuration/security.md) beschrieben.
* Da die Anwendung von Systemd als **root** User ausgeführt wird, sollte auch nur **root** schreibberechtigt sein. Sobald die Python Anwendung läuft lässt diese die root-Rechte fallen, da diese nicht erforderlich sind. Die Ausführung erfolgt stattdessen mit einem User, welcher bei der Konfiguration festgelegt wird. Dieser User sollte in einer Gruppe sein die lesesberechtigt ist.

  Folgendes Berechtigungsschema berücksichtigt diese Punkte:
  ```bash
  sudo chown -R root:<usergroup> .
  sudo find . -type f -exec chmod 640 {} \;
  sudo chmod 740 INSTALL UNINSTALL
  sudo chmod 644 LICENSE README.md
  ```

## Getestetes System
Die Funktionalität der Anwendung ist mit folgenden Komponenten getestet:
* Raspberry Pi Zero W
* Raspbian Stretch
* Samsung TV LE40B530P7W

## Fragen und Probleme
Für Fragen und Probleme (Bugs, Feature requests, ...) bitte ein [Issue erstellen](https://github.com/stg93/blaulichtsms_einsatzmonitor_tv_controller/issues/new).
