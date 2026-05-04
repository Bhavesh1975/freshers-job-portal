// ✅ Clean imports
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';

document.addEventListener("DOMContentLoaded", () => {

    console.log("Chatbot running ✅");

    // ================= THREE JS =================

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    camera.position.set(0, 0, 4);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

    const SIZE = 120; // 🔥 smaller (no overlap)
    renderer.setSize(SIZE, SIZE);
    renderer.setClearColor(0x000000, 0);

    const canvas = renderer.domElement;

    canvas.style.position = "fixed";
    canvas.style.bottom = "12px";
    canvas.style.right = "12px";
    canvas.style.width = SIZE + "px";
    canvas.style.height = SIZE + "px";
    canvas.style.zIndex = "2"; // 🔥 behind chatbot
    canvas.style.cursor = "pointer";

    document.body.appendChild(canvas);

    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 1));

    const dirLight = new THREE.DirectionalLight(0xffffff, 2);
    dirLight.position.set(5, 5, 5);
    scene.add(dirLight);

    // HDRI
    new RGBELoader().load(
        'https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/studio_small_09_1k.hdr',
        (texture) => {
            texture.mapping = THREE.EquirectangularReflectionMapping;
            scene.environment = texture;
        }
    );

    const loader = new GLTFLoader();
    let mixer;
    let chatbotModel;

    loader.load('/static/models/chatbot.glb', (gltf) => {

        chatbotModel = gltf.scene;

        chatbotModel.scale.set(1.4, 1.4, 1.4);

        // Auto center
        const box = new THREE.Box3().setFromObject(chatbotModel);
        const center = box.getCenter(new THREE.Vector3());
        chatbotModel.position.sub(center);

        chatbotModel.rotation.y = -Math.PI / 2;

        chatbotModel.traverse((child) => {
            if (child.isMesh && child.material) {
                child.material.color.set(0x111111);
                child.material.metalness = 1;
                child.material.roughness = 0.25;
                child.material.envMapIntensity = 2;
            }
        });

        scene.add(chatbotModel);

        if (gltf.animations.length > 0) {
            mixer = new THREE.AnimationMixer(chatbotModel);
            gltf.animations.forEach((clip) => {
                mixer.clipAction(clip).play();
            });
        }
    });

    // ================= CLICK DETECTION =================

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    canvas.addEventListener("click", (event) => {

        const rect = canvas.getBoundingClientRect();

        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);

        if (chatbotModel) {
            const intersects = raycaster.intersectObject(chatbotModel, true);

            if (intersects.length > 0) {
                toggleChatbot();
            }
        }
    });

    // ================= ANIMATION =================

    const clock = new THREE.Clock();

    function animate() {
        requestAnimationFrame(animate);

        if (mixer) mixer.update(clock.getDelta());

        renderer.render(scene, camera);
    }

    animate();

    // ================= CHATBOT =================

    const chatbot = document.getElementById("chatbot-container");
    const closeBtn = document.getElementById("closeChat");
    const sendBtn = document.getElementById("sendBtn");
    const chatInput = document.getElementById("chatInput");
    const chatBody = document.getElementById("chatBody");

    let isOpen = false;

    function toggleChatbot() {
        isOpen = !isOpen;
        chatbot.classList.toggle("active", isOpen);

        if (isOpen && chatBody.children.length === 0) {
            addBot("Hi 👋 I am your job assistant. Ask me anything!");
        }
    }

    // Close button
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            isOpen = false;
            chatbot.classList.remove("active");
        });
    }

    // ================= UI HELPERS =================

    function addBot(text) {
        const msg = document.createElement("div");
        msg.className = "bot-message";
        msg.innerText = text;
        chatBody.appendChild(msg);
        scrollBottom();
    }

    function addUser(text) {
        const msg = document.createElement("div");
        msg.className = "user-message";
        msg.innerText = text;
        chatBody.appendChild(msg);
        scrollBottom();
    }

    function scrollBottom() {
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    // ================= API CALL =================

    async function sendMessage() {
        if (!chatInput) return;

        const message = chatInput.value.trim();
        if (!message) return;

        addUser(message);
        chatInput.value = "";

        // Typing indicator
        const typing = document.createElement("div");
        typing.className = "bot-message";
        typing.innerText = "Typing...";
        chatBody.appendChild(typing);
        scrollBottom();

        try {
            const res = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message })
            });

            const data = await res.json();

            typing.remove();
            addBot(data.reply || "No response");

        } catch (err) {
            typing.remove();
            addBot("⚠️ Server error. Check backend.");
        }
    }

    // ================= INPUT =================

    if (sendBtn) {
        sendBtn.addEventListener("click", (e) => {
            e.stopPropagation(); // 🔥 prevent canvas click conflict
            sendMessage();
        });
    }

    if (chatInput) {
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                sendMessage();
            }
        });
    }

});