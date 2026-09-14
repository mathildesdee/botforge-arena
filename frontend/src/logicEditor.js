// A Stage 1 rule editor (see the PDF's "Programming progression"):
// priority-ordered `IF condition THEN action` rules, one condition
// per rule — no AND/OR/NOT or variables yet, those are later stages.
// Every field/op/action here is copied exactly from the real
// interpreter's vocabulary (backend/app/interpreter.py), verified by
// reading it directly rather than guessing from the docs.

export const LEFT_FIELDS = [
  { value: 'self.health_pct', label: 'My health %', kind: 'number' },
  { value: 'self.energy_pct', label: 'My energy %', kind: 'number' },
  { value: 'self.direction', label: 'My direction (°)', kind: 'number' },
  { value: 'enemy.distance', label: 'Enemy distance', kind: 'number' },
  { value: 'enemy.health_pct', label: 'Enemy health %', kind: 'number' },
  { value: 'enemy.direction', label: 'Enemy direction (°)', kind: 'number' },
  { value: 'enemy.visible', label: 'Enemy visible', kind: 'boolean' },
];

export const CONDITION_OPS = [
  { value: 'lt', label: '<' },
  { value: 'gt', label: '>' },
  { value: 'eq', label: '=' },
  { value: 'neq', label: '≠' },
];

export const RULE_ACTIONS = [
  { value: 'move_forward', label: 'Move forward' },
  { value: 'move_backward', label: 'Move backward' },
  { value: 'turn_left', label: 'Turn left' },
  { value: 'turn_right', label: 'Turn right' },
  { value: 'turn_toward_enemy', label: 'Turn toward enemy' },
  { value: 'move_toward_enemy', label: 'Move toward enemy' },
  { value: 'move_away_from_enemy', label: 'Move away from enemy' },
  { value: 'shoot', label: 'Shoot' },
  { value: 'select_nearest_enemy', label: 'Target nearest enemy' },
  { value: 'select_weakest_enemy', label: 'Target weakest enemy' },
  { value: 'wait', label: 'Wait' },
  { value: 'scan', label: 'Scan' },
];

export const DEFAULT_STARTER_LOGIC = [
  { priority: 1, if: { op: 'lt', left: 'enemy.distance', right: 250 }, then: 'shoot' },
  { priority: 2, if: { op: 'lt', left: 'enemy.distance', right: 999999 }, then: 'move_toward_enemy' },
];

function fieldKind(leftValue) {
  return LEFT_FIELDS.find((f) => f.value === leftValue)?.kind ?? 'number';
}

function optionsHtml(options, selected) {
  return options
    .map((o) => `<option value="${o.value}"${o.value === selected ? ' selected' : ''}>${o.label}</option>`)
    .join('');
}

export function createLogicEditor(rulesEl, previewEl) {
  let rules = [];

  function toRuleState(logicEntry) {
    return {
      op: logicEntry.if.op,
      left: logicEntry.if.left,
      right: logicEntry.if.right,
      action: logicEntry.then,
    };
  }

  function defaultRuleState() {
    return { op: 'lt', left: LEFT_FIELDS[0].value, right: 50, action: RULE_ACTIONS[0].value };
  }

  function render() {
    rulesEl.innerHTML = '';

    if (rules.length === 0) {
      rulesEl.innerHTML = '<p class="empty-note">No rules yet — add one below.</p>';
    }

    rules.forEach((rule, index) => {
      const row = document.createElement('div');
      row.className = 'rule-row';

      const priorityEl = document.createElement('span');
      priorityEl.className = 'rule-priority';
      priorityEl.textContent = `#${index + 1}`;

      const ifLabel = document.createElement('span');
      ifLabel.className = 'rule-word';
      ifLabel.textContent = 'IF';

      const leftSelect = document.createElement('select');
      leftSelect.innerHTML = optionsHtml(LEFT_FIELDS, rule.left);
      leftSelect.addEventListener('change', () => {
        rule.left = leftSelect.value;
        if (fieldKind(rule.left) === 'boolean') {
          rule.right = true;
        } else if (typeof rule.right !== 'number') {
          rule.right = 50;
        }
        render();
      });

      const opSelect = document.createElement('select');
      opSelect.innerHTML = optionsHtml(CONDITION_OPS, rule.op);
      opSelect.addEventListener('change', () => {
        rule.op = opSelect.value;
      });

      let rightInput;
      if (fieldKind(rule.left) === 'boolean') {
        rightInput = document.createElement('select');
        rightInput.innerHTML = optionsHtml(
          [
            { value: 'true', label: 'true' },
            { value: 'false', label: 'false' },
          ],
          String(rule.right)
        );
        rightInput.addEventListener('change', () => {
          rule.right = rightInput.value === 'true';
        });
      } else {
        rightInput = document.createElement('input');
        rightInput.type = 'number';
        rightInput.value = rule.right;
        rightInput.className = 'rule-number';
        rightInput.addEventListener('input', () => {
          rule.right = Number(rightInput.value);
        });
      }

      const thenLabel = document.createElement('span');
      thenLabel.className = 'rule-word';
      thenLabel.textContent = 'THEN';

      const actionSelect = document.createElement('select');
      actionSelect.innerHTML = optionsHtml(RULE_ACTIONS, rule.action);
      actionSelect.addEventListener('change', () => {
        rule.action = actionSelect.value;
      });

      const controls = document.createElement('div');
      controls.className = 'rule-controls';

      const upBtn = document.createElement('button');
      upBtn.type = 'button';
      upBtn.textContent = '↑';
      upBtn.disabled = index === 0;
      upBtn.addEventListener('click', () => {
        [rules[index - 1], rules[index]] = [rules[index], rules[index - 1]];
        render();
      });

      const downBtn = document.createElement('button');
      downBtn.type = 'button';
      downBtn.textContent = '↓';
      downBtn.disabled = index === rules.length - 1;
      downBtn.addEventListener('click', () => {
        [rules[index + 1], rules[index]] = [rules[index], rules[index + 1]];
        render();
      });

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.textContent = 'Remove';
      // The backend rejects a robot with an empty logic list outright —
      // a robot with zero rules can't do anything, so don't let the
      // editor reach that state.
      removeBtn.disabled = rules.length === 1;
      removeBtn.addEventListener('click', () => {
        rules.splice(index, 1);
        render();
      });

      controls.append(upBtn, downBtn, removeBtn);
      row.append(priorityEl, ifLabel, leftSelect, opSelect, rightInput, thenLabel, actionSelect, controls);
      rulesEl.appendChild(row);
    });

    previewEl.textContent = JSON.stringify(getLogic(), null, 2);
  }

  function addRule() {
    rules.push(defaultRuleState());
    render();
  }

  function getLogic() {
    return rules.map((rule, index) => ({
      priority: index + 1,
      if: { op: rule.op, left: rule.left, right: rule.right },
      then: rule.action,
    }));
  }

  function setLogic(logicEntries) {
    rules = (logicEntries && logicEntries.length > 0 ? logicEntries : DEFAULT_STARTER_LOGIC).map(toRuleState);
    render();
  }

  setLogic(DEFAULT_STARTER_LOGIC);

  return { addRule, getLogic, setLogic };
}
