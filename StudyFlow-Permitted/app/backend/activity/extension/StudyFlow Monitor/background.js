const ACTIVITY_ENDPOINT = "http://127.0.0.1:8765/v1/browser-activity";
const ALARM_NAME = "studyflow-monitor-poll";

function postJson(endpoint, payload) {
  fetch(endpoint, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  }).catch(() => {});
}

async function collectSnapshot() {
  try {
    const activeTabs = await chrome.tabs.query({
      active: true,
      lastFocusedWindow: true
    });
    const active = activeTabs[0];
    if (!active) return;

    const audibleTabs = await chrome.tabs.query({audible: true});

    postJson(ACTIVITY_ENDPOINT, {
      source: "chrome-extension",
      timestamp: new Date().toISOString(),
      active_tab: {
        tab_id: active.id ?? -1,
        window_id: active.windowId ?? -1,
        url: active.url || "",
        title: active.title || "",
        audible: Boolean(active.audible),
        discarded: Boolean(active.discarded),
        status: active.status || ""
      },
      audible_tabs: audibleTabs.map((tab) => ({
        tab_id: tab.id ?? -1,
        window_id: tab.windowId ?? -1,
        url: tab.url || "",
        title: tab.title || "",
        audible: Boolean(tab.audible),
        discarded: Boolean(tab.discarded)
      }))
    });
  } catch (_) {
    // The monitor must remain silent if Chrome temporarily rejects a query.
  }
}

if (chrome.runtime?.onInstalled?.addListener) {
  chrome.runtime.onInstalled.addListener(() => {
    chrome.alarms?.create(ALARM_NAME, {periodInMinutes: 0.1});
    collectSnapshot();
  });
}

if (chrome.alarms?.onAlarm?.addListener) {
  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === ALARM_NAME) collectSnapshot();
  });
}

if (chrome.tabs?.onActivated?.addListener) {
  chrome.tabs.onActivated.addListener(collectSnapshot);
}

if (chrome.tabs?.onUpdated?.addListener) {
  chrome.tabs.onUpdated.addListener((_tabId, changeInfo) => {
    if (
      changeInfo.status ||
      changeInfo.audible !== undefined ||
      changeInfo.title ||
      changeInfo.url
    ) {
      collectSnapshot();
    }
  });
}

chrome.alarms?.create(ALARM_NAME, {periodInMinutes: 0.1});
collectSnapshot();
