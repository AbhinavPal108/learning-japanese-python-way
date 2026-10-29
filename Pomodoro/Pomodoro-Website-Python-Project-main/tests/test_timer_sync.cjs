// Lightweight timer sync DOM contract test, without a browser or external dependencies.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const handlers = {};
const buttons = Object.fromEntries(['startButton', 'resetButton', 'sessionTask', 'settingsForm'].map(id => [id, {
    id,
    disabled: false,
    value: '',
    addEventListener: (type, cb) => { handlers[id + ':' + type] = cb; }
}]));
let state = {
    mode: 'focus',
    running: false,
    round: 1,
    remaining_seconds: 1500,
    revision: 0,
    completed: 0,
    settings: {focus: 25, shortBreak: 5, longBreak: 15, autoStartBreaks: false, autoStartFocus: false},
    task_id: null
};
const actions = [];
let displayCount = 0;
const sandbox = {
    currentMode: 'focus',
    running: false,
    round: 1,
    remainingSeconds: 1500,
    deadline: null,
    selectedTaskId: null,
    settings: {...state.settings},
    DEFAULT_SETTINGS: {...state.settings},
    performance: {now: () => 0},
    Date,
    document: {
        getElementById: id => buttons[id] || null,
        addEventListener: (type, cb) => { handlers['document:' + type] = cb; },
        hidden: false
    },
    window: {addEventListener: (type, cb) => { handlers['window:' + type] = cb; }},
    setInterval: () => 1,
    setTimeout: () => 1,
    clearTimeout: () => {},
    AbortController,
    console,
    fetch: async (url, options) => {
        assert.equal(url, '/api/timer');
        if (options.method === 'POST') {
            const command = JSON.parse(options.body);
            assert.equal(command.revision, state.revision);
            actions.push(command);
            state = {...state, revision: state.revision + 1};
            if (command.action === 'start') state.running = true;
            if (command.action === 'pause') state.running = false;
            if (command.action === 'mode') {
                state.mode = command.mode;
                state.remaining_seconds = state.settings[command.mode] * 60;
                state.running = false;
            }
        }
        return {ok: true, json: async () => ({...state})};
    },
    stopInterval: () => {},
    updateDisplay: () => { displayCount++; },
    updateStatus: () => {},
    refreshData: () => Promise.resolve(),
    showToast: message => { throw new Error(message); }
};

vm.createContext(sandbox);
vm.runInContext(
    fs.readFileSync(path.join(__dirname, '..', 'timer-sync.js'), 'utf8'),
    sandbox
);
const tick = () => new Promise(resolve => setImmediate(resolve));

(async () => {
    await tick();
    assert.ok(displayCount > 0, 'initial timer read renders');
    async function click(button) {
        let blocked = false;
        handlers['document:click']({
            target: {closest: () => button},
            preventDefault() {},
            stopImmediatePropagation() { blocked = true; }
        });
        await tick();
        await tick();
        assert.ok(blocked, 'sync script intercepts timer control');
    }

    await click(buttons.startButton);
    assert.equal(actions[0].action, 'start');
    assert.equal(sandbox.running, true);
    await click(buttons.startButton);
    assert.equal(actions[1].action, 'pause');
    assert.equal(sandbox.running, false);
    await click({
        dataset: {mode: 'longBreak'},
        matches: selector => selector === '.mode[data-mode]'
    });
    assert.equal(actions[2].action, 'mode');
    assert.equal(sandbox.currentMode, 'longBreak');
    console.log('Pomodoro timer sync JS contract passed');
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
