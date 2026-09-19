function send(state) {

    console.log("Sending:", state);

    fetch("http://127.0.0.1:5000/" + state, {
        method: "POST"
    })
    .then(response => {

        console.log("Status:", response.status);

    })
    .catch(err => {

        console.error("Fetch failed:", err);

    });

}

function hookVideo() {

    const video = document.querySelector("video");

    if (!video) {
        setTimeout(hookVideo, 1000);
        return;
    }

    console.log("StudyFlow Connected");

    let pauseTimer = null;

    video.addEventListener("pause", () => {

        console.log("Video paused");

        pauseTimer = setTimeout(() => {
            send("pause");
        }, 300);

    });

    video.addEventListener("play", () => {

        console.log("Video playing");

        if (pauseTimer) {
            clearTimeout(pauseTimer);
            pauseTimer = null;
        }

        send("play");

    });

}

hookVideo();