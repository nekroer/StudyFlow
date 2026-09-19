const ENDPOINT = "http://127.0.0.1:8765/v1/browser-activity";
const ALARM_NAME = "studyflow-monitor-poll";

function sendSnapshot(snapshot) {
  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(snapshot)
  }).catch(() => {});
}

async function collectSnapshot() {
  const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  const active = tabs[0];
  if (!active) return;

  sendSnapshot({
    source: "chrome-extension",
    timestamp: new Date().toISOString(),
    tab_id: active.id ?? -1,
    window_id: active.windowId ?? -1,
    url: active.url || "",
    title: active.title || "",
    audible: Boolean(active.audible),
    discarded: Boolean(active.discarded),
    status: active.status || ""
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 0.1 });
  collectSnapshot();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) collectSnapshot();
});

chrome.tabs.onActivated.addListener(collectSnapshot);
chrome.tabs.onUpdated.addListener((_tabId, changeInfo) => {
  if (changeInfo.status || changeInfo.audible !== undefined || changeInfo.title) {
    collectSnapshot();
  }
});
