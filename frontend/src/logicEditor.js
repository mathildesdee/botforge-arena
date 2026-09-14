// Rule/variable/behaviour editor for the Robot Builder, matching
// docs/ARCHITECTURE.md #6 and backend/app/interpreter.py. Deliberately
// still not the complete language in one go (the project brief warns
// against that): supports the PDF's progression stages 2 (AND/OR,
// flat — not full nested trees), 4 (ELSE), 5 (variables), 6 (memory
// fields), and 9 (behaviours as named, reusable action lists). NOT
// and ad-hoc unnamed action sequences are deferred — a behaviour
// already covers "do several things," just with a name attached.

export const LEFT_FIELDS = [
  { value: 'self.health_pct', label: 'My health %', kind: 'number' },
  { value: 'self.energy_pct', label: 'My energy %', kind: 'number' },
  { value: 'self.previous_health_pct', label: 'My health, last tick %', kind: 'number' },
  { value: 'self.seconds_since_enemy_seen', label: 'Seconds since enemy seen', kind: 'number' },
  { value: 'self.shots_fired', label: 'Shots fired', kind: 'number' },
  { value: 'self.shots_hit', label: 'Shots hit', kind: 'number' },
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

export const JOIN_OPS = [
  { value: 'and', label: 'AND' },
  { value: 'or', label: 'OR' },
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

const MAX_CONDITIONS_PER_RULE = 2;
const MAX_ACTIONS_PER_BEHAVIOUR = 5;

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

function isCompoundCondition(condition) {
  return condition.op === 'and' || condition.op === 'or';
}

function simpleConditionToState(condition) {
  let right = condition.right;
  let rightKind = 'number';
  if (typeof right === 'string' && right.startsWith('vars.')) {
    rightKind = 'variable';
    right = right.slice('vars.'.length);
  } else if (typeof right === 'boolean') {
    rightKind = 'boolean';
  }
  return { left: condition.left, op: condition.op, right, rightKind };
}

function simpleConditionToJson(c) {
  return { op: c.op, left: c.left, right: c.rightKind === 'variable' ? `vars.${c.right}` : c.right };
}

function defaultSimpleCondition() {
  return { left: LEFT_FIELDS[0].value, op: 'lt', right: 50, rightKind: 'number' };
}

function conditionToRuleState(ifCondition) {
  if (isCompoundCondition(ifCondition)) {
    return {
      conditions: [simpleConditionToState(ifCondition.left), simpleConditionToState(ifCondition.right)],
      joiner: ifCondition.op,
    };
  }
  return { conditions: [simpleConditionToState(ifCondition)], joiner: null };
}

function ruleStateToConditionJson(rule) {
  if (rule.conditions.length === 1) return simpleConditionToJson(rule.conditions[0]);
  return {
    op: rule.joiner,
    left: simpleConditionToJson(rule.conditions[0]),
    right: simpleConditionToJson(rule.conditions[1]),
  };
}

export function createRobotProgramEditor({ rulesEl, variablesEl, behavioursEl, previewEl }) {
  let rules = [];
  let variables = []; // [{ name, value }]
  let behaviours = []; // [{ name, actions: [actionName, ...] }]

  function variableNames() {
    return variables.map((v) => v.name).filter(Boolean);
  }

  function actionOptions() {
    return [...RULE_ACTIONS, ...behaviours.filter((b) => b.name).map((b) => ({ value: b.name, label: `⚙ ${b.name}` }))];
  }

  function updatePreview() {
    previewEl.textContent = JSON.stringify(getProgram(), null, 2);
  }

  // ---------- conditions ----------

  function renderConditionRow(condition, onLeftChanged) {
    const row = document.createElement('div');
    row.className = 'rule-condition';

    const leftSelect = document.createElement('select');
    leftSelect.innerHTML = optionsHtml(LEFT_FIELDS, condition.left);
    leftSelect.addEventListener('change', () => {
      condition.left = leftSelect.value;
      if (fieldKind(condition.left) === 'boolean') {
        condition.right = true;
        condition.rightKind = 'boolean';
      } else if (condition.rightKind === 'boolean') {
        condition.right = 50;
        condition.rightKind = 'number';
      }
      onLeftChanged();
    });

    const opSelect = document.createElement('select');
    opSelect.innerHTML = optionsHtml(CONDITION_OPS, condition.op);
    opSelect.addEventListener('change', () => {
      condition.op = opSelect.value;
    });

    row.append(leftSelect, opSelect);

    const kind = fieldKind(condition.left);
    if (kind === 'boolean') {
      const boolSelect = document.createElement('select');
      boolSelect.innerHTML = optionsHtml(
        [
          { value: 'true', label: 'true' },
          { value: 'false', label: 'false' },
        ],
        String(condition.right)
      );
      boolSelect.addEventListener('change', () => {
        condition.right = boolSelect.value === 'true';
      });
      row.append(boolSelect);
    } else if (condition.rightKind === 'variable' && variableNames().length > 0) {
      const varSelect = document.createElement('select');
      varSelect.innerHTML = optionsHtml(
        variableNames().map((name) => ({ value: name, label: name })),
        condition.right
      );
      varSelect.addEventListener('change', () => {
        condition.right = varSelect.value;
      });
      row.append(varSelect);
    } else {
      const numberInput = document.createElement('input');
      numberInput.type = 'number';
      numberInput.className = 'rule-number';
      numberInput.value = condition.right;
      numberInput.addEventListener('input', () => {
        condition.right = Number(numberInput.value);
      });
      row.append(numberInput);
    }

    if (kind !== 'boolean' && variableNames().length > 0) {
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'rule-var-toggle';
      toggle.textContent = condition.rightKind === 'variable' ? '#' : 'var';
      toggle.title = condition.rightKind === 'variable' ? 'Use a number instead' : 'Compare against a variable instead';
      toggle.addEventListener('click', () => {
        if (condition.rightKind === 'variable') {
          condition.rightKind = 'number';
          condition.right = 50;
        } else {
          condition.rightKind = 'variable';
          condition.right = variableNames()[0];
        }
        onLeftChanged();
      });
      row.append(toggle);
    }

    return row;
  }

  // ---------- rules ----------

  function renderRules() {
    rulesEl.innerHTML = '';

    if (rules.length === 0) {
      rulesEl.innerHTML = '<p class="empty-note">No rules yet — add one below.</p>';
    }

    rules.forEach((rule, index) => {
      const row = document.createElement('div');
      row.className = 'rule-row';

      const header = document.createElement('div');
      header.className = 'rule-header';

      const priorityEl = document.createElement('span');
      priorityEl.className = 'rule-priority';
      priorityEl.textContent = `#${index + 1}`;

      const upBtn = document.createElement('button');
      upBtn.type = 'button';
      upBtn.textContent = '↑';
      upBtn.disabled = index === 0;
      upBtn.addEventListener('click', () => {
        [rules[index - 1], rules[index]] = [rules[index], rules[index - 1]];
        renderRules();
      });

      const downBtn = document.createElement('button');
      downBtn.type = 'button';
      downBtn.textContent = '↓';
      downBtn.disabled = index === rules.length - 1;
      downBtn.addEventListener('click', () => {
        [rules[index + 1], rules[index]] = [rules[index], rules[index + 1]];
        renderRules();
      });

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.textContent = 'Remove';
      removeBtn.disabled = rules.length === 1; // backend rejects empty logic outright
      removeBtn.addEventListener('click', () => {
        rules.splice(index, 1);
        renderRules();
      });

      header.append(priorityEl, upBtn, downBtn, removeBtn);
      row.appendChild(header);

      const ifWord = document.createElement('span');
      ifWord.className = 'rule-word';
      ifWord.textContent = 'IF';
      row.appendChild(ifWord);
      row.appendChild(renderConditionRow(rule.conditions[0], renderRules));

      if (rule.conditions.length === MAX_CONDITIONS_PER_RULE) {
        const joinerSelect = document.createElement('select');
        joinerSelect.innerHTML = optionsHtml(JOIN_OPS, rule.joiner);
        joinerSelect.addEventListener('change', () => {
          rule.joiner = joinerSelect.value;
          updatePreview();
        });
        row.appendChild(joinerSelect);
        row.appendChild(renderConditionRow(rule.conditions[1], renderRules));

        const removeCondBtn = document.createElement('button');
        removeCondBtn.type = 'button';
        removeCondBtn.textContent = '−cond';
        removeCondBtn.title = 'Remove second condition';
        removeCondBtn.addEventListener('click', () => {
          rule.conditions.pop();
          rule.joiner = null;
          renderRules();
        });
        row.appendChild(removeCondBtn);
      } else {
        const addCondBtn = document.createElement('button');
        addCondBtn.type = 'button';
        addCondBtn.textContent = '+ AND/OR';
        addCondBtn.title = 'Add a second condition';
        addCondBtn.addEventListener('click', () => {
          rule.conditions.push(defaultSimpleCondition());
          rule.joiner = 'and';
          renderRules();
        });
        row.appendChild(addCondBtn);
      }

      const thenWord = document.createElement('span');
      thenWord.className = 'rule-word';
      thenWord.textContent = 'THEN';
      row.appendChild(thenWord);

      const actionSelect = document.createElement('select');
      actionSelect.innerHTML = optionsHtml(actionOptions(), rule.action);
      actionSelect.addEventListener('change', () => {
        rule.action = actionSelect.value;
        updatePreview();
      });
      row.appendChild(actionSelect);

      const elseLabel = document.createElement('label');
      elseLabel.className = 'rule-else-toggle';
      const elseCheckbox = document.createElement('input');
      elseCheckbox.type = 'checkbox';
      elseCheckbox.checked = rule.hasElse;
      elseCheckbox.addEventListener('change', () => {
        rule.hasElse = elseCheckbox.checked;
        if (rule.hasElse && !rule.elseAction) rule.elseAction = RULE_ACTIONS[0].value;
        renderRules();
      });
      elseLabel.append(elseCheckbox, ' ELSE');
      row.appendChild(elseLabel);

      if (rule.hasElse) {
        const elseSelect = document.createElement('select');
        elseSelect.innerHTML = optionsHtml(actionOptions(), rule.elseAction);
        elseSelect.addEventListener('change', () => {
          rule.elseAction = elseSelect.value;
          updatePreview();
        });
        row.appendChild(elseSelect);
      }

      rulesEl.appendChild(row);
    });

    updatePreview();
  }

  function addRule() {
    rules.push({ conditions: [defaultSimpleCondition()], joiner: null, action: RULE_ACTIONS[0].value, hasElse: false, elseAction: null });
    renderRules();
  }

  // ---------- variables ----------

  function renderVariables() {
    variablesEl.innerHTML = '';
    if (variables.length === 0) {
      variablesEl.innerHTML = '<p class="empty-note">No variables yet.</p>';
    }

    variables.forEach((variable, index) => {
      const row = document.createElement('div');
      row.className = 'kv-row';

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.placeholder = 'name (e.g. preferred_distance)';
      nameInput.value = variable.name;
      nameInput.addEventListener('input', () => {
        variable.name = nameInput.value.trim();
        renderRules(); // variable name now usable/unusable in conditions
      });

      const valueInput = document.createElement('input');
      valueInput.type = 'number';
      valueInput.value = variable.value;
      valueInput.addEventListener('input', () => {
        variable.value = Number(valueInput.value);
        updatePreview();
      });

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.textContent = 'Remove';
      removeBtn.addEventListener('click', () => {
        variables.splice(index, 1);
        renderVariables();
        renderRules();
      });

      row.append(nameInput, valueInput, removeBtn);
      variablesEl.appendChild(row);
    });

    updatePreview();
  }

  function addVariable() {
    variables.push({ name: `var${variables.length + 1}`, value: 0 });
    renderVariables();
    renderRules();
  }

  // ---------- behaviours ----------

  function renderBehaviours() {
    behavioursEl.innerHTML = '';
    if (behaviours.length === 0) {
      behavioursEl.innerHTML = '<p class="empty-note">No behaviours yet.</p>';
    }

    behaviours.forEach((behaviour, bIndex) => {
      const row = document.createElement('div');
      row.className = 'behaviour-row';

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.placeholder = 'name (e.g. retreat)';
      nameInput.value = behaviour.name;
      nameInput.addEventListener('input', () => {
        behaviour.name = nameInput.value.trim();
        renderRules(); // behaviour name now usable/unusable as an action
      });

      const stepsEl = document.createElement('div');
      stepsEl.className = 'behaviour-steps';

      behaviour.actions.forEach((actionName, aIndex) => {
        const stepSelect = document.createElement('select');
        stepSelect.innerHTML = optionsHtml(RULE_ACTIONS, actionName);
        stepSelect.addEventListener('change', () => {
          behaviour.actions[aIndex] = stepSelect.value;
          updatePreview();
        });

        const removeStepBtn = document.createElement('button');
        removeStepBtn.type = 'button';
        removeStepBtn.textContent = '×';
        removeStepBtn.disabled = behaviour.actions.length === 1;
        removeStepBtn.addEventListener('click', () => {
          behaviour.actions.splice(aIndex, 1);
          renderBehaviours();
        });

        const stepWrap = document.createElement('span');
        stepWrap.className = 'behaviour-step';
        stepWrap.append(stepSelect, removeStepBtn);
        stepsEl.appendChild(stepWrap);
      });

      const addStepBtn = document.createElement('button');
      addStepBtn.type = 'button';
      addStepBtn.textContent = '+ step';
      addStepBtn.disabled = behaviour.actions.length >= MAX_ACTIONS_PER_BEHAVIOUR;
      addStepBtn.addEventListener('click', () => {
        behaviour.actions.push(RULE_ACTIONS[0].value);
        renderBehaviours();
      });

      const removeBehaviourBtn = document.createElement('button');
      removeBehaviourBtn.type = 'button';
      removeBehaviourBtn.textContent = 'Remove behaviour';
      removeBehaviourBtn.addEventListener('click', () => {
        behaviours.splice(bIndex, 1);
        renderBehaviours();
        renderRules();
      });

      row.append(nameInput, stepsEl, addStepBtn, removeBehaviourBtn);
      behavioursEl.appendChild(row);
    });

    updatePreview();
  }

  function addBehaviour() {
    behaviours.push({ name: `behaviour${behaviours.length + 1}`, actions: [RULE_ACTIONS[0].value] });
    renderBehaviours();
    renderRules();
  }

  // ---------- program (de)serialization ----------

  function getProgram() {
    const logic = rules.map((rule, index) => {
      const entry = { priority: index + 1, if: ruleStateToConditionJson(rule), then: rule.action };
      if (rule.hasElse && rule.elseAction) entry.else = rule.elseAction;
      return entry;
    });

    const variablesObj = {};
    variables.forEach((v) => {
      if (v.name) variablesObj[v.name] = v.value;
    });

    const behavioursObj = {};
    behaviours.forEach((b) => {
      if (b.name) behavioursObj[b.name] = [...b.actions];
    });

    return { logic, variables: variablesObj, behaviours: behavioursObj };
  }

  function setProgram({ logic, variables: variablesObj, behaviours: behavioursObj }) {
    rules = (logic && logic.length > 0 ? logic : DEFAULT_STARTER_LOGIC).map((entry) => {
      const ruleState = conditionToRuleState(entry.if);
      return { ...ruleState, action: entry.then, hasElse: Boolean(entry.else), elseAction: entry.else || null };
    });
    variables = Object.entries(variablesObj || {}).map(([name, value]) => ({ name, value }));
    behaviours = Object.entries(behavioursObj || {}).map(([name, actions]) => ({ name, actions: [...actions] }));
    renderVariables();
    renderBehaviours();
    renderRules();
  }

  setProgram({ logic: DEFAULT_STARTER_LOGIC, variables: {}, behaviours: {} });

  return { addRule, addVariable, addBehaviour, getProgram, setProgram };
}
