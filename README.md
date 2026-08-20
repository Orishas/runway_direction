# Runway Direction for Home Assistant

[![version](https://img.shields.io/github/manifest-json/v/Orishas/runway_direction?filename=custom_components%2Frunway_direction%2Fmanifest.json&color=slateblue)](https://github.com/Orishas/runway_direction/releases/latest)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?logo=HomeAssistantCommunityStore&logoColor=white)](https://www.hacs.xyz/)
[![HACS validation](https://github.com/Orishas/runway_direction/actions/workflows/hacs.yml/badge.svg)](https://github.com/Orishas/runway_direction/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/Orishas/runway_direction/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Orishas/runway_direction/actions/workflows/hassfest.yml)
[![Tests](https://github.com/Orishas/runway_direction/actions/workflows/tests.yml/badge.svg)](https://github.com/Orishas/runway_direction/actions/workflows/tests.yml)

Home Assistant integration for the runway expected to be in use at any of about
2500 airports worldwide, with an aircraft noise indicator for your location.

Add one airport per config entry, pick the runway ends whose traffic you hear,
and get sensors for the runway in use, the forecast, and when noise is expected
to start.

## What this forecast is, and what it is not

**It is derived from wind, not published by air traffic control.** The sources
compute which runway offers the best headwind. They do not know local runway
usage schemes, noise abatement procedures, capacity constraints or preferred
directions.

That has visible consequences. For Frankfurt in calm wind, the worldwide source
proposes runway 18/36 — a departure-only runway, with "36" never in use at all —
and does so partly at high confidence. For Heathrow it alternates between 27R
and 09L while the airport in reality runs westerly almost throughout.

So the integration carries the uncertainty rather than hiding it:

- every slot keeps the source it came from
- every slot keeps its confidence, and `binary_sensor.<icao>_forecast_uncertain`
  turns on below a threshold you choose
- where a source cannot support a direction at all — a tendency near zero, or
  wind below 3 kn, at which point airports follow their preferred direction
  rather than the wind — the forecast shows a gap instead of a guess

Treat it as a tendency, not a schedule. If your airport publishes an official
operating direction forecast, that will always beat this.

**For Frankfurt (EDDF) it does:** the
[fra_betriebsrichtung](https://github.com/Orishas/fra_betriebsrichtung)
integration reads the official Umwelthaus forecast and is more accurate. Use
that one for Frankfurt, and this one for everywhere else.

## Entities

One device and one set of entities per configured airport, prefixed with the
ICAO code.

| Entity | State | Purpose |
| --- | --- | --- |
| `sensor.<icao>_current_runway` | e.g. `25C` | Runway expected to be in use now |
| `sensor.<icao>_forecast` | e.g. `07C` | Next runway, with all slots as attributes |
| `sensor.<icao>_confidence` | 0-100 | Confidence of the current forecast |
| `sensor.<icao>_headwind` | km/h | Headwind on the runway in use |
| `sensor.<icao>_crosswind` | km/h | Crosswind on the runway in use |
| `sensor.<icao>_next_aircraft_noise` | timestamp | When a runway you selected is next in use |
| `binary_sensor.<icao>_aircraft_noise` | `on` / `off` | A runway you selected is in use now |
| `binary_sensor.<icao>_aircraft_noise_warning` | `on` / `off` | Noise is forecast within your warning window |
| `binary_sensor.<icao>_forecast_uncertain` | `on` / `off` | Current forecast is below your confidence threshold |

The `slots` attribute on the forecast sensor holds the merged timeline:

```json
[
  {
    "start": "2026-08-20T14:00:00+02:00",
    "end": "2026-08-20T20:00:00+02:00",
    "from": "14:00",
    "to": "20:00",
    "date": "2026-08-20",
    "runway": "25C",
    "runway_ref": "07C/25C",
    "heading": 250,
    "confidence": 100,
    "confidence_class": "high",
    "source": "runwaydirectionforecast.com",
    "wind_kmh": 20,
    "headwind_kmh": 20,
    "crosswind_kmh": 1
  }
]
```

## Installation

### HACS

1. Add this repository as a custom repository:
   `https://github.com/Orishas/runway_direction`, category `Integration`.
2. Download it and restart Home Assistant.
3. Add the integration from **Settings > Devices & services**.

### Manual

Copy `custom_components/runway_direction` into your Home Assistant
configuration directory, restart Home Assistant, and add the integration from
the UI.

## Configuration

1. **Settings > Devices & services > Add integration**, pick `Runway Direction`.
2. Search by ICAO or IATA code, airport or city name — or leave the search empty
   to get the airports nearest to your Home Assistant location.
3. Select the airport.
4. Pick the runway ends whose traffic is audible where you live, a warning time,
   and the confidence below which a forecast counts as uncertain.

Repeat for as many airports as you like. All settings can be changed later from
the integration options.

## Dashboard card

The integration ships its own card, served and registered automatically — there
is no dashboard resource to add by hand. Force-reload the browser once after
installing, then `Runway Direction` appears in the card picker.

```yaml
type: custom:runway-direction-card
```

With one airport configured it needs no configuration at all. With several, name
one:

```yaml
type: custom:runway-direction-card
airport: EGLL
layout: days
days: 5
```

The card draws one row per day on a 24-hour scale (`layout: days`) or a single
continuous bar (`layout: compact`). Segment width follows real slot duration,
gaps stay visible as gaps, and **low-confidence periods are hatched** rather than
drawn as solid fact.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `airport` | ICAO code | auto | Required only when several airports are configured |
| `layout` | `days` \| `compact` | `days` | One row per day, or a single bar |
| `days` | number (1-10) | `5` | Days of forecast to show |
| `title` | string | airport name | Card title |
| `icon` | string | `mdi:airport` | Header icon |
| `show_header` / `show_hero` / `show_legend` / `show_now` / `show_footer` | boolean | `true` | Card sections |
| `noise_runways` | list | from integration | Override which runway ends count as noisy |

Colours follow your theme and can be overridden with `rd-noise-color`,
`rd-quiet-color` and `rd-track-color`.

## Events

`runway_direction_runway_changed` fires when the runway in use changes, with
`icao`, `airport`, `old_runway`, `new_runway`, `confidence`, `confidence_class`,
`noise_runways`, `noise_active` and `source`.

## Service action

`runway_direction.refresh` fetches new data immediately. Pass `icao` to refresh
one airport, omit it for all of them. With `response_variable` it returns a
compact summary per airport for use in automations.

## Automation example

```yaml
automation:
  - alias: "Aircraft noise expected, and the forecast is worth trusting"
    trigger:
      - platform: state
        entity_id: binary_sensor.eddm_aircraft_noise_warning
        to: "on"
    condition:
      - condition: state
        entity_id: binary_sensor.eddm_forecast_uncertain
        state: "off"
    action:
      - service: notify.mobile_app_phone
        data:
          message: >-
            Aircraft noise expected in
            {{ state_attr('binary_sensor.eddm_aircraft_noise_warning', 'starts_in_minutes') }}
            minutes.
```

## Data sources

Public HTML pages only, polled every 30 minutes. No hidden or undocumented API
endpoints.

| Source | Coverage | Range | Resolves |
| --- | --- | --- | --- |
| [runwaydirectionforecast.com](https://www.runwaydirectionforecast.com/) | ~2500 airports, 223 countries | 2 days, 3-hour steps | a specific runway |
| [betriebsrichtungsprognose.de](https://betriebsrichtungsprognose.de/) | 27 airports in Germany and Austria | 5 days, 3-hour steps | a runway axis only |

Where both cover an airport, the precise one wins for its two days and the other
extends the forecast to five. Because the second only resolves an axis, its
slots list every runway end pointing that way and never claim high confidence.

The airport index is read once while adding an airport, never while polling.

## Troubleshooting

- Open the integration diagnostics from **Settings > Devices & services**. It
  reports, per source, whether it is supported for that airport and how many
  slots it contributed. A source that silently stopped parsing shows zero.
- Website structures change. Parser failures are handled gracefully — the
  integration does not invent runway data.
- If the dashboard card is missing after an update, force-reload the browser.

## Development

```bash
python -m pytest tests            # integration tests
node --test tests/card.test.mjs   # dashboard card tests
```

Both run in CI. Parser tests work against captured pages in `tests/fixtures/`,
so a source changing its markup fails a test rather than going unnoticed.

## Acknowledgements

Thanks to runwaydirectionforecast.com and betriebsrichtungsprognose.de for
publishing runway direction information.

This integration is not affiliated with, endorsed by, or officially connected to
those websites or their operators.
