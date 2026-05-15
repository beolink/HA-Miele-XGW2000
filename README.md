# Miele XGW 2000 — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/Home%20Assistant-2023.4%2B-blue.svg)](https://www.home-assistant.io)

Local integration for Miele@home appliances connected via the **XGW 2000** gateway. No cloud, no Miele account required — communicates directly with the gateway on your LAN.

---

## Vad är Miele@home?

Miele@home är Mieles system för att ansluta hushållsmaskiner till ett lokalt nätverk. Maskinerna kommunicerar via **Powerline** (HomePlug) — det vill säga via det vanliga elnätet — och behöver inget separat trådlöst nätverk. Systemet gör det möjligt att:

- Övervaka maskiners status (program, fas, återstående tid)
- Ta emot felmeddelanden och driftinformation
- Styra maskiner (start, stopp, paus) beroende på maskintyp och läge
- Integrera maskiner i smarta hem-system via ett öppet XML-API

Miele@home stöds av en rad produkter: tvättmaskiner, torktumlare, diskmaskiner, ugnar, kylskåp och frysar.

---

## Vad är XGW 2000?

**XGW 2000** (eXternal GateWay 2000) är Mieles nätverksgateway som fungerar som brygga mellan Miele@home-maskinerna och ett vanligt Ethernet-/IP-nätverk.

```
[Miele-maskiner] ──Powerline──► [XGW 2000] ──Ethernet──► [Hemmanätverk / Home Assistant]
```

Gatewayen:
- Ansluts till elnätet (Powerline) och Ethernet samtidigt
- Har ett inbyggt webbgränssnitt för konfiguration (`http://<ip>/`)
- Exponerar ett **lokalt HTTP/XML-API** kallat *Hausbus-Schnittstelle* på `http://<ip>/homebus`
- Skickar **UDP multicast-notiser** (239.255.68.139) när en maskins status ändras

### Standardinställningar

| Parameter | Standardvärde |
|-----------|--------------|
| IP-adress | `192.168.1.237` |
| Användarnamn | `xgw2000` |
| Lösenord | `xgw2000` |
| Homebus-URL | `http://<ip>/homebus` |

> Lösenordet kan ändras i gatewayens webbgränssnitt under **Status**.

---

## Hur API:et fungerar

### Hausbus-Schnittstelle (XML API)

Gatewayen erbjuder ett tre-stegs XML-API:

#### Steg 1 — Hämta alla maskiner

```
GET http://<gateway-ip>/homebus
```

Returnerar en lista med alla anslutna maskiner och deras grundstatus. Varje maskin innehåller också en URL till mer detaljerad information.

**Exempel på svar:**
```xml
<DEVICES>
  <device>
    <class>com.miele.xgw3000.gateway.api.appliance.MieleApplianceWM</class>
    <UID>000123456789</UID>
    <type>WM_W1234</type>
    <name>Waschautomat</name>
    <state>In Betrieb</state>
    <additionalName/>
    <room id="1" level="0">Keller</room>
    <information>
      <key name="phase" value="Waschen"/>
      <key name="remainingTime" value="1:23"/>
    </information>
    <actions>
      <action name="details" URL="/homebus/appliance?uid=000123456789"/>
    </actions>
  </device>
</DEVICES>
```

#### Steg 2 — Hämta detaljstatus för en maskin

```
GET http://<gateway-ip>/homebus/appliance?uid=<UID>
```

Returnerar utökad information och de åtgärder som är tillgängliga i maskinens nuvarande läge (t.ex. start/stopp är bara tillgängliga i rätt läge).

```xml
<device>
  <information>
    <key name="program" value="Baumwolle"/>
    <key name="phase" value="Waschen"/>
    <key name="remainingTime" value="1:23"/>
    <key name="startTime" value="14:41"/>
    <key name="endTime" value="16:30"/>
  </information>
  <actions>
    <action name="stop" URL="/homebus/appliance?uid=000123456789&amp;action=stop"/>
  </actions>
</device>
```

#### Steg 3 — Utlös en åtgärd

```
GET http://<gateway-ip>/homebus/appliance?uid=<UID>&action=start
```

**Vid lyckad åtgärd:**
```xml
<ok>
  <action>start</action>
  <cu-type>WM_W1234</cu-type>
  <cu-id>000123456789</cu-id>
</ok>
```

**Vid fel:**
```xml
<error>
  <error-type>ACTION_EXEC_ERROR</error-type>
  <cu-type>WM_W1234</cu-type>
  <cu-id>000123456789</cu-id>
  <action-id>start</action-id>
  <message>Maskin ej redo</message>
</error>
```

### XML-scheman (DTD)

Gatewayen definierar XML-strukturen via fyra DTD-filer:

