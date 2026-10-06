# Miele XGW 2000 — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/Home%20Assistant-2023.4%2B-blue.svg)](https://www.home-assistant.io)

Local integration for Miele@home appliances connected via the **XGW 2000** gateway. No cloud, no Miele account required — communicates directly with the gateway on your LAN.

---

## What is Miele@home?

Miele@home is Miele's system for connecting household appliances to a local network. Appliances communicate via **Powerline** (HomePlug) — through the existing electrical wiring — and require no separate wireless network. The system enables you to:

- Monitor appliance status (program, phase, remaining time)
- Receive error messages and operational information
- Control appliances (start, stop, pause) depending on appliance type and state
- Integrate appliances into smart home systems via an open XML API

Miele@home is supported by a wide range of products: washing machines, tumble dryers, dishwashers, ovens, refrigerators and freezers.

---

## What is the XGW 2000?

The **XGW 2000** (eXternal GateWay 2000) is Miele's network gateway that bridges Miele@home appliances to a standard Ethernet/IP network.

```
[Miele appliances] ──Powerline──► [XGW 2000] ──Ethernet──► [Home network / Home Assistant]
```

The gateway:
- Connects to both the power line (Powerline) and Ethernet simultaneously
- Has a built-in web interface for configuration (`http://<ip>/`)
- Exposes a **local HTTP/XML API** called the *Hausbus interface* at `http://<ip>/homebus`
- Sends **UDP multicast notifications** (239.255.68.139) whenever an appliance changes state

### Default settings

| Parameter | Default value |
|-----------|--------------|
| IP address | `192.168.1.237` |
| Username | `xgw2000` |
| Password | `xgw2000` |
| Homebus URL | `http://<ip>/homebus` |

> The password can be changed in the gateway's web interface under **Status**.

---

## How the API works

### Hausbus interface (XML API)

The gateway provides a three-step XML API:

#### Step 1 — Fetch all appliances

```
GET http://<gateway-ip>/homebus
```

Returns a list of all connected appliances and their basic status. Each appliance also contains a URL pointing to more detailed information.

**Example response:**
```xml
<DEVICES>
  <device>
    <class>com.miele.xgw3000.gateway.api.appliance.MieleApplianceWM</class>
    <UID>000123456789</UID>
    <type>WM_W1234</type>
    <name>Washing machine</name>
    <state>Running</state>
    <additionalName/>
    <room id="1" level="0">Basement</room>
    <information>
      <key name="phase" value="Washing"/>
      <key name="remainingTime" value="1:23"/>
    </information>
    <actions>
      <action name="details" URL="/homebus/appliance?uid=000123456789"/>
    </actions>
  </device>
</DEVICES>
```

#### Step 2 — Fetch detailed status for an appliance

```
GET http://<gateway-ip>/homebus/appliance?uid=<UID>
```

Returns extended information and the actions available in the appliance's current state (e.g. start/stop are only available at the right moment).

```xml
<device>
  <information>
    <key name="program" value="Cotton"/>
    <key name="phase" value="Washing"/>
    <key name="remainingTime" value="1:23"/>
    <key name="startTime" value="14:41"/>
    <key name="endTime" value="16:30"/>
  </information>
  <actions>
    <action name="stop" URL="/homebus/appliance?uid=000123456789&amp;action=stop"/>
  </actions>
</device>
```

#### Step 3 — Trigger an action

```
GET http://<gateway-ip>/homebus/appliance?uid=<UID>&action=start
```

**On success:**
```xml
<ok>
  <action>start</action>
  <cu-type>WM_W1234</cu-type>
  <cu-id>000123456789</cu-id>
</ok>
```

**On error:**
```xml
<error>
  <error-type>ACTION_EXEC_ERROR</error-type>
  <cu-type>WM_W1234</cu-type>
  <cu-id>000123456789</cu-id>
  <action-id>start</action-id>
  <message>Appliance not ready</message>
</error>
```

### XML schemas (DTD)

The gateway defines the XML structure via four DTD files:

