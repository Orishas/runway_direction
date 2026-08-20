/**
 * Runway Direction card.
 *
 * Shipped with the runway_direction integration and registered automatically
 * as a Lovelace resource. No build step, no dependencies.
 */

const CARD_VERSION = "0.1.0";
const MINUTE_MS = 60000;
const DAY_MS = 86400000;

const DEFAULT_CONFIG = {
  layout: "days",
  days: 5,
  show_header: true,
  show_hero: true,
  show_legend: true,
  show_now: true,
  show_footer: true,
};

const LAYOUTS = ["days", "compact"];

const TRANSLATIONS = {
  en: {
    title: "Runway direction",
    noiseActive: "Aircraft noise",
    quiet: "Quiet",
    since: "since",
    quietFrom: "Quiet expected from",
    noiseFrom: "Aircraft noise expected from",
    noChange: "No change forecast",
    legendNoise: "noise",
    legendQuiet: "quiet",
    legendUncertain: "low confidence",
    legendExtended: "extended forecast",
    legendGap: "no forecast",
    unavailable: "No forecast data available.",
    setup: "Add the Runway Direction integration to use this card.",
    missingAirport: "No airport matches this card's configuration.",
    source: "Source",
    stale: "Data may be outdated",
    confidence: "confidence",
    runway: "Runway",
  },
  de: {
    title: "Betriebsrichtung",
    noiseActive: "Fluglärm",
    quiet: "Ruhig",
    since: "seit",
    quietFrom: "Ruhe voraussichtlich ab",
    noiseFrom: "Fluglärm voraussichtlich ab",
    noChange: "Kein Wechsel in Sicht",
    legendNoise: "Lärm",
    legendQuiet: "ruhig",
    legendUncertain: "geringe Sicherheit",
    legendExtended: "verlängerte Prognose",
    legendGap: "keine Prognose",
    unavailable: "Keine Prognosedaten verfügbar.",
    setup: "Integration Runway Direction einrichten, um diese Karte zu nutzen.",
    missingAirport: "Kein Flughafen passt zur Konfiguration dieser Karte.",
    source: "Quelle",
    stale: "Daten möglicherweise veraltet",
    confidence: "Sicherheit",
    runway: "Bahn",
  },
};