| DTD-fil | Beskrivning |
|---------|-------------|
| `appliance_list.dtd` | Struktur för bas-listan med alla maskiner |
| `appliance_info.dtd` | Struktur för detaljsvar per maskin |
| `action_ok_response.dtd` | Svar vid lyckad åtgärd |
| `error.dtd` | Felsvar med felkod och meddelande |

### Push-notiser via UDP multicast

Förutom polling skickar gatewayen automatiskt en UDP-notis till multicast-adressen **239.255.68.139** när en maskins status ändras. Den här integrationen lyssnar på dessa notiser och triggar en omedelbar uppdatering, vilket ger snabbare respons än enbart polling.

---

## Funktioner i integrationen

### Sensorer (per maskin)

| Sensor | Beskrivning |
|--------|-------------|
| **Status** | Maskinens övergripande tillstånd (Bereit, In Betrieb, etc.) |
| **Program** | Valt program (t.ex. Baumwolle, Pflegeleicht) |
| **Fas** | Aktuell fas (Waschen, Spülen, Schleudern, etc.) |
| **Återstående tid** | Tid kvar i minuter |
| **Starttid** | Planerad starttid |
| **Sluttid** | Beräknad sluttid |

### Knappar (per maskin, beroende på läge)

| Knapp | Beskrivning |
|-------|-------------|
| **Start** | Startar maskinen |
| **Stop** | Stoppar pågående program |
| **Pause** | Pausar maskinen |
| **SuperCooling on/off** | Aktiverar/avaktiverar SuperCooling (kylskåp) |
| **SuperFreezing on/off** | Aktiverar/avaktiverar SuperFreezing (frys) |

> Tillgängliga knappar beror på maskintyp och aktuellt läge — gatewayen exponerar bara de åtgärder som är möjliga just nu.

---

## Installation

### Via HACS (rekommenderat)

1. Öppna HACS i Home Assistant
2. Gå till **Integrations** → klicka på tre-punktsmenyn → **Custom repositories**
3. Lägg till: `https://github.com/beolink/HA-Miele-XGW2000`
4. Välj kategori: **Integration**
5. Klicka **Add** → sök efter "Miele" → **Download**
6. Starta om Home Assistant

### Manuell installation

1. Kopiera mappen `custom_components/miele_xgw2000/` till din HA:s `config/custom_components/`
2. Starta om Home Assistant

---

## Konfiguration

1. Gå till **Inställningar → Enheter & Tjänster → Lägg till integration**
2. Sök efter **Miele XGW 2000**
3. Fyll i formuläret:

| Fält | Beskrivning | Standard |
|------|-------------|---------|
| **IP-adress** | Gatewayens IP-adress | `10.0.40.20` |
| **Användarnamn** | Inloggning för Homebus (om aktiverat) | `xgw2000` |
| **Lösenord** | Lösenord för Homebus (om aktiverat) | `xgw2000` |
| **Poll-intervall** | Sekunder mellan uppdateringar | `30` |

> **Obs:** Homebus-inloggning är avaktiverat som standard i gatewayen. Det aktiveras under **Konfigurationseinstellungen → Homebus Login aktiv** i gatewayens webbgränssnitt.

---

## Gateway-konfiguration (rekommenderade inställningar)

I gatewayens webbgränssnitt (`http://<ip>/`) rekommenderas följande inställningar för bästa integration:

- **Homebus Event Notification** → `på` (standard) — skickar push-notiser vid statusändring
- **Homebus alle Informationen senden** → `på` — skickar all statusinformation, inte bara det viktigaste
- **Gateway periodisch neu starten** → valfritt (gatewayen startas om var 24:e timme som standard)

---

## Felsökning

**Integrationen hittar inga maskiner**
- Kontrollera att gatewayen är nåbar: `http://<ip>/homebus` ska returnera XML
- Kontrollera att maskinerna är anslutna via Powerline (PL-LEDen på gatewayen ska lysa konstant)

**Sensorer visar okänd/tom data**
- Aktivera debug-loggning i HA för att se vilka `key`-namn gatewayen skickar:
```yaml
logger:
  default: warning
  logs:
    custom_components.miele_xgw2000: debug
```

**Knappar är gråa/otillgängliga**
- Normalt beteende — gatewayen exponerar bara åtgärder som är möjliga i maskinens nuvarande läge. Start visas t.ex. bara när maskinen är redo och stopp bara när den är igång.

---

## Tekniska detaljer

- **Kommunikation:** Lokal HTTP, ingen molnåtkomst
- **Protokoll:** XML över HTTP (Hausbus-Schnittstelle, firmware ≥ 3.0.0)
- **Push-notiser:** UDP multicast 239.255.68.139
- **Polling:** Konfigurerbart, standard 30 sekunder
- **HA-plattformar:** `sensor`, `button`
- **Config entries:** Konfigureras via UI, sparas i HA:s interna lagring

---

## Licens

MIT