| DTD file | Description |
|----------|-------------|
| `appliance_list.dtd` | Structure for the base list of all appliances |
| `appliance_info.dtd` | Structure for the detail response per appliance |
| `action_ok_response.dtd` | Response on successful action |
| `error.dtd` | Error response with error code and message |

### Push notifications via UDP multicast

In addition to polling, the gateway automatically sends a UDP notification to multicast address **239.255.68.139** whenever an appliance changes state. This integration listens for these notifications and triggers an immediate refresh, giving faster response than polling alone.

---

## Integration features

### Sensors (per appliance)

| Sensor | Description |
|--------|-------------|
| **Status** | Overall appliance state (Ready, Running, etc.) |
| **Program** | Selected program (e.g. Cotton, Easy-Care) |
| **Phase** | Current phase (Washing, Rinsing, Spinning, etc.) |
| **Remaining time** | Time remaining in minutes |
| **Duration** | Program duration in minutes |
| **Start time** | Scheduled start time |
| **End time** | Estimated end time |
| **Cooking function** | Ovens: selected cooking function |
| **Temperature** / **Core temperature** | Ovens: cavity and probe temperature (°C) |

Apart from Status, a sensor is only created when the appliance reports the matching value. The gateway names values in plain language in the detail XML (`State`, `Phase`, `Remaining Time`, …); the older camelCase names (`remainingTime`, …) are accepted too.

### Buttons (per appliance, depending on state)

| Button | Description |
|--------|-------------|
| **Start** | Start the appliance |
| **Stop** | Stop the current program |
| **Pause** | Pause the appliance |
| **SuperCooling on/off** | Activate/deactivate SuperCooling (refrigerator) |
| **SuperFreezing on/off** | Activate/deactivate SuperFreezing (freezer) |

> Available buttons depend on appliance type and current state — the gateway only exposes actions that are possible at any given moment.

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add: `https://github.com/beolink/HA-Miele-XGW2000`
4. Select category: **Integration**
5. Click **Add** → search for "Miele" → **Download**
6. Restart Home Assistant

### Manual installation

1. Copy the `custom_components/miele_xgw2000/` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Miele XGW 2000**
3. Fill in the form:

| Field | Description | Default |
|-------|-------------|---------|
| **IP Address** | IP address of the gateway (factory default `192.168.1.237`) | — |
| **Username** | Login for Homebus (if enabled) | `xgw2000` |
| **Password** | Password for Homebus (if enabled) | `xgw2000` |
| **Poll interval** | Seconds between updates | `30` |

> **Note:** Homebus login is disabled by default in the gateway. It can be enabled under **Configuration settings → Homebus Login active** in the gateway's web interface.

---

## Recommended gateway settings

In the gateway's web interface (`http://<ip>/`) the following settings are recommended for the best integration experience:

- **Homebus Event Notification** → `on` (default) — sends push notifications on state change
- **Homebus send all information** → `on` — sends all status information, not just the essentials
- **Gateway periodic restart** → optional (the gateway restarts every 24 hours by default)

---

## Troubleshooting

**Integration finds no appliances**
- Verify the gateway is reachable: `http://<ip>/homebus` should return XML
- Check that appliances are connected via Powerline (the PL LED on the gateway should be solid)

**Sensors show unknown/empty data**
- Enable debug logging in HA to see which `key` names your gateway sends:
```yaml
logger:
  default: warning
  logs:
    custom_components.miele_xgw2000: debug
```

**Buttons are greyed out / unavailable**
- This is normal — the gateway only exposes actions that are valid in the appliance's current state. Start is only shown when the appliance is ready, stop only when it is running.

---

## Technical details

- **Communication:** Local HTTP only, no cloud access
- **Protocol:** XML over HTTP (Hausbus interface, firmware ≥ 3.0.0)
- **Push notifications:** UDP multicast 239.255.68.139
- **Polling:** Configurable, default 30 seconds
- **HA platforms:** `sensor`, `button`
- **Config entries:** Configured via UI, stored in HA's internal storage

---

## License

Apache License 2.0, see [LICENSE](LICENSE).
