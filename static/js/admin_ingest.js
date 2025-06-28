document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".ajax-process-btn").forEach(btn => {
        btn.addEventListener("click", function () {
            const tarId = btn.dataset.tarId;

            btn.disabled = true;
            btn.innerText = "Processing...";
            fetch(`/gallery/async-ingest/${tarId}/`)
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    btn.innerText = "Done ✅";
                })
                .catch(error => {
                    alert("Error occurred: " + error);
                    btn.innerText = "Failed ❌";
                });
        });
    });
});

function startIngestion(tarId) {
    fetch(`/gallery/async-ingest/${tarId}/`)
        .then(() => updateStatus(tarId));
}

function stopIngestion(tarId) {
    fetch(`/gallery/stop-ingest/${tarId}/`)
        .then(() => updateStatus(tarId));
}

function updateStatus(tarId) {
    fetch(`/gallery/async-status/${tarId}/`)
        .then(response => response.json())
        .then(data => {
            const statusDiv = document.getElementById(`status-${tarId}`);
            if (statusDiv) {
                statusDiv.innerText = "Status: " + data.last_message;
            }
            if (data.is_processing) {
                setTimeout(() => updateStatus(tarId), 3000);
            }
        });
}
