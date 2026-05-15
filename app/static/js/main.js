const navToggle = document.querySelector("[data-nav-toggle]");
const siteNav = document.querySelector("[data-site-nav]");

if (navToggle && siteNav) {
  navToggle.addEventListener("click", () => {
    const isOpen = siteNav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
}

const chatWidget = document.querySelector("[data-chat-widget]");

if (chatWidget) {
  const messagesEl = chatWidget.querySelector("[data-chat-messages]");
  const formEl = chatWidget.querySelector("[data-chat-form]");
  const inputEl = chatWidget.querySelector("[data-chat-input]");
  const submitEl = chatWidget.querySelector("[data-chat-submit]");
  const statusEl = chatWidget.querySelector("[data-chat-status]");
  const errorEl = chatWidget.querySelector("[data-chat-error]");
  const categoryEl = document.querySelector("[data-chat-category]");
  const toneEl = document.querySelector("[data-chat-tone]");
  const handoverEl = document.querySelector("[data-chat-handover]");
  const storageKey = "adresponseConversationId";

  const setError = (message) => {
    if (!errorEl) return;
    errorEl.hidden = !message;
    errorEl.textContent = message || "";
  };

  const setLoading = (isLoading) => {
    submitEl.disabled = isLoading;
    inputEl.disabled = isLoading;
    statusEl.textContent = isLoading ? "Готовим ответ..." : "Готов принять обращение";
  };

  const clearEmptyState = () => {
    const empty = messagesEl.querySelector(".chat-empty");
    if (empty) empty.remove();
  };

  const scrollToBottom = () => {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  };

  const appendMessage = (senderType, content, extraClass = "") => {
    clearEmptyState();
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-bubble--${senderType} ${extraClass}`.trim();
    bubble.textContent = content;
    messagesEl.appendChild(bubble);
    scrollToBottom();
    return bubble;
  };

  const appendLoadingBubble = () => {
    clearEmptyState();
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble chat-bubble--system chat-bubble--loading";
    bubble.innerHTML = "<span></span><span></span><span></span>";
    messagesEl.appendChild(bubble);
    scrollToBottom();
    return bubble;
  };

  const updateAnalysis = ({ category, emotional_tone: emotionalTone, handover_offered: handoverOffered, status }) => {
    if (categoryEl && category) categoryEl.textContent = `категория: ${category}`;
    if (toneEl && emotionalTone) toneEl.textContent = `тон: ${emotionalTone}`;
    if (handoverEl) {
      const handoverText = handoverOffered || status === "needs_manager" ? "предложен" : "не требуется";
      handoverEl.textContent = `менеджер: ${handoverText}`;
    }
  };

  const requestJson = async (url, options = {}) => {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Не удалось выполнить запрос.");
    }
    return data;
  };

  const loadHistory = async () => {
    const conversationId = localStorage.getItem(storageKey);
    if (!conversationId) return;

    try {
      const history = await requestJson(`/chat/api/conversations/${conversationId}`);
      messagesEl.innerHTML = "";
      if (history.messages.length === 0) {
        messagesEl.innerHTML = '<div class="chat-empty"><strong>Добрый день!</strong><span>Напишите, что нужно рекламировать или какая проблема возникла в кампании.</span></div>';
      } else {
        history.messages.forEach((message) => appendMessage(message.sender_type, message.content));
      }
      updateAnalysis(history);
    } catch (error) {
      localStorage.removeItem(storageKey);
      setError(error.message);
    }
  };

  formEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const content = inputEl.value.trim();
    if (!content) return;

    setError("");
    setLoading(true);
    appendMessage("client", content);
    inputEl.value = "";
    const loadingBubble = appendLoadingBubble();

    try {
      const payload = {
        conversation_id: localStorage.getItem(storageKey) ? Number(localStorage.getItem(storageKey)) : null,
        content,
      };
      const result = await requestJson("/chat/api/messages", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      localStorage.setItem(storageKey, String(result.conversation_id));
      loadingBubble.remove();
      appendMessage("system", result.system_message.content);
      updateAnalysis(result);
    } catch (error) {
      loadingBubble.remove();
      setError(error.message);
    } finally {
      setLoading(false);
      inputEl.focus();
    }
  });

  loadHistory();
}