const STYLES = `
  :host {
    --rd-noise: var(--rd-noise-color, var(--error-color, #db4437));
    --rd-quiet: var(--rd-quiet-color, var(--success-color, #43a047));
    --rd-track: var(--rd-track-color, var(--divider-color, #e0e0e0));
  }
  ha-card {
    padding: 12px 16px 14px;
    overflow: hidden;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  .header ha-icon {
    color: var(--secondary-text-color);
    --mdc-icon-size: 20px;
  }
  .header .name {
    font-size: 16px;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .header .code {
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .badge {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    padding: 3px 9px;
    border-radius: 12px;
    white-space: nowrap;
  }
  .badge ha-icon {
    --mdc-icon-size: 15px;
  }
  .badge.noise {
    color: var(--rd-noise);
    background: color-mix(in srgb, var(--rd-noise) 14%, transparent);
  }
  .badge.quiet {
    color: var(--rd-quiet);
    background: color-mix(in srgb, var(--rd-quiet) 14%, transparent);
  }
  .hero {
    display: flex;
    align-items: flex-end;
    gap: 16px;
    margin-bottom: 14px;
    cursor: pointer;
  }
  .hero .state {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 22px;
    font-weight: 500;
    line-height: 1.15;
    color: var(--primary-text-color);
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex: none;
  }
  .dot.noise { background: var(--rd-noise); }
  .dot.quiet { background: var(--rd-quiet); }
  .hero .sub {
    font-size: 13px;
    color: var(--secondary-text-color);
    margin-top: 4px;
  }
  .next {
    margin-left: auto;
    text-align: right;
    min-width: 0;
  }
  .next .label {
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .next .value {
    font-size: 15px;
    font-weight: 500;
    color: var(--primary-text-color);
    margin-top: 2px;
    white-space: nowrap;
  }
  .next .rel {
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .scale {
    display: flex;
    font-size: 11px;
    color: var(--secondary-text-color);
    margin-bottom: 5px;
  }
  .rows {
    position: relative;
  }
  .row {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
  }
  .row:last-child {
    margin-bottom: 0;
  }
  .row .day {
    flex: 0 0 62px;
    font-size: 12px;
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .row.today .day {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .track {
    position: relative;
    flex: 1 1 auto;
    display: flex;
    height: 18px;
    border-radius: 4px;
    overflow: hidden;
    background: var(--rd-track);
    min-width: 0;
  }
  .track.bar {
    height: 22px;
    border-radius: 5px;
  }
  .seg {
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    overflow: hidden;
    white-space: nowrap;
  }
  .seg.noise {
    background: color-mix(in srgb, var(--rd-noise) 22%, transparent);
    color: var(--rd-noise);
  }
  .seg.quiet {
    background: color-mix(in srgb, var(--rd-quiet) 22%, transparent);
    color: var(--rd-quiet);
  }
  .seg.gap {
    background: var(--card-background-color, transparent);
    border: 1px dashed var(--rd-track);
    box-sizing: border-box;
  }
  /* Low confidence and extended-range slots are hatched: the colour still
     says noise or quiet, the texture says do not plan your day around it. */
  .seg.uncertain {
    background-image: repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.55) 0 3px,
      rgba(255, 255, 255, 0) 3px 7px
    );
  }
  .seg.past {
    opacity: 0.45;
  }
  .now {
    position: absolute;
    top: -2px;
    bottom: -2px;
    width: 2px;
    background: var(--primary-text-color);
    z-index: 2;
    pointer-events: none;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 10px;
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .legend i {
    width: 9px;
    height: 9px;
    border-radius: 2px;
    display: inline-block;
  }
  .legend i.noise { background: color-mix(in srgb, var(--rd-noise) 40%, transparent); }
  .legend i.quiet { background: color-mix(in srgb, var(--rd-quiet) 40%, transparent); }
  .legend i.uncertain {
    background: color-mix(in srgb, var(--rd-quiet) 40%, transparent);
    background-image: repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.7) 0 2px,
      rgba(255, 255, 255, 0) 2px 4px
    );
  }
  .legend i.gap { border: 1px dashed var(--rd-track); box-sizing: border-box; }
  .footer {
    margin-top: 10px;
    font-size: 11px;
    color: var(--secondary-text-color);
  }
  .footer.stale {
    color: var(--warning-color, #ffa600);
  }
  .tooltip {
    position: absolute;
    z-index: 5;
    pointer-events: none;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    padding: 6px 9px;
    font-size: 12px;
    line-height: 1.35;
    color: var(--primary-text-color);
    box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.2));
    white-space: nowrap;
    transform: translate(-50%, -100%);
    opacity: 0;
    transition: opacity 90ms linear;
  }
  .tooltip.visible {
    opacity: 1;
  }
  .tooltip .meta {
    color: var(--secondary-text-color);
  }
  .empty {
    font-size: 13px;
    color: var(--secondary-text-color);
    padding: 4px 0;
  }
`;

function localize(hass, key) {
  const language = (hass && hass.locale && hass.locale.language) || "en";
  const table = TRANSLATIONS[language.split("-")[0]] || TRANSLATIONS.en;
  return table[key] || TRANSLATIONS.en[key] || key;
}

