const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

test('la interfaz muestra un fotograma anotado y guarda el resumen al detener', async () => {
  const layout = readFileSync(resolve(__dirname, '../../templates/processor/layout.html'), 'utf8');
  const script = layout.match(/<script>([\s\S]*?)<\/script>/)[1];
  const controls = new Map();
  const requests = [];
  const track = { readyState: 'live', stop() { this.readyState = 'ended'; }, addEventListener() {} };
  const stream = { getTracks: () => [track], getVideoTracks: () => [track] };
  const rawFrame = 'data:image/jpeg;base64,entrada';
  const outputFrame = 'data:image/jpeg;base64,anotado';
  let releaseDetection;
  const pendingDetection = new Promise(resolve => { releaseDetection = resolve; });

  function control(id) {
    if (!controls.has(id)) {
      controls.set(id, {
        dataset: {},
        addEventListener(event, listener) { this[event] = listener; }
      });
    }
    return controls.get(id);
  }

  Object.assign(control('camera'), { readyState: 2, play: async () => {} });
  Object.assign(control('frameCanvas'), {
    getContext: () => ({ drawImage() {} }),
    toDataURL: () => rawFrame
  });
  runInNewContext(script, {
    AbortSignal,
    crypto: { randomUUID: () => 'session-id' },
    navigator: { mediaDevices: { getUserMedia: async () => stream } },
    window: { setInterval: () => 1, clearInterval() {}, addEventListener() {} },
    document: {
      getElementById: control,
      querySelector: () => ({ value: 'csrf' }),
      body: { dataset: { startUrl: '/start', detectUrl: '/detect', finishUrl: '/finish' } }
    },
    async fetch(url, options) {
      requests.push({ url, data: JSON.parse(options.body) });
      if (url === '/detect') await pendingDetection;
      const bodies = {
        '/start': { session_id: 'session-id' },
        '/detect': { image: outputFrame, counts: { Celular: 1 } },
        '/finish': { saved: true }
      };
      return { ok: true, json: async () => bodies[url] };
    }
  });

  await control('startButton').click();
  assert.equal(control('liveBadge').hidden, false);
  assert.deepEqual(requests[1], { url: '/detect', data: { frame: rawFrame } });
  releaseDetection();
  await new Promise(setImmediate);
  assert.equal(control('processedFrame').src, outputFrame);
  assert.equal(control('processedFrame').hidden, false);
  assert.equal(control('currentTotal').textContent, 1);
  assert.match(control('detectionList').innerHTML, /Celular/);

  await control('stopButton').click();
  assert.equal(track.readyState, 'ended');
  assert.equal(control('liveBadge').hidden, true);
  assert.deepEqual(requests.at(-1), {
    url: '/finish',
    data: {
      session_id: 'session-id',
      frames_processed: 1,
      class_counts: { Celular: 1 },
      start_pending: false
    }
  });
  assert.match(control('statusLine').textContent, /resumen guardado/);
});
