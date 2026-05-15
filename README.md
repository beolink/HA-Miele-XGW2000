# Miele XGW 2000 — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Local integration for Miele@home appliances connected via the **XGW 2000** gateway. No cloud required — communicates directly with the gateway on your LAN using the Hausbus XML API.

## Features

- Sensors: status, program, phase, remaining time, start/end time
- Buttons: Start, Stop, Pause (and other actions exposed by the gateway)
- Push updates via UDP multicast (239.255.68.139) in addition to polling
- Fully configured through the Home Assistant UI

## Requirements

- Miele XGW 2000 gateway connected to your local network
- Home Assistant 2023.4.0 or newer
- HACS (for easy installation)

## Installation via HACS

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add this repository URL and select category **Integration**
4. Click **Download**
5. Restart Home Assistant

## Manual Installation

Copy the `custom_components/miele_xgw2000/` folder to your Home Assistant `config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Miele XGW 2000**
3. Enter:
   - **IP Address** — IP of your gateway (default: `192.168.1.237`)
   - **Username** — default: `xgw2000`
   - **Password** — default: `xgw2000`
   - **Poll interval** — seconds between updates (default: `30`, minimum: `10`)

## Gateway defaults

| Setting | Default value |
|---------|--------------|
| IP address | `192.168.1.237` |
| Username | `xgw2000` |
| Password | `xgw2000` |

The password can be changed in the gateway's web interface under **Status**.

## Supported appliances

Any Miele@home capable appliance connected to the XGW 2000, including:
- Washing machines
- Tumble dryers
- Dishwashers
- Ovens
- Refrigerators / freezers

Available sensors and actions depend on the appliance type and its current state.
