class UdkDimmerCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._configEntity];
    const key = state ? state.last_updated : '';
    if (key !== this._lastKey && !this._editing) {
      this._lastKey = key;
      this._render();
    }
  }

  setConfig(config) {
    this._config = config;
    this._configEntity = config.config_entity || 'sensor.udk_04_10_dimmer_dimmer_config';
    this._lastKey = '';
    this._editing = false;
    this._showAdd = false;
  }

  _getModules() {
    if (!this._hass) return [];
    const state = this._hass.states[this._configEntity];
    if (!state || !state.attributes || !state.attributes.modules) return [];
    return state.attributes.modules;
  }

  async _save(address, key, value) {
    if (!this._hass) return;
    try {
      await this._hass.callService('ha_udk_0410_dimmer', 'update_module', {
        address: address, key: key, value: value,
      });
    } catch (e) {
      alert('Speichern fehlgeschlagen: ' + e.message);
    }
  }

  async _addModule(address, name) {
    if (!this._hass) return;
    try {
      await this._hass.callService('ha_udk_0410_dimmer', 'add_module', { address, name });
      this._showAdd = false;
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }

  async _removeModule(address, name) {
    if (!this._hass) return;
    // Use a custom confirm via rendering
    this._confirmDelete = { address, name };
    this._render();
  }

  async _doRemove(address) {
    this._confirmDelete = null;
    try {
      await this._hass.callService('ha_udk_0410_dimmer', 'remove_module', { address });
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }

  _render() {
    if (!this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });

    const modules = this._getModules();

    let rows = '';
    for (const m of modules) {
      const addr = m.address || 0;
      const name = m.name || '';
      const dimmers = m.dimmers || [];
      while (dimmers.length < 4) dimmers.push({ index: dimmers.length + 1, name: '' });

      const isDeleting = this._confirmDelete && this._confirmDelete.address === addr;

      rows += `
        <tr>
          <td class="addr">${addr}</td>
          <td class="mname"><input type="text" value="${this._esc(name)}" data-addr="${addr}" data-key="name"></td>
          <td class="dname"><input type="text" value="${this._esc(dimmers[0].name)}" data-addr="${addr}" data-key="d1"></td>
          <td class="dname"><input type="text" value="${this._esc(dimmers[1].name)}" data-addr="${addr}" data-key="d2"></td>
          <td class="dname"><input type="text" value="${this._esc(dimmers[2].name)}" data-addr="${addr}" data-key="d3"></td>
          <td class="dname"><input type="text" value="${this._esc(dimmers[3].name)}" data-addr="${addr}" data-key="d4"></td>
          <td class="action">${isDeleting
            ? `<button class="confirm-yes" data-addr="${addr}">Ja</button><button class="confirm-no">Nein</button>`
            : `<button class="del" data-addr="${addr}" data-name="${this._esc(name)}">✕</button>`
          }</td>
        </tr>`;
    }

    // Add module form row
    let addRow = '';
    if (this._showAdd) {
      const nextAddr = modules.length > 0 ? Math.max(...modules.map(m => m.address || 0)) + 1 : 1;
      addRow = `
        <tr class="add-row">
          <td class="addr"><input type="number" id="new-addr" value="${nextAddr}" min="1" max="247" style="width:50px;text-align:center"></td>
          <td class="mname"><input type="text" id="new-name" value="M${String(nextAddr).padStart(2,'0')}" placeholder="Name"></td>
          <td colspan="4" class="add-hint">Dimmer-Namen können nach dem Anlegen editiert werden</td>
          <td class="action">
            <button class="save-add">✓</button>
            <button class="cancel-add">✕</button>
          </td>
        </tr>`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block}
        ha-card{padding:20px;overflow-x:auto}
        h2{margin:0 0 16px 4px;font-size:1.4em;font-weight:500;color:var(--primary-text-color)}
        table{width:100%;border-collapse:collapse;font-size:15px}
        th{text-align:left;padding:8px 6px;border-bottom:2px solid var(--divider-color,#333);color:var(--secondary-text-color);font-weight:500;font-size:13px;white-space:nowrap}
        td{padding:8px 6px;border-bottom:1px solid var(--divider-color,#333);vertical-align:middle}
        .addr{text-align:center;font-weight:bold;width:40px;font-size:15px}
        .mname{min-width:120px}.mname input{width:100%;min-width:100px}
        .dname{min-width:150px}.dname input{width:100%;min-width:130px}
        .add-hint{color:var(--secondary-text-color);font-size:13px;font-style:italic}
        .add-row td{background:var(--primary-color,#03a9f4)11}
        input[type="text"],input[type="number"]{
          padding:6px 8px;border:1px solid var(--divider-color,#444);border-radius:4px;
          background:var(--input-fill-color,var(--card-background-color,#1c1c1c));
          color:var(--primary-text-color);font-size:14px;box-sizing:border-box;
        }
        input:focus{outline:none;border-color:var(--primary-color,#03a9f4);box-shadow:0 0 0 1px var(--primary-color,#03a9f4)}
        .action{width:70px;text-align:center;white-space:nowrap}
        button.del{background:none;border:1px solid var(--error-color,#db4437);color:var(--error-color,#db4437);border-radius:4px;cursor:pointer;padding:4px 8px;font-size:14px}
        button.del:hover{background:var(--error-color,#db4437);color:#fff}
        button.confirm-yes{background:var(--error-color,#db4437);color:#fff;border:none;border-radius:4px;cursor:pointer;padding:4px 8px;font-size:13px;margin-right:4px}
        button.confirm-no{background:none;border:1px solid var(--divider-color,#666);color:var(--primary-text-color);border-radius:4px;cursor:pointer;padding:4px 8px;font-size:13px}
        button.save-add{background:var(--success-color,#4caf50);color:#fff;border:none;border-radius:4px;cursor:pointer;padding:4px 10px;font-size:16px;margin-right:4px}
        button.cancel-add{background:none;border:1px solid var(--divider-color,#666);color:var(--primary-text-color);border-radius:4px;cursor:pointer;padding:4px 8px;font-size:14px}
        button.add{background:var(--primary-color,#03a9f4);color:#fff;border:none;border-radius:4px;cursor:pointer;padding:8px 16px;font-size:14px;margin-top:12px}
        button.add:hover{opacity:.85}
        .foot{margin-top:12px;font-size:13px;color:var(--secondary-text-color)}
      </style>
      <ha-card>
        <h2>UDK-04-10 Dimmer Module</h2>
        <table><thead><tr>
          <th>Adr</th><th>Modul</th><th>Dimmer 1</th><th>Dimmer 2</th><th>Dimmer 3</th><th>Dimmer 4</th><th></th>
        </tr></thead><tbody>${rows}${addRow}</tbody></table>
        ${this._showAdd ? '' : '<button class="add" id="btn-add">+ Modul hinzufügen</button>'}
        <div class="foot">${modules.length} Module · ${modules.length * 4} Dimmer · Änderungen werden sofort gespeichert<br>Umbenennen ändert nur den Anzeigenamen — Entity-IDs und Automationen bleiben unverändert.</div>
      </ha-card>`;

    this._bindEvents();
  }

  _bindEvents() {
    const self = this;

    // Text inputs
    this.shadowRoot.querySelectorAll('input[type="text"]').forEach(el => {
      if (el.id === 'new-name') return;
      el.addEventListener('change', e => {
        e.stopPropagation();
        self._save(parseInt(e.target.dataset.addr), e.target.dataset.key, e.target.value);
      });
      el.addEventListener('focus', () => { self._editing = true; });
      el.addEventListener('blur', () => { self._editing = false; });
    });

    // Delete buttons
    this.shadowRoot.querySelectorAll('button.del').forEach(el => {
      el.addEventListener('click', e => {
        self._removeModule(parseInt(e.target.dataset.addr), e.target.dataset.name);
      });
    });

    // Confirm delete
    this.shadowRoot.querySelectorAll('button.confirm-yes').forEach(el => {
      el.addEventListener('click', e => {
        self._doRemove(parseInt(e.target.dataset.addr));
      });
    });
    this.shadowRoot.querySelectorAll('button.confirm-no').forEach(el => {
      el.addEventListener('click', () => {
        self._confirmDelete = null;
        self._render();
      });
    });

    // Add button
    const addBtn = this.shadowRoot.getElementById('btn-add');
    if (addBtn) addBtn.addEventListener('click', () => { self._showAdd = true; self._render(); });

    // Save new module
    const saveAdd = this.shadowRoot.querySelector('button.save-add');
    if (saveAdd) saveAdd.addEventListener('click', () => {
      const addrEl = self.shadowRoot.getElementById('new-addr');
      const nameEl = self.shadowRoot.getElementById('new-name');
      const addr = parseInt(addrEl.value);
      const name = nameEl.value.trim();
      if (isNaN(addr) || addr < 1 || addr > 247) return;
      self._addModule(addr, name || `M${String(addr).padStart(2,'0')}`);
    });

    // Cancel add
    const cancelAdd = self.shadowRoot.querySelector('button.cancel-add');
    if (cancelAdd) cancelAdd.addEventListener('click', () => { self._showAdd = false; self._render(); });

    // Focus tracking for new module inputs
    ['new-addr', 'new-name'].forEach(id => {
      const el = self.shadowRoot.getElementById(id);
      if (el) {
        el.addEventListener('focus', () => { self._editing = true; });
        el.addEventListener('blur', () => { self._editing = false; });
      }
    });
  }

  _esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
  getCardSize(){return 10}
  static getStubConfig(){return{}}
}

customElements.define('udk-dimmer-card', UdkDimmerCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'udk-dimmer-card',name:'UDK Dimmer Card',description:'Configure UDK-04-10 dimmer modules'});
