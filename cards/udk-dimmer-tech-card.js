class UdkDimmerTechCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (this._interacting) return;
    this._updateValues();
  }

  setConfig(config) {
    this._config = config;
    this._interacting = false;
    this._interactTimers = {};
    this._rendered = false;
  }

  _getDimmers() {
    if (!this._hass) return [];
    const dimmers = [];
    for (const [eid, state] of Object.entries(this._hass.states)) {
      if (!eid.startsWith('light.')) continue;
      const a = state.attributes;
      if (a.module_address === undefined || a.dimmer_index === undefined) continue;
      dimmers.push({
        entity_id: eid,
        name: a.friendly_name || eid,
        state: state.state,
        brightness: a.brightness || 0,
        module_address: a.module_address,
        dimmer_index: a.dimmer_index,
        phase_mode: a.phase_mode || null,
        grid_frequency: a.grid_frequency || null,
        emergency_stop: a.emergency_stop || false,
        overtemperature: a.overtemperature || false,
        offline: a.offline || false,
        overcurrent: a.overcurrent || false,
        load_error: a.load_error || false,
      });
    }
    dimmers.sort((a, b) => a.module_address - b.module_address || a.dimmer_index - b.dimmer_index);
    return dimmers;
  }

  _groupByModule(dimmers) {
    const groups = {};
    for (const d of dimmers) {
      const key = d.module_address;
      if (!groups[key]) groups[key] = [];
      groups[key].push(d);
    }
    return groups;
  }

  _phaseLabel(mode) {
    if (mode === 'leading_edge') return 'Anschnitt';
    if (mode === 'trailing_edge') return 'Abschnitt';
    return '—';
  }

  _statusIcons(d) {
    const icons = [];
    if (d.emergency_stop) icons.push('<span class="warn" title="NOT-AUS">NOT</span>');
    if (d.overtemperature) icons.push('<span class="warn" title="Übertemperatur">TEMP</span>');
    if (d.overcurrent) icons.push('<span class="warn" title="Überstrom">OC</span>');
    if (d.offline) icons.push('<span class="warn" title="Offline">OFF</span>');
    if (d.load_error) icons.push('<span class="warn" title="Lastart-Fehler">LOAD</span>');
    if (icons.length === 0) icons.push('<span class="ok">OK</span>');
    return icons.join(' ');
  }

  /** Full DOM build — only once. After that, _updateValues() patches in place. */
  _render() {
    if (!this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });

    const dimmers = this._getDimmers();
    const groups = this._groupByModule(dimmers);

    let html = '';
    for (const [addr, dims] of Object.entries(groups)) {
      const modName = `M${String(addr).padStart(2, '0')}`;
      html += `<div class="module-header">${modName} <span class="addr">Addr ${addr}</span></div>`;
      html += '<div class="module-grid">';
      for (const d of dims) {
        const dimName = d.name.replace(/^M\d+D\d+\s*-\s*/, '');
        const val = d.state === 'on' ? d.brightness : 0;
        const pct = this._fmtPct(val);
        html += `
          <div class="dimmer-row ${d.state === 'on' ? 'is-on' : ''}" data-eid="${d.entity_id}">
            <div class="dimmer-info">
              <span class="ch">D${d.dimmer_index}</span>
              <span class="dname">${this._esc(dimName)}</span>
            </div>
            <div class="slider-wrap">
              <button class="step" data-eid="${d.entity_id}" data-dir="-1" title="Feinjustierung −1">−</button>
              <input type="range" min="0" max="255" value="${val}"
                     data-eid="${d.entity_id}" class="slider">
              <button class="step" data-eid="${d.entity_id}" data-dir="1" title="Feinjustierung +1">+</button>
              <span class="pct">${pct}</span>
            </div>
            <div class="meta">
              <span class="phase" title="Schaltart">${this._phaseLabel(d.phase_mode)}</span>
              <span class="freq" title="Netzfrequenz">${d.grid_frequency || '—'}</span>
              <span class="status">${this._statusIcons(d)}</span>
            </div>
          </div>`;
      }
      html += '</div>';
    }

    if (dimmers.length === 0) {
      html = '<div class="empty">Keine Dimmer-Entities gefunden</div>';
    }

    const footer = `${dimmers.length} Dimmer auf ${Object.keys(groups).length} Modulen`;

    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block}
        ha-card{padding:20px;overflow-x:auto}
        h2{margin:0 0 16px 4px;font-size:1.4em;font-weight:500;color:var(--primary-text-color)}
        .module-header{
          font-weight:600;font-size:14px;color:var(--primary-color,#03a9f4);
          padding:12px 4px 4px;border-bottom:1px solid var(--divider-color,#333);
          margin-top:8px;
        }
        .module-header:first-child{margin-top:0}
        .module-header .addr{font-weight:400;color:var(--secondary-text-color);font-size:12px;margin-left:8px}
        .module-grid{padding:4px 0}
        .dimmer-row{
          display:grid;
          grid-template-columns:240px 260px 1fr;
          align-items:center;
          padding:6px 8px;
          border-bottom:1px solid var(--divider-color,#222);
          gap:12px;
        }
        .dimmer-row.is-on{background:var(--primary-color,#03a9f4)08}
        .dimmer-info{display:flex;align-items:center;gap:8px;min-width:0}
        .ch{
          font-weight:700;font-size:13px;color:var(--secondary-text-color);
          min-width:24px;
        }
        .dname{font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .slider-wrap{display:flex;align-items:center;gap:6px}
        .step{
          width:24px;height:24px;padding:0;flex-shrink:0;
          border:1px solid var(--divider-color,#444);border-radius:4px;
          background:var(--card-background-color,transparent);
          color:var(--primary-text-color);
          font-size:16px;line-height:1;cursor:pointer;
          display:flex;align-items:center;justify-content:center;
        }
        .step:hover{border-color:var(--primary-color,#03a9f4);color:var(--primary-color,#03a9f4)}
        .step:active{background:var(--primary-color,#03a9f4)30}
        .slider{
          width:140px;height:6px;-webkit-appearance:none;appearance:none;
          background:var(--divider-color,#444);border-radius:3px;outline:none;
          cursor:pointer;flex-shrink:0;
        }
        .slider::-webkit-slider-thumb{
          -webkit-appearance:none;width:18px;height:18px;border-radius:50%;
          background:var(--primary-color,#03a9f4);cursor:pointer;border:none;
        }
        .pct{font-size:13px;min-width:46px;text-align:right;color:var(--secondary-text-color);font-variant-numeric:tabular-nums}
        .meta{display:flex;align-items:center;gap:10px;font-size:12px}
        .phase{
          padding:2px 6px;border-radius:3px;
          background:var(--primary-color,#03a9f4)18;
          color:var(--primary-text-color);
        }
        .freq{color:var(--secondary-text-color)}
        .status .ok{color:var(--success-color,#4caf50);font-weight:600}
        .status .warn{
          color:var(--error-color,#db4437);font-weight:700;font-size:11px;
          padding:1px 4px;border:1px solid var(--error-color,#db4437);border-radius:3px;
          animation:blink 1s infinite;
        }
        @keyframes blink{50%{opacity:.5}}
        .foot{margin-top:12px;font-size:13px;color:var(--secondary-text-color)}
        .legend{
          margin-top:8px;padding:8px 0;font-size:12px;color:var(--secondary-text-color);
          border-top:1px solid var(--divider-color,#333);
          display:flex;flex-wrap:wrap;align-items:center;gap:4px;
        }
        .legend-title{font-weight:600;margin-right:4px}
        .legend-sep{color:var(--divider-color,#555)}
        .legend .ok{color:var(--success-color,#4caf50);font-weight:600}
        .legend .warn{color:var(--error-color,#db4437);font-weight:700;font-size:11px;padding:1px 4px;border:1px solid var(--error-color,#db4437);border-radius:3px}
        .empty{padding:20px;color:var(--secondary-text-color);font-style:italic}
        @media(max-width:700px){
          .dimmer-row{grid-template-columns:1fr;gap:4px}
          .meta{justify-content:flex-start}
          .slider{width:120px}
        }
      </style>
      <ha-card>
        <h2>UDK-04-10 Techniker-Ansicht</h2>
        ${html}
        <div class="foot">${footer}</div>
        <div class="legend">
          <span class="legend-title">Status:</span>
          <span class="ok">OK</span> = Kein Fehler
          <span class="legend-sep">|</span>
          <span class="warn">NOT</span> NOT-AUS
          <span class="legend-sep">|</span>
          <span class="warn">TEMP</span> Übertemperatur
          <span class="legend-sep">|</span>
          <span class="warn">OC</span> Überstrom
          <span class="legend-sep">|</span>
          <span class="warn">OFF</span> Offline
          <span class="legend-sep">|</span>
          <span class="warn">LOAD</span> Lastart-Fehler
        </div>
      </ha-card>`;

    this._bindSliders();
    this._rendered = true;
  }

  /** Patch existing DOM without full re-render — keeps slider interaction intact. */
  _updateValues() {
    if (!this._rendered) { this._render(); return; }
    if (!this._hass || !this.shadowRoot) return;

    const dimmers = this._getDimmers();
    for (const d of dimmers) {
      const row = this.shadowRoot.querySelector(`.dimmer-row[data-eid="${d.entity_id}"]`);
      if (!row) { this._render(); return; }  // structure changed, full re-render

      // Skip slider update if user is interacting with this entity
      if (!this._interactTimers[d.entity_id]) {
        const slider = row.querySelector('.slider');
        const pctEl = row.querySelector('.pct');
        const val = d.state === 'on' ? d.brightness : 0;
        if (slider) slider.value = val;
        if (pctEl) pctEl.textContent = this._fmtPct(val);
      }

      // Update on/off highlight
      row.classList.toggle('is-on', d.state === 'on');

      // Update status
      const statusEl = row.querySelector('.status');
      if (statusEl) statusEl.innerHTML = this._statusIcons(d);

      const phaseEl = row.querySelector('.phase');
      if (phaseEl) phaseEl.textContent = this._phaseLabel(d.phase_mode);

      const freqEl = row.querySelector('.freq');
      if (freqEl) freqEl.textContent = d.grid_frequency || '—';
    }
  }

  _bindSliders() {
    const self = this;

    this.shadowRoot.querySelectorAll('.slider').forEach(el => {
      // Live percentage update while dragging
      el.addEventListener('input', e => {
        const pctEl = e.target.parentElement.querySelector('.pct');
        if (pctEl) pctEl.textContent = self._fmtPct(parseInt(e.target.value));
      });

      // Mark as interacting on any touch/mouse
      const startInteract = () => {
        const eid = el.dataset.eid;
        self._interacting = true;
        clearTimeout(self._interactTimers[eid]);
        self._interactTimers[eid] = true;  // flag, not a timer yet
      };
      el.addEventListener('mousedown', startInteract);
      el.addEventListener('touchstart', startInteract, { passive: true });

      // Send command on release, then cooldown before allowing updates
      el.addEventListener('change', e => {
        self._sendValue(e.target.dataset.eid, parseInt(e.target.value));
      });
    });

    // Fine adjustment via -/+ buttons (single brightness steps)
    this.shadowRoot.querySelectorAll('.step').forEach(el => {
      el.addEventListener('click', () => {
        const eid = el.dataset.eid;
        const dir = parseInt(el.dataset.dir);
        const row = el.closest('.dimmer-row');
        const slider = row.querySelector('.slider');
        const val = Math.min(255, Math.max(0, parseInt(slider.value) + dir));
        slider.value = val;
        const pctEl = row.querySelector('.pct');
        if (pctEl) pctEl.textContent = self._fmtPct(val);
        self._sendValue(eid, val);
      });
    });
  }

  _sendValue(eid, val) {
    if (val === 0) {
      this._hass.callService('light', 'turn_off', { entity_id: eid });
    } else {
      this._hass.callService('light', 'turn_on', { entity_id: eid, brightness: val });
    }

    // Keep blocking updates for this entity for 5s (dimmer transition time)
    clearTimeout(this._interactTimers[eid]);
    this._interactTimers[eid] = setTimeout(() => {
      delete this._interactTimers[eid];
      // Check if any entity is still interacting
      this._interacting = Object.keys(this._interactTimers).length > 0;
    }, 5000);

    // Allow other entities to update immediately
    this._interacting = false;
  }

  /** One decimal so single brightness steps (1/255 ≈ 0.4%) stay visible. */
  _fmtPct(val) { return (val / 255 * 100).toFixed(1) + '%'; }

  _esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  getCardSize() { return 15; }
  static getStubConfig() { return {}; }
}

customElements.define('udk-dimmer-tech-card', UdkDimmerTechCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'udk-dimmer-tech-card',
  name: 'UDK Dimmer Tech Card',
  description: 'Technician view for UDK-04-10 dimmer modules with sliders and diagnostics',
});