function parseDate(value) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfDay(date) {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function formatTime(hass, date) {
  const language = (hass.locale && hass.locale.language) || undefined;
  const format = hass.locale && hass.locale.time_format;
  const options = { hour: "2-digit", minute: "2-digit" };
  if (format === "12") {
    options.hour12 = true;
  } else if (format === "24") {
    options.hour12 = false;
  }
  return date.toLocaleTimeString(language, options);
}

function formatDay(hass, date) {
  const language = (hass.locale && hass.locale.language) || undefined;
  return date.toLocaleDateString(language, {
    weekday: "short",
    day: "numeric",
    month: "numeric",
  });
}

function formatDuration(minutes) {
  const total = Math.max(0, Math.round(minutes));
  if (total < 60) {
    return `${total} min`;
  }
  const hours = Math.floor(total / 60);
  if (hours < 48) {
    const rest = total % 60;
    return rest ? `${hours} h ${rest} min` : `${hours} h`;
  }
  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  return restHours ? `${days} d ${restHours} h` : `${days} d`;
}

class RunwayDirectionCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("runway-direction-card-editor");
  }

  static getStubConfig(hass) {
    const airports = RunwayDirectionCard.airports(hass);
    return airports.length > 1
      ? { type: "custom:runway-direction-card", airport: airports[0] }
      : { type: "custom:runway-direction-card" };
  }

  /** Every ICAO code the integration currently provides entities for. */
  static airports(hass) {
    const codes = [];
    for (const state of Object.values((hass && hass.states) || {})) {
      const icao = state.attributes && state.attributes.icao;
      if (icao && Array.isArray(state.attributes.slots) && !codes.includes(icao)) {
        codes.push(icao);
      }
    }
    return codes.sort();
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = { ...DEFAULT_CONFIG };
    this._hass = null;
    this._timer = null;
    this._fingerprint = null;
  }

  setConfig(config) {
    const merged = { ...DEFAULT_CONFIG, ...(config || {}) };
    if (!LAYOUTS.includes(merged.layout)) {
      throw new Error(`layout must be one of: ${LAYOUTS.join(", ")}`);
    }
    const days = Number(merged.days);
    if (!Number.isFinite(days) || days < 1 || days > 10) {
      throw new Error("days must be a number between 1 and 10");
    }
    merged.days = Math.round(days);
    this._config = merged;
    this._fingerprint = null;
    if (this._hass) {
      this._render();
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._renderIfChanged();
  }

  connectedCallback() {
    this._startTimer();
    if (this._hass) {
      this._render();
    }
  }

  disconnectedCallback() {
    this._stopTimer();
  }

  getCardSize() {
    let size = 1;
    if (this._config.show_hero) {
      size += 1;
    }
    size += this._config.layout === "days" ? Math.ceil(this._config.days / 2) : 1;
    return size;
  }

  _startTimer() {
    this._stopTimer();
    this._timer = window.setInterval(() => this._renderIfChanged(), MINUTE_MS);
  }

  _stopTimer() {
    if (this._timer) {
      window.clearInterval(this._timer);
      this._timer = null;
    }
  }

  _renderIfChanged() {
    if (!this._hass || !this.isConnected) {
      return;
    }
    const entities = this._entities();
    const parts = [Math.floor(Date.now() / MINUTE_MS)];
    for (const entityId of Object.values(entities)) {
      const state = entityId && this._hass.states[entityId];
      parts.push(entityId || "-", state ? state.last_updated : "-");
    }
    const fingerprint = parts.join("|");
    if (fingerprint === this._fingerprint) {
      return;
    }
    this._fingerprint = fingerprint;
    this._render(entities);
  }

  /** Resolve the entities of one airport, by config or by being the only one. */
  _entities() {
    const hass = this._hass;
    const config = this._config;
    if (config.forecast_entity || config.noise_entity || config.runway_entity) {
      return {
        forecast: config.forecast_entity,
        current: config.runway_entity,
        noise: config.noise_entity,
      };
    }

    const airports = RunwayDirectionCard.airports(hass);
    const icao = config.airport || (airports.length === 1 ? airports[0] : null);
    if (!icao) {
      return { forecast: null, current: null, noise: null, ambiguous: airports };
    }

    const find = (domain, predicate) =>
      Object.keys(hass.states).find((entityId) => {
        if (!entityId.startsWith(domain)) {
          return false;
        }
        const state = hass.states[entityId];
        return (
          state.attributes &&
          String(state.attributes.icao || "").toUpperCase() === icao.toUpperCase() &&
          predicate(state)
        );
      });

    return {
      icao,
      forecast: find("sensor.", (state) => Array.isArray(state.attributes.slots)),
      current: find("sensor.", (state) => state.attributes.runway_ref !== undefined),
      noise: find(
        "binary_sensor.",
        (state) => state.attributes.noise_runways !== undefined,
      ),
    };
  }

  _noiseRunways(entities) {
    if (Array.isArray(this._config.noise_runways)) {
      return this._config.noise_runways;
    }
    const noiseState = entities.noise && this._hass.states[entities.noise];
    const configured = noiseState && noiseState.attributes.noise_runways;
    return Array.isArray(configured) ? configured : [];
  }

  _timeline(entities, noiseRunways) {
    const hass = this._hass;
    const forecast = entities.forecast && hass.states[entities.forecast];
    const slots = (forecast && forecast.attributes.slots) || [];

    const intervals = [];
    for (const slot of slots) {
      const start = parseDate(slot.start);
      const end = parseDate(slot.end);
      if (!start || !end || end <= start) {
        continue;
      }
      const runways = [
        ...(slot.runway ? [slot.runway] : []),
        ...(Array.isArray(slot.runway_options) ? slot.runway_options : []),
      ];
      intervals.push({
        start,
        end,
        runway: slot.runway || null,
        runwayOptions: Array.isArray(slot.runway_options) ? slot.runway_options : [],
        direction: slot.direction || null,
        confidence: slot.confidence ?? null,
        confidenceClass: slot.confidence_class || null,
        source: slot.source || null,
        kind: runways.some((end) => noiseRunways.includes(end)) ? "noise" : "quiet",
        uncertain: slot.confidence_class === "low" || !slot.runway,
      });
    }
    intervals.sort((a, b) => a.start - b.start);

    const filled = [];
    intervals.forEach((interval, index) => {
      const previous = intervals[index - 1];
      if (previous && interval.start - previous.end > MINUTE_MS) {
        filled.push({ start: previous.end, end: interval.start, kind: "gap" });
      }
      filled.push(interval);
    });
    return filled;
  }

  _nextChange(timeline, now) {
    const active = timeline.find(
      (interval) => interval.start <= now && interval.end > now,
    );
    const activeKind = active ? active.kind : null;
    for (const interval of timeline) {
      if (interval.end <= now || interval.kind === "gap") {
        continue;
      }
      if (activeKind && interval.kind === activeKind) {
        continue;
      }
      if (!activeKind && interval.start <= now) {
        continue;
      }
      return interval;
    }
    return null;
  }

  _slice(timeline, rangeStart, rangeEnd, now) {
    const span = rangeEnd - rangeStart;
    const segments = [];
    for (const interval of timeline) {
      const start = Math.max(interval.start.getTime(), rangeStart);
      const end = Math.min(interval.end.getTime(), rangeEnd);
      if (end <= start) {
        continue;
      }
      const cuts = [start];
      if (now > start && now < end) {
        cuts.push(now);
      }
      cuts.push(end);
      for (let index = 0; index < cuts.length - 1; index += 1) {
        segments.push({
          interval,
          start: cuts[index],
          end: cuts[index + 1],
          past: cuts[index + 1] <= now,
          width: ((cuts[index + 1] - cuts[index]) / span) * 100,
        });
      }
    }
    return segments;
  }

  _segmentHtml(segment, showLabel) {
    const interval = segment.interval;
    const classes = ["seg", interval.kind];
    if (interval.uncertain) {
      classes.push("uncertain");
    }
    if (segment.past) {
      classes.push("past");
    }
    const label =
      showLabel && segment.width >= 14 && interval.kind !== "gap"
        ? interval.runway || interval.direction || ""
        : "";
    return `<div class="${classes.join(" ")}" style="flex: 0 0 ${segment.width.toFixed(
      3,
    )}%;" data-start="${segment.start}" data-end="${segment.end}" data-kind="${
      interval.kind
    }" data-runway="${interval.runway || ""}" data-options="${(
      interval.runwayOptions || []
    ).join(", ")}" data-confidence="${
      interval.confidence ?? ""
    }" data-source="${interval.source || ""}">${label}</div>`;
  }

  _nowMarker(rangeStart, rangeEnd, now) {
    if (!this._config.show_now || now < rangeStart || now > rangeEnd) {
      return "";
    }
    const position = ((now - rangeStart) / (rangeEnd - rangeStart)) * 100;
    return `<div class="now" style="left: ${position.toFixed(3)}%;"></div>`;
  }

  _daysHtml(timeline, now) {
    const hass = this._hass;
    const today = startOfDay(new Date(now));
    const lastEnd = timeline.length
      ? timeline[timeline.length - 1].end.getTime()
      : now;
    const maxDays = Math.ceil((lastEnd - today.getTime()) / DAY_MS);
    const dayCount = Math.max(1, Math.min(this._config.days, maxDays));

    const scale = [0, 6, 12, 18]
      .map(
        (hour) =>
          `<span style="flex: 1 1 0;">${String(hour).padStart(2, "0")}</span>`,
      )
      .join("");

    const rows = [];
    for (let index = 0; index < dayCount; index += 1) {
      const dayStart = today.getTime() + index * DAY_MS;
      const dayEnd = dayStart + DAY_MS;
      const segments = this._slice(timeline, dayStart, dayEnd, now);
      const isToday = index === 0;
      rows.push(`
        <div class="row${isToday ? " today" : ""}">
          <span class="day">${formatDay(hass, new Date(dayStart))}</span>
          <div class="track">
            ${segments.map((segment) => this._segmentHtml(segment, false)).join("")}
            ${isToday ? this._nowMarker(dayStart, dayEnd, now) : ""}
          </div>
        </div>
      `);
    }

    return `
      <div class="scale">
        <span style="flex: 0 0 62px;"></span>
        ${scale}
      </div>
      <div class="rows">${rows.join("")}</div>
    `;
  }

  _compactHtml(timeline, now) {
    const hass = this._hass;
    const today = startOfDay(new Date(now));
    const rangeStart = today.getTime();
    const lastEnd = timeline.length
      ? timeline[timeline.length - 1].end.getTime()
      : rangeStart + DAY_MS;
    const rangeEnd = Math.min(lastEnd, rangeStart + this._config.days * DAY_MS);
    const segments = this._slice(timeline, rangeStart, rangeEnd, now);
    const dayCount = Math.max(1, Math.round((rangeEnd - rangeStart) / DAY_MS));
    const ticks = [];
    for (let index = 0; index < dayCount; index += 1) {
      const dayStart = rangeStart + index * DAY_MS;
      const width =
        (Math.min(dayStart + DAY_MS, rangeEnd) - dayStart) / (rangeEnd - rangeStart);
      ticks.push(
        `<span style="flex: 0 0 ${(width * 100).toFixed(3)}%;">${formatDay(
          hass,
          new Date(dayStart),
        )}</span>`,
      );
    }
    return `
      <div class="rows">
        <div class="track bar">
          ${segments.map((segment) => this._segmentHtml(segment, true)).join("")}
          ${this._nowMarker(rangeStart, rangeEnd, now)}
        </div>
      </div>
      <div class="scale" style="margin: 4px 0 0;">${ticks.join("")}</div>
    `;
  }

  _heroHtml(entities, timeline, now) {
    const hass = this._hass;
    const active = timeline.find(
      (interval) => interval.start <= now && interval.end > now,
    );
    if (!active) {
      return "";
    }

    const label = active.runway
      ? `${localize(hass, "runway")} ${active.runway}`
      : active.direction || "";
    const running = timeline
      .filter((interval) => interval.end <= now && interval.kind === active.kind)
      .reduce((earliest, interval) => Math.min(earliest, interval.start), active.start);
    const minutes = (now - running) / MINUTE_MS;
    const sub = `${
      active.kind === "noise" ? localize(hass, "noiseActive") : localize(hass, "quiet")
    } ${localize(hass, "since")} ${formatDuration(minutes)}`;

    const change = this._nextChange(timeline, now);
    let next = `<div class="label">${localize(hass, "noChange")}</div>`;
    if (change) {
      const heading =
        change.kind === "noise"
          ? localize(hass, "noiseFrom")
          : localize(hass, "quietFrom");
      next = `
        <div class="label">${heading}</div>
        <div class="value">${formatDay(hass, change.start)}, ${formatTime(
          hass,
          change.start,
        )}</div>
        <div class="rel">${formatDuration((change.start.getTime() - now) / MINUTE_MS)}</div>
      `;
    }

    return `
      <div class="hero" data-entity="${entities.current || entities.forecast || ""}">
        <div>
          <div class="state"><span class="dot ${active.kind}"></span>${label}</div>
          <div class="sub">${sub}</div>
        </div>
        <div class="next">${next}</div>
      </div>
    `;
  }

  _headerHtml(entities) {
    const hass = this._hass;
    const forecast = entities.forecast && hass.states[entities.forecast];
    const airport =
      (forecast && forecast.attributes.airport) ||
      this._config.title ||
      localize(hass, "title");
    const icao = (forecast && forecast.attributes.icao) || entities.icao || "";
    return `
      <div class="header">
        <ha-icon icon="${this._config.icon || "mdi:airport"}"></ha-icon>
        <span class="name">${this._config.title || airport}</span>
        ${icao ? `<span class="code">${icao}</span>` : ""}
      </div>
    `;
  }

  _legendHtml() {
    const hass = this._hass;
    return `
      <div class="legend">
        <span><i class="noise"></i>${localize(hass, "legendNoise")}</span>
        <span><i class="quiet"></i>${localize(hass, "legendQuiet")}</span>
        <span><i class="uncertain"></i>${localize(hass, "legendUncertain")}</span>
        <span><i class="gap"></i>${localize(hass, "legendGap")}</span>
      </div>
    `;
  }

  _footerHtml(entities) {
    const hass = this._hass;
    const forecast = entities.forecast && hass.states[entities.forecast];
    if (!forecast) {
      return "";
    }
    const sources = forecast.attributes.sources;
    const updated = parseDate(forecast.last_updated);
    const stale = updated && Date.now() - updated.getTime() > 6 * 3600000;
    if (!Array.isArray(sources) || !sources.length) {
      return "";
    }
    return `<div class="footer${stale ? " stale" : ""}">${
      stale ? `${localize(hass, "stale")} · ` : ""
    }${localize(hass, "source")}: ${sources.join(", ")}</div>`;
  }

  _render(entities) {
    const hass = this._hass;
    if (!hass) {
      return;
    }
    const resolved = entities || this._entities();
    const now = Date.now();

    if (resolved.ambiguous && resolved.ambiguous.length > 1) {
      this.shadowRoot.innerHTML = `
        <style>${STYLES}</style>
        <ha-card><div class="empty">${localize(
          hass,
          "missingAirport",
        )} (${resolved.ambiguous.join(", ")})</div></ha-card>
      `;
      return;
    }

    if (!resolved.forecast) {
      this.shadowRoot.innerHTML = `
        <style>${STYLES}</style>
        <ha-card><div class="empty">${localize(hass, "setup")}</div></ha-card>
      `;
      return;
    }

    const noiseRunways = this._noiseRunways(resolved);
    const timeline = this._timeline(resolved, noiseRunways);
    const body = timeline.length
      ? this._config.layout === "days"
        ? this._daysHtml(timeline, now)
        : this._compactHtml(timeline, now)
      : `<div class="empty">${localize(hass, "unavailable")}</div>`;

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <ha-card>
        ${this._config.show_header ? this._headerHtml(resolved) : ""}
        ${this._config.show_hero ? this._heroHtml(resolved, timeline, now) : ""}
        ${body}
        ${this._config.show_legend && timeline.length ? this._legendHtml() : ""}
        ${this._config.show_footer ? this._footerHtml(resolved) : ""}
        <div class="tooltip"></div>
      </ha-card>
    `;
    this._attachHandlers(resolved);
  }

  _attachHandlers(entities) {
    const root = this.shadowRoot;
    const tooltip = root.querySelector(".tooltip");

    const hero = root.querySelector(".hero");
    if (hero) {
      hero.addEventListener("click", () =>
        this._moreInfo(entities.current || entities.forecast),
      );
    }
    const header = root.querySelector(".header .name");
    if (header && entities.forecast) {
      header.style.cursor = "pointer";
      header.addEventListener("click", () => this._moreInfo(entities.forecast));
    }

    const showTooltip = (event) => {
      const segment = event.target.closest(".seg");
      if (!segment || !tooltip) {
        return;
      }
      tooltip.innerHTML = this._tooltipHtml(segment);
      const cardRect = root.querySelector("ha-card").getBoundingClientRect();
      const rect = segment.getBoundingClientRect();
      const left = Math.min(
        Math.max(rect.left + rect.width / 2 - cardRect.left, 70),
        cardRect.width - 70,
      );
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${rect.top - cardRect.top - 6}px`;
      tooltip.classList.add("visible");
    };
    const hideTooltip = () => {
      if (tooltip) {
        tooltip.classList.remove("visible");
      }
    };

    root.querySelectorAll(".track").forEach((track) => {
      track.addEventListener("pointerover", showTooltip);
      track.addEventListener("pointerleave", hideTooltip);
      track.addEventListener("click", (event) => {
        showTooltip(event);
        window.setTimeout(hideTooltip, 2500);
      });
    });
  }

  _tooltipHtml(segment) {
    const hass = this._hass;
    const start = new Date(Number(segment.dataset.start));
    const end = new Date(Number(segment.dataset.end));
    const kind = segment.dataset.kind;

    if (kind === "gap") {
      return `
        <span class="meta">${localize(hass, "legendGap")}</span><br />
        ${formatDay(hass, start)}, ${formatTime(hass, start)}–${formatTime(hass, end)}
      `;
    }

    const runway = segment.dataset.runway;
    const options = segment.dataset.options;
    const confidence = segment.dataset.confidence;
    const source = segment.dataset.source;
    const heading = runway
      ? `<b>${localize(hass, "runway")} ${runway}</b>`
      : `<b>${options || "—"}</b>`;
    const meta = [
      kind === "noise" ? localize(hass, "legendNoise") : localize(hass, "legendQuiet"),
      confidence ? `${confidence}% ${localize(hass, "confidence")}` : "",
      source,
    ]
      .filter(Boolean)
      .join(" · ");

    return `
      ${heading}<br />
      ${formatDay(hass, start)}, ${formatTime(hass, start)}–${formatTime(hass, end)}<br />
      <span class="meta">${meta}</span>
    `;
  }

  _moreInfo(entityId) {
    if (!entityId) {
      return;
    }
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

class RunwayDirectionCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = { ...DEFAULT_CONFIG };
    this._form = null;
  }

  setConfig(config) {
    this._config = { ...DEFAULT_CONFIG, ...(config || {}) };
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _schema() {
    const airports = RunwayDirectionCard.airports(this._hass);
    return [
      { name: "title", selector: { text: {} } },
      {
        name: "airport",
        selector: {
          select: {
            mode: "dropdown",
            options: airports.map((icao) => ({ value: icao, label: icao })),
          },
        },
      },
      {
        name: "layout",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "days", label: "Days (one row per day)" },
              { value: "compact", label: "Compact (single bar)" },
            ],
          },
        },
      },
      {
        name: "days",
        selector: { number: { min: 1, max: 10, step: 1, mode: "slider" } },
      },
      {
        name: "",
        type: "grid",
        schema: [
          { name: "show_header", selector: { boolean: {} } },
          { name: "show_hero", selector: { boolean: {} } },
          { name: "show_legend", selector: { boolean: {} } },
          { name: "show_now", selector: { boolean: {} } },
          { name: "show_footer", selector: { boolean: {} } },
        ],
      },
    ];
  }

  _update() {
    if (!this._hass) {
      return;
    }
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) =>
        schema.name.replace(/_/g, " ").replace(/^./, (char) => char.toUpperCase());
      this._form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: { ...event.detail.value, type: this._config.type } },
            bubbles: true,
            composed: true,
          }),
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = this._schema();
    this._form.data = this._config;
  }
}

if (!customElements.get("runway-direction-card")) {
  customElements.define("runway-direction-card", RunwayDirectionCard);
  customElements.define("runway-direction-card-editor", RunwayDirectionCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "runway-direction-card")) {
  window.customCards.push({
    type: "runway-direction-card",
    name: "Runway Direction",
    description: "Runway in use and aircraft noise forecast for any airport.",
    documentationURL: "https://github.com/Orishas/runway_direction",
  });
}

console.info(
  `%c RUNWAY-DIRECTION-CARD %c ${CARD_VERSION} `,
  "color: white; background: #3f51b5; font-weight: 700;",
  "color: #3f51b5; background: white; font-weight: 700;",
);
