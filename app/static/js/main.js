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

  const attachFeedbackForm = (form) => {
    const dislikeToggle = form.querySelector("[data-dislike-toggle]");
    const panel = form.querySelector(".dislike-panel");
    const status = form.querySelector("[data-feedback-status]");
    if (dislikeToggle && panel) {
      dislikeToggle.addEventListener("click", () => {
        panel.hidden = !panel.hidden;
      });
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submitter = event.submitter;
      const body = new FormData(form);
      if (submitter && submitter.name === "value") {
        body.set("value", submitter.value);
      }
      try {
        const response = await fetch(form.action, { method: "POST", body });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.detail || "Не удалось сохранить оценку.");
        form.querySelectorAll(".feedback-chip").forEach((button) => button.classList.remove("is-selected"));
        const selected = form.querySelector(`[name="value"][value="${result.value}"]`);
        if (selected && selected.classList.contains("feedback-chip")) selected.classList.add("is-selected");
        if (result.value === "dislike" && dislikeToggle) dislikeToggle.classList.add("is-selected");
        if (status) status.textContent = "Оценка сохранена";
      } catch (error) {
        if (status) status.textContent = error.message;
      }
    });
  };

  const appendFeedbackControls = (bubble, message) => {
    if (!message || message.sender_type !== "system" || !message.id) return;
    const form = document.createElement("form");
    form.className = "ai-feedback";
    form.dataset.aiFeedback = "true";
    form.action = `/chat/api/messages/${message.id}/feedback`;
    form.method = "post";
    form.innerHTML = `
      <span>Оценить ответ</span>
      <button class="feedback-chip ${message.ai_feedback_value === "like" ? "is-selected" : ""}" type="submit" name="value" value="like">Нравится</button>
      <button class="feedback-chip ${message.ai_feedback_value === "dislike" ? "is-selected" : ""}" type="button" data-dislike-toggle>Не нравится</button>
      <div class="dislike-panel" ${message.ai_feedback_value === "dislike" ? "" : "hidden"}>
        <input type="hidden" name="value" value="dislike">
        <select name="reason">
          <option value="off_topic">Не по теме</option>
          <option value="too_general">Слишком общий ответ</option>
          <option value="not_helpful">Не помог решить вопрос</option>
          <option value="wrong_info">Ошибочная информация</option>
          <option value="bad_tone">Неподходящий тон</option>
          <option value="other">Другое</option>
        </select>
        <input name="custom_reason" maxlength="300" placeholder="Если выбрали другое">
        <button class="button button--secondary button--small" type="submit">Сохранить</button>
      </div>
      <small data-feedback-status>${message.ai_feedback_value ? "Оценка сохранена" : ""}</small>
    `;
    bubble.appendChild(form);
    attachFeedbackForm(form);
  };

  const appendMessage = (senderType, content, attachments = [], extraClass = "", message = null) => {
    clearEmptyState();
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-bubble--${senderType} ${extraClass}`.trim();
    bubble.textContent = content;
    appendAttachments(bubble, attachments);
    appendFeedbackControls(bubble, message || { sender_type: senderType });
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
        history.messages.forEach((message) => appendMessage(message.sender_type, message.content, message.attachments || [], "", message));
      }
      updateAnalysis(history);
    } catch (error) {
      conversationId = null;
      setError(error.message);
    }
  };

  if (formEl && inputEl && submitEl) formEl.addEventListener("submit", async (event) => {
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
      appendMessage("client", result.client_message.content, result.client_message.attachments || [], "", result.client_message);
      appendMessage("system", result.system_message.content, result.system_message.attachments || [], "", result.system_message);
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

document.querySelectorAll("[data-ai-feedback]").forEach((form) => {
  const dislikeToggle = form.querySelector("[data-dislike-toggle]");
  const panel = form.querySelector(".dislike-panel");
  const status = form.querySelector("[data-feedback-status]");
  if (dislikeToggle && panel) {
    dislikeToggle.addEventListener("click", () => {
      panel.hidden = !panel.hidden;
    });
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = new FormData(form);
    if (event.submitter && event.submitter.name === "value") {
      body.set("value", event.submitter.value);
    }
    try {
      const response = await fetch(form.action, { method: "POST", body });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Не удалось сохранить оценку.");
      form.querySelectorAll(".feedback-chip").forEach((button) => button.classList.remove("is-selected"));
      if (result.value === "like") form.querySelector('[name="value"][value="like"]').classList.add("is-selected");
      if (result.value === "dislike" && dislikeToggle) dislikeToggle.classList.add("is-selected");
      if (status) status.textContent = "Оценка сохранена";
    } catch (error) {
      if (status) status.textContent = error.message;
    }
  });
});
