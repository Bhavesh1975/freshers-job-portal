document.addEventListener("DOMContentLoaded", loadTopics);

let allData = [];
let selectedTopic = "";
let selectedSubtopic = "";

/* =========================
   LOAD TOPICS
========================= */
function loadTopics() {
    fetch("/get_topics")
        .then(res => res.json())
        .then(data => {
            allData = data;
            displayTopics(data);
        });
}

/* =========================
   SHOW TOPICS
========================= */
function displayTopics(data) {
    const container = document.getElementById("topicsContainer");
    container.innerHTML = "";

    data.forEach(topic => {
        const card = document.createElement("div");
        card.className = "topic-card";

        card.innerHTML = `<div class="topic-title">${topic.topic}</div>`;

        card.onclick = () => showSubtopics(topic.topic);

        container.appendChild(card);
    });
}

/* =========================
   SHOW SUBTOPICS
========================= */
function showSubtopics(topicName) {
    selectedTopic = topicName;

    const subSection = document.getElementById("subtopicsSection");
    const subContainer = document.getElementById("subtopicsContainer");
    const title = document.getElementById("selectedTopic");

    subSection.style.display = "block";
    title.innerText = topicName;

    subContainer.innerHTML = "";

    const topicData = allData.find(t => t.topic === topicName);

    topicData.subtopics.forEach(sub => {
        const card = document.createElement("div");
        card.className = "subtopic-card";

        // 🔥 FIX: use sub.name (not object)
        card.innerText = sub.name;

        // 🔥 pass full object
        card.onclick = () => showDifficulty(sub);

        subContainer.appendChild(card);
    });

    subSection.scrollIntoView({ behavior: "smooth" });
}

/* =========================
   SHOW DIFFICULTY
========================= */
function showDifficulty(subObj) {
    selectedSubtopic = subObj.name;

    const diffSection = document.getElementById("difficultySection");
    const diffContainer = document.getElementById("difficultyContainer");
    const title = document.getElementById("selectedSubtopic");

    diffSection.style.display = "block";
    title.innerText = subObj.name;

    diffContainer.innerHTML = "";

    // 🔥 NO FETCH NEEDED (already from DB)
    const levels = subObj.difficulty;

    if (!levels || levels.length === 0) {
        diffContainer.innerHTML = "<p>No difficulty found</p>";
        return;
    }

    levels.forEach(level => {
        const card = document.createElement("div");
        card.className = "difficulty-card";
        card.innerText = level;

        card.onclick = () => {
            window.location.href = `/practice/${selectedTopic}/${selectedSubtopic}/${level}`;
        };

        diffContainer.appendChild(card);
    });

    diffSection.scrollIntoView({ behavior: "smooth" });
}