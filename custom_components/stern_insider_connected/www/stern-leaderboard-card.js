/**
 * Stern Insider Connected Leaderboard Card
 * A custom Lovelace card for displaying pinball high scores
 */

class SternLeaderboardCard extends HTMLElement {
  static get properties() {
    return {
      hass: {},
      config: {},
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity (any high score sensor for the machine)");
    }
    this.config = config;
    this._machineId = null;
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  _getMachineData() {
    if (!this._hass || !this.config.entity) return null;

    const state = this._hass.states[this.config.entity];
    if (!state) return null;

    const machineId = state.attributes.machine_id;
    if (!machineId) return null;

    // Find all high score entities for this machine
    const scores = [];
    const entityPrefix = `sensor.${machineId}_high_score_`;

    for (const [entityId, entityState] of Object.entries(this._hass.states)) {
      if (entityState.attributes.machine_id === machineId &&
          entityState.attributes.rank !== undefined) {
        scores.push({
          rank: entityState.attributes.rank,
          score: parseInt(entityState.state) || 0,
          initials: entityState.attributes.player_initials || "???",
          playerName: entityState.attributes.player_name || "",
        });
      }
    }

    scores.sort((a, b) => a.rank - b.rank);

    return {
      name: state.attributes.machine_name || "Unknown",
      machineId: machineId,
      scores: scores,
    };
  }

  _formatScore(score) {
    return score.toLocaleString();
  }

  _getRankName(rank) {
    const names = {
      1: "Grand Champion",
      2: "High Score #1",
      3: "High Score #2",
      4: "High Score #3",
      5: "High Score #4",
    };
    return names[rank] || `#${rank}`;
  }

  render() {
    if (!this._hass) return;

    const machine = this._getMachineData();
    if (!machine) {
      this.innerHTML = `
        <ha-card>
          <div class="card-content">
            <p>Entity not found: ${this.config.entity}</p>
          </div>
        </ha-card>
      `;
      return;
    }

    const showLogo = this.config.show_logo !== false;
    const showRankNames = this.config.show_rank_names !== false;
    const compact = this.config.compact === true;

    this.innerHTML = `
      <ha-card>
        <style>
          .stern-card {
            padding: 16px;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.6);
          }
          .stern-header {
            display: flex;
            align-items: center;
            margin-bottom: 16px;
            gap: 12px;
          }
          .stern-logo {
            width: 64px;
            height: 64px;
            object-fit: contain;
          }
          .stern-title {
            font-size: 1.5em;
            font-weight: 500;
          }
          .stern-scores {
            display: flex;
            flex-direction: column;
            gap: ${compact ? '4px' : '8px'};
          }
          .stern-score-row {
            display: flex;
            align-items: center;
            padding: ${compact ? '4px 0' : '8px 0'};
            border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.1));
          }
          .stern-score-row:last-child {
            border-bottom: none;
          }
          .stern-rank {
            width: ${showRankNames ? '140px' : '30px'};
            font-weight: 500;
            color: var(--secondary-text-color);
            font-size: ${compact ? '0.9em' : '1em'};
          }
          .stern-initials {
            width: 50px;
            font-weight: bold;
            font-size: ${compact ? '1em' : '1.1em'};
          }
          .stern-score-value {
            flex: 1;
            text-align: right;
            font-family: monospace;
            font-size: ${compact ? '1em' : '1.2em'};
            font-weight: 500;
          }
          .stern-gc {
            color: var(--warning-color, #ffc107);
          }
          .stern-gc .stern-initials {
            color: var(--warning-color, #ffc107);
          }
        </style>
        <div class="stern-card">
          <div class="stern-header">
            ${showLogo ? `<img class="stern-logo" src="" alt="" id="stern-logo-img">` : ''}
            <div class="stern-title">${machine.name}</div>
          </div>
          <div class="stern-scores">
            ${machine.scores.map(score => `
              <div class="stern-score-row ${score.rank === 1 ? 'stern-gc' : ''}">
                <div class="stern-rank">${showRankNames ? this._getRankName(score.rank) : '#' + score.rank}</div>
                <div class="stern-initials">${score.initials.toUpperCase()}</div>
                <div class="stern-score-value">${this._formatScore(score.score)}</div>
              </div>
            `).join('')}
          </div>
        </div>
      </ha-card>
    `;

    // Set logo from entity attributes
    if (showLogo) {
      const state = this._hass.states[this.config.entity];
      const logoImg = this.querySelector('#stern-logo-img');
      if (logoImg && state) {
        const logoUrl = this.config.logo_url ||
                        state.attributes.square_logo_url ||
                        state.attributes.variable_width_logo_url;
        if (logoUrl) {
          logoImg.src = logoUrl;
        } else {
          logoImg.style.display = 'none';
        }
      }
    }

    // Apply gradient background if available
    const state = this._hass.states[this.config.entity];
    if (state && state.attributes.gradient_start && state.attributes.gradient_stop) {
      const card = this.querySelector('.stern-card');
      if (card && this.config.use_gradient !== false) {
        card.style.background = `linear-gradient(135deg, ${state.attributes.gradient_start}, ${state.attributes.gradient_stop})`;
      }
    }
  }

  getCardSize() {
    return 4;
  }

  static getConfigElement() {
    return document.createElement("stern-leaderboard-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      show_logo: true,
      show_rank_names: true,
      compact: false,
    };
  }
}

// Card Editor
class SternLeaderboardCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  render() {
    if (!this._hass || !this._config) return;

    this.innerHTML = `
      <div class="card-config">
        <ha-entity-picker
          .hass="${this._hass}"
          .value="${this._config.entity || ''}"
          .configValue="${'entity'}"
          label="Entity (any high score sensor)"
          allow-custom-entity
        ></ha-entity-picker>
        <ha-formfield label="Show Logo">
          <ha-switch
            .checked="${this._config.show_logo !== false}"
            .configValue="${'show_logo'}"
          ></ha-switch>
        </ha-formfield>
        <ha-formfield label="Show Rank Names">
          <ha-switch
            .checked="${this._config.show_rank_names !== false}"
            .configValue="${'show_rank_names'}"
          ></ha-switch>
        </ha-formfield>
        <ha-formfield label="Compact Mode">
          <ha-switch
            .checked="${this._config.compact === true}"
            .configValue="${'compact'}"
          ></ha-switch>
        </ha-formfield>
        <ha-textfield
          label="Logo URL (optional)"
          .value="${this._config.logo_url || ''}"
          .configValue="${'logo_url'}"
        ></ha-textfield>
      </div>
    `;

    this.querySelectorAll('ha-switch, ha-textfield, ha-entity-picker').forEach(element => {
      element.addEventListener('change', (e) => this._valueChanged(e));
      element.addEventListener('value-changed', (e) => this._valueChanged(e));
    });
  }

  _valueChanged(ev) {
    if (!this._config || !ev.target) return;

    const target = ev.target;
    const configValue = target.configValue;

    if (!configValue) return;

    let newValue;
    if (target.tagName === 'HA-SWITCH') {
      newValue = target.checked;
    } else {
      newValue = ev.detail?.value || target.value;
    }

    if (this._config[configValue] === newValue) return;

    const newConfig = { ...this._config, [configValue]: newValue };

    const event = new CustomEvent('config-changed', {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define("stern-leaderboard-card", SternLeaderboardCard);
customElements.define("stern-leaderboard-card-editor", SternLeaderboardCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "stern-leaderboard-card",
  name: "Stern Leaderboard Card",
  description: "Display pinball high scores from Stern Insider Connected",
  preview: true,
});

console.info(
  "%c STERN-LEADERBOARD-CARD %c loaded ",
  "color: white; background: #aa21ff; font-weight: 700;",
  "color: #aa21ff; background: white; font-weight: 700;"
);
