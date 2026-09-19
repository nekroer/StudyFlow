function sendPlaybackState(state) {
  fetch("http://127.0.0.1:5000/" + state, {
    method: "POST"
  }).catch(() => {});
}

function hookVideo() {
  const video = document.querySelector("video");

  if (!video) {
    setTimeout(hookVideo, 1000);
    return;
  }

  let pauseTimer = null;

  video.addEventListener("pause", () => {
    pauseTimer = setTimeout(() => {
      sendPlaybackState("pause");
    }, 300);
  });

  video.addEventListener("play", () => {
    if (pauseTimer) {
      clearTimeout(pauseTimer);
      pauseTimer = null;
    }

    sendPlaybackState("play");
  });
}

hookVideo();
