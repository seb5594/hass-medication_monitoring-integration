const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function card() {
  const registered = new Map();
  class HTMLElement {
    attachShadow() { this.shadowRoot = { innerHTML: "", querySelectorAll: () => [] }; }
  }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,
    "../custom_components/medication_monitoring/www/medication-monitoring-card.js"), "utf8"), {
    HTMLElement, window: {}, console: { info() {} }, Date, Intl,
    customElements: { get: name => registered.get(name), define: (name, type) => registered.set(name, type) },
  });
  return new (registered.get("medication-monitoring-card"))();
}

test("card follows profile language and normalizes regional tags", () => {
  const c = card();
  for (const language of ["de", "de-AT", "de_CH", "DE-de"]) {
    c.hass = { language, locale: { language: "en" }, states: {} };
    assert.equal(c._language, "de");
    assert.match(c.shadowRoot.innerHTML, /Keine Medikamente gefunden/);
  }
  c.hass = { language: "fr", states: {} };
  assert.match(c.shadowRoot.innerHTML, /No medications found/);
});

test("translated and renamed entities keep their medication and actions", () => {
  const c = card();
  const states = {};
  function add(id, role, entry = "profile1") {
    states[id] = { entity_id: id, state: role === "next_dose" ? "2026-11-20T08:00:00+01:00" : "2",
      attributes: { tracker_domain: "medication_monitoring", tracker_entry_id: entry,
        medication_id: "same-medication-id", medication_name: "Vitamin D", medication_role: role,
        friendly_name: "Vitamin D Nächste Einnahme" } };
  }
  add("sensor.vollstaendig_umbenannt", "next_dose");
  add("button.einnahme_bestaetigen", "mark_taken");
  add("button.einnahme_auslassen", "mark_skipped");
  add("sensor.vorratsmenge", "stock");
  add("number.vorrat_auffuellen", "stock_number");
  add("sensor.andere_person", "next_dose", "profile2");
  add("button.andere_person", "mark_taken", "profile2");
  c.hass = { language: "de", states };
  assert.equal(c._medications.length, 2);
  assert.equal(c._medications[0].name, "Vitamin D");
  assert.equal(c._medications[0].btn_taken.entity_id, "button.einnahme_bestaetigen");
  assert.equal(c._medications[1].btn_taken.entity_id, "button.andere_person");
  assert.match(c.shadowRoot.innerHTML, /Als eingenommen markieren/);
  assert.match(c.shadowRoot.innerHTML, /data-entity="number.vorrat_auffuellen"/);
});

test("old entity ids still work without new metadata", () => {
  const c = card();
  c.hass = { language: "de", states: {
    "sensor.aspirin_next_dose": { entity_id: "sensor.aspirin_next_dose", state: "unknown",
      attributes: { tracker_domain: "medication_monitoring", friendly_name: "Aspirin Next Dose" } },
    "button.aspirin_mark_taken": { entity_id: "button.aspirin_mark_taken", state: "unknown", attributes: {} },
  } };
  assert.equal(c._medications[0].name, "Aspirin");
  assert.equal(c._medications[0].btn_taken.entity_id, "button.aspirin_mark_taken");
});
