/**
 * Dashboard card tests. Run with: node --test tests/card.test.mjs
 *
 * The card is plain DOM, so a tiny stub is enough — no jsdom, no build step.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import assert from "node:assert/strict";
import test from "node:test";

const cardPath = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "custom_components",
  "runway_direction",
  "www",
  "runway-direction-card.js",
);

const rendered = { html: "" };

globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = {
      set innerHTML(value) {
        rendered.html = value;
      },
      get innerHTML() {
        return rendered.html;
      },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    return this.shadowRoot;
  }

  get isConnected() {
    return true;
  }

  dispatchEvent() {}
};
globalThis.customElements = { get: () => undefined, define: () => {} };
globalThis.window = { customCards: [], setInterval: () => 0, clearInterval: () => {} };
globalThis.document = { createElement: () => ({}) };
globalThis.CustomEvent = class {};

const Card = new Function(
  `${readFileSync(cardPath, "utf8")}\nreturn RunwayDirectionCard;`,
)();

const hoursFromNow = (hours) =>
  new Date(Date.now() + hours * 3600000).toISOString();

/** Midnight-anchored ISO timestamp, N days out at the given hour. */
const atDay = (days, hour) => {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + days);
  date.setHours(hour);
  return date.toISOString();
};

function states(slots, { icao = "EDDF", noiseRunways = ["25C"] } = {}) {
  const now = new Date().toISOString();
  const prefix = icao.toLowerCase();
  return {
    [`sensor.${prefix}_forecast`]: {
      state: "25C",
      last_updated: now,
      attributes: {
        icao,
        airport: "Frankfurt Main Airport",
        slots,
        sources: ["runwaydirectionforecast.com"],
      },
    },
    [`sensor.${prefix}_current_runway`]: {
      state: "25C",
      last_updated: now,
      attributes: { icao, runway_ref: "07C/25C", confidence: 100 },
    },
    [`binary_sensor.${prefix}_aircraft_noise`]: {
      state: "on",
      last_updated: now,
      attributes: { icao, noise_runways: noiseRunways },
    },
  };
}

function render(stateMap, config = {}) {
  rendered.html = "";
  const card = new Card();
  card.setConfig({ type: "custom:runway-direction-card", ...config });
  card.hass = { locale: { language: "en", time_format: "24" }, states: stateMap };
  card._render();
  return rendered.html;
}

const kinds = (html) =>
  [...html.matchAll(/data-kind="(\w+)"/g)].map((match) => match[1]);

/** Segments of one track, in day order. */
const trackSegments = (html, index) => {
  const track = html.split('<div class="track')[index + 1] || "";
  return [
    ...track.matchAll(/class="seg ([^"]*)"[\s\S]*?flex: 0 0 ([\d.]+)%/g),
  ].map((match) => ({ classes: match[1].split(" "), width: Number(match[2]) }));
};

test("segment width follows slot duration, not slot count", () => {
  const html = render(
    states([
      { start: atDay(1, 0), end: atDay(1, 6), runway: "25C", confidence_class: "high" },
      { start: atDay(1, 6), end: atDay(2, 0), runway: "07C", confidence_class: "high" },
    ]),
  );
  const segments = trackSegments(html, 1);

  assert.equal(segments.length, 2);
  assert.ok(Math.abs(segments[0].width - 25) < 0.01, "6 h slot covers a quarter");
  assert.ok(Math.abs(segments[1].width - 75) < 0.01, "18 h slot covers the rest");
});

test("missing slots become a visible gap", () => {
  const html = render(
    states([
      { start: atDay(1, 0), end: atDay(1, 6), runway: "25C", confidence_class: "high" },
      { start: atDay(1, 12), end: atDay(2, 0), runway: "07C", confidence_class: "high" },
    ]),
  );
  const segments = trackSegments(html, 1);

  assert.deepEqual(
    segments.map((segment) => segment.classes[0]),
    ["noise", "gap", "quiet"],
  );
  assert.deepEqual(
    segments.map((segment) => Math.round(segment.width)),
    [25, 25, 50],
  );
});

test("noise is decided by the integration's runway selection", () => {
  const slots = [
    { start: hoursFromNow(-1), end: hoursFromNow(7), runway: "25C", confidence_class: "high" },
  ];

  assert.ok(kinds(render(states(slots, { noiseRunways: ["25C"] }))).includes("noise"));
  assert.ok(kinds(render(states(slots, { noiseRunways: ["07C"] }))).includes("quiet"));
});

test("axis-only slots match any of their possible runway ends", () => {
  const html = render(
    states(
      [
        {
          start: hoursFromNow(-1),
          end: hoursFromNow(7),
          runway_options: ["25C", "25L", "25R"],
          direction: "west",
          confidence_class: "low",
          source: "betriebsrichtungsprognose.de",
        },
      ],
      { noiseRunways: ["25L"] },
    ),
  );

  assert.ok(kinds(html).includes("noise"));
});

test("low confidence and axis-only slots are marked uncertain", () => {
  const html = render(
    states([
      { start: atDay(1, 0), end: atDay(1, 12), runway: "25C", confidence_class: "high" },
      { start: atDay(1, 12), end: atDay(2, 0), runway: "25C", confidence_class: "low" },
    ]),
  );
  const segments = trackSegments(html, 1);

  assert.ok(!segments[0].classes.includes("uncertain"));
  assert.ok(segments[1].classes.includes("uncertain"));
});

test("the now marker is rendered once, on today's row", () => {
  const html = render(
    states([
      { start: hoursFromNow(-1), end: hoursFromNow(30), runway: "25C", confidence_class: "high" },
    ]),
  );

  assert.equal((html.match(/class="now"/g) || []).length, 1);
});

test("both layouts render without undefined values", () => {
  for (const layout of ["days", "compact"]) {
    const html = render(
      states([
        { start: hoursFromNow(-2), end: hoursFromNow(6), runway: "25C", confidence_class: "high" },
        { start: hoursFromNow(6), end: hoursFromNow(30), runway: "07C", confidence_class: "medium" },
      ]),
      { layout },
    );
    assert.ok(!/undefined|NaN|Invalid Date/.test(html), `${layout} layout is clean`);
  }
});

test("a single configured airport needs no card configuration", () => {
  const html = render(
    states([
      { start: hoursFromNow(-1), end: hoursFromNow(7), runway: "25C", confidence_class: "high" },
    ]),
  );

  assert.match(html, /Frankfurt Main Airport/);
  assert.ok(kinds(html).length > 0);
});

test("several airports require the card to name one", () => {
  const both = {
    ...states([
      { start: hoursFromNow(-1), end: hoursFromNow(7), runway: "25C", confidence_class: "high" },
    ]),
    ...states(
      [{ start: hoursFromNow(-1), end: hoursFromNow(7), runway: "27R", confidence_class: "high" }],
      { icao: "EGLL", noiseRunways: ["27R"] },
    ),
  };

  assert.match(render(both), /EDDF, EGLL/);

  const chosen = render(both, { airport: "EGLL" });
  assert.ok(kinds(chosen).length > 0);
  assert.ok(!/EDDF, EGLL/.test(chosen));
});

test("a slot without timestamps is skipped instead of breaking the card", () => {
  const html = render(states([{ runway: "25C", confidence_class: "high" }]));

  assert.ok(!/undefined|NaN|Invalid Date/.test(html));
});

test("without integration entities the card explains what to do", () => {
  const html = render({ "light.kitchen": { state: "on", attributes: {} } });

  assert.match(html, /Runway Direction/);
  assert.equal(kinds(html).length, 0);
});

test("invalid configuration is rejected", () => {
  const card = new Card();

  assert.throws(() => card.setConfig({ layout: "spiral" }), /layout/);
  assert.throws(() => card.setConfig({ days: 0 }), /days/);
});
