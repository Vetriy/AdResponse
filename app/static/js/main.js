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
  const filesEl = chatWidget.querySelector("[data-chat-files]");
  const submitEl = chatWidget.querySelector("[data-chat-submit]");
  const statusEl = chatWidget.querySelector("[data-chat-status]");
  const errorEl = chatWidget.querySelector("[data-chat-error]");
  const categoryEl = document.querySelector("[data-chat-category]");
  const toneEl = document.querySelector("[data-chat-tone]");
  const handoverEl = document.querySelector("[data-chat-handover]");
  let conversationId = chatWidget.dataset.conversationId ? Number(chatWidget.dataset.conversationId) : null;
  const reportId = chatWidget.dataset.reportId ? Number(chatWidget.dataset.reportId) : null;

  const setError = (message) => {
    if (!errorEl) return;
    errorEl.hidden = !message;
    errorEl.textContent = message || "";
  };

  const setLoading = (isLoading) => {
    submitEl.disabled = isLoading;
    inputEl.disabled = isLoading;
    if (statusEl) {
      statusEl.textContent = isLoading ? "Готовим ответ..." : "Готов принять обращение";
    }
  };

  const clearEmptyState = () => {
    const empty = messagesEl.querySelector(".chat-empty");
    if (empty) empty.remove();
  };

  const scrollToBottom = () => {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  };

  const appendAttachments = (bubble, attachments = []) => {
    if (!attachments.length) return;
    const list = document.createElement("div");
    list.className = "attachment-list";
    attachments.forEach((attachment) => {
      const link = document.createElement("a");
      link.href = attachment.url;
      if (attachment.is_image) {
        const image = document.createElement("img");
        image.src = attachment.url;
        image.alt = attachment.original_filename;
        link.appendChild(image);
      } else {
        link.className = "attachment-link";
        link.textContent = attachment.original_filename;
      }
      list.appendChild(link);
    });
    bubble.appendChild(list);
  };

  const appendMessage = (senderType, content, attachments = [], extraClass = "") => {
    clearEmptyState();
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-bubble--${senderType} ${extraClass}`.trim();
    bubble.textContent = content;
    appendAttachments(bubble, attachments);
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

  const updateAnalysis = ({ category, category_label: categoryLabel, emotional_tone: emotionalTone, emotional_tone_label: toneLabel, handover_offered: handoverOffered, status }) => {
    if (categoryEl && (categoryLabel || category)) categoryEl.textContent = `категория: ${categoryLabel || category}`;
    if (toneEl && (toneLabel || emotionalTone)) toneEl.textContent = `тон: ${toneLabel || emotionalTone}`;
    if (handoverEl) {
      const managerStatuses = ["needs_manager", "handover_requested", "assigned_to_manager", "manager_answered"];
      const handoverText = handoverOffered || managerStatuses.includes(status) ? "предложен" : "не требуется";
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
    if (!conversationId) return;

    try {
      const history = await requestJson(`/chat/api/conversations/${conversationId}`);
      messagesEl.innerHTML = "";
      if (history.messages.length === 0) {
        messagesEl.innerHTML = '<div class="chat-empty"><strong>Добрый день!</strong><span>Напишите, что нужно рекламировать или какая проблема возникла в кампании.</span></div>';
      } else {
        history.messages.forEach((message) => appendMessage(message.sender_type, message.content, message.attachments || []));
      }
      updateAnalysis(history);
    } catch (error) {
      conversationId = null;
      setError(error.message);
    }
  };

  formEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const content = inputEl.value.trim();
    if (!content) return;

    setError("");
    setLoading(true);
    const selectedFiles = filesEl ? Array.from(filesEl.files) : [];
    inputEl.value = "";
    if (filesEl) filesEl.value = "";
    const loadingBubble = appendLoadingBubble();

    try {
      const payload = new FormData();
      if (conversationId) payload.append("conversation_id", String(conversationId));
      if (reportId) payload.append("report_id", String(reportId));
      payload.append("content", content);
      selectedFiles.forEach((file) => payload.append("attachments", file));
      const response = await fetch("/chat/api/messages/upload", {
        method: "POST",
        body: payload,
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.detail || "Не удалось выполнить запрос.");
      }

      conversationId = Number(result.conversation_id);
      chatWidget.dataset.conversationId = String(result.conversation_id);
      loadingBubble.remove();
      appendMessage("client", result.client_message.content, result.client_message.attachments || []);
      appendMessage("system", result.system_message.content, result.system_message.attachments || []);
      updateAnalysis(result);
    } catch (error) {
      loadingBubble.remove();
      setError(error.message);
    } finally {
      setLoading(false);
      inputEl.focus();
    }
  });

  if (conversationId && chatWidget.dataset.preloaded !== "true") {
    loadHistory();
  }
}
