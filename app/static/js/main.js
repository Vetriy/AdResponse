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
  const handoverEl = document.querySelector("[data-chat-handover]");
  let conversationId = chatWidget.dataset.conversationId ? Number(chatWidget.dataset.conversationId) : null;
  const reportId = chatWidget.dataset.reportId ? Number(chatWidget.dataset.reportId) : null;
  let lastRenderedDate = "";

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

  const dateLabel = (value) => {
    const date = value ? new Date(value) : new Date();
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const sameDay = (left, right) => left.toDateString() === right.toDateString();
    if (sameDay(date, today)) return "Сегодня";
    if (sameDay(date, yesterday)) return "Вчера";
    return date.toLocaleDateString("ru-RU");
  };

  const timeLabel = (value) => {
    const date = value ? new Date(value) : new Date();
    return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  };

  const appendDateSeparator = (createdAt) => {
    const label = dateLabel(createdAt);
    if (label === lastRenderedDate) return;
    const separator = document.createElement("div");
    separator.className = "chat-date-separator";
    const text = document.createElement("span");
    text.textContent = label;
    separator.appendChild(text);
    messagesEl.appendChild(separator);
    lastRenderedDate = label;
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

  const escapeAttribute = (value) => String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));

  const attachFeedbackForm = (form) => {
    const dislikeToggle = form.querySelector("[data-dislike-toggle]");
    const panel = form.querySelector(".dislike-panel");
    const status = form.querySelector("[data-feedback-status]");
    const reasonSelect = form.querySelector("[data-dislike-reason]");
    const customInput = form.querySelector("[data-custom-reason]");
    const likeButton = form.querySelector('.feedback-chip[name="value"][value="like"]');
    const setCustomVisibility = () => {
      if (!customInput || !reasonSelect) return;
      const isOther = reasonSelect.value === "other";
      customInput.hidden = !isOther;
      if (!isOther) customInput.value = "";
    };
    const setSelectedFeedback = (value) => {
      form.querySelectorAll(".feedback-chip").forEach((button) => button.classList.remove("is-selected"));
      if (value === "like" && likeButton) {
        likeButton.classList.add("is-selected");
        if (panel) panel.hidden = true;
        if (reasonSelect) reasonSelect.selectedIndex = 0;
        setCustomVisibility();
      }
      if (value === "dislike" && dislikeToggle) {
        dislikeToggle.classList.add("is-selected");
        if (panel) panel.hidden = false;
      }
    };
    if (reasonSelect) {
      reasonSelect.addEventListener("change", setCustomVisibility);
      setCustomVisibility();
    }
    if (dislikeToggle && panel) {
      dislikeToggle.addEventListener("click", () => {
        setSelectedFeedback("dislike");
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
        setSelectedFeedback(result.value);
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
    const savedReason = message.ai_feedback_reason || "off_topic";
    const savedCustomReason = escapeAttribute(message.ai_feedback_custom_reason || "");
    form.innerHTML = `
      <span>Оценить ответ</span>
      <button class="feedback-chip ${message.ai_feedback_value === "like" ? "is-selected" : ""}" type="submit" name="value" value="like">Нравится</button>
      <button class="feedback-chip ${message.ai_feedback_value === "dislike" ? "is-selected" : ""}" type="button" data-dislike-toggle>Не нравится</button>
      <div class="dislike-panel" ${message.ai_feedback_value === "dislike" ? "" : "hidden"}>
        <input type="hidden" name="value" value="dislike">
        <select name="reason" data-dislike-reason>
          <option value="off_topic" ${savedReason === "off_topic" ? "selected" : ""}>Не по теме</option>
          <option value="too_general" ${savedReason === "too_general" ? "selected" : ""}>Слишком общий ответ</option>
          <option value="not_helpful" ${savedReason === "not_helpful" ? "selected" : ""}>Не помог решить вопрос</option>
          <option value="wrong_info" ${savedReason === "wrong_info" ? "selected" : ""}>Ошибочная информация</option>
          <option value="bad_tone" ${savedReason === "bad_tone" ? "selected" : ""}>Неподходящий тон</option>
          <option value="other" ${savedReason === "other" ? "selected" : ""}>Другое</option>
        </select>
        <input name="custom_reason" data-custom-reason maxlength="300" placeholder="Укажите причину" value="${savedCustomReason}">
        <button class="button button--secondary button--small" type="submit">Сохранить</button>
      </div>
      <small data-feedback-status>${message.ai_feedback_value ? "Оценка сохранена" : ""}</small>
    `;
    bubble.appendChild(form);
    attachFeedbackForm(form);
  };

  const appendMessage = (senderType, content, attachments = [], extraClass = "", message = null) => {
    clearEmptyState();
    appendDateSeparator(message && message.created_at);
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-bubble--${senderType} ${extraClass}`.trim();
    if (senderType !== "system") {
      const meta = document.createElement("div");
      meta.className = "chat-meta";
      const name = document.createElement("strong");
      name.textContent = (message && message.sender_display_name) || (senderType === "manager" ? "Менеджер агентства" : (chatWidget.dataset.clientName || "Клиент"));
      meta.appendChild(name);
      if (senderType === "manager") {
        const role = document.createElement("span");
        role.textContent = "Менеджер";
        meta.appendChild(role);
      }
      bubble.appendChild(meta);
    }
    const body = document.createElement("div");
    body.className = "chat-content";
    body.textContent = content;
    bubble.appendChild(body);
    appendAttachments(bubble, attachments);
    appendFeedbackControls(bubble, message || { sender_type: senderType });
    const time = document.createElement("time");
    time.className = "chat-time";
    if (message && message.created_at) time.dateTime = message.created_at;
    time.textContent = timeLabel(message && message.created_at);
    bubble.appendChild(time);
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

  const updateAnalysis = ({ category, category_label: categoryLabel, handover_offered: handoverOffered, status }) => {
    if (categoryEl && (categoryLabel || category)) categoryEl.textContent = `категория: ${categoryLabel || category}`;
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
      lastRenderedDate = "";
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
      if (result.system_message) {
        appendMessage("system", result.system_message.content, result.system_message.attachments || [], "", result.system_message);
      }
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
  const reasonSelect = form.querySelector("[data-dislike-reason]");
  const customInput = form.querySelector("[data-custom-reason]");
  const likeButton = form.querySelector('.feedback-chip[name="value"][value="like"]');
  const setCustomVisibility = () => {
    if (!customInput || !reasonSelect) return;
    const isOther = reasonSelect.value === "other";
    customInput.hidden = !isOther;
    if (!isOther) customInput.value = "";
  };
  const setSelectedFeedback = (value) => {
    form.querySelectorAll(".feedback-chip").forEach((button) => button.classList.remove("is-selected"));
    if (value === "like" && likeButton) {
      likeButton.classList.add("is-selected");
      if (panel) panel.hidden = true;
      if (reasonSelect) reasonSelect.selectedIndex = 0;
      setCustomVisibility();
    }
    if (value === "dislike" && dislikeToggle) {
      dislikeToggle.classList.add("is-selected");
      if (panel) panel.hidden = false;
    }
  };
  if (reasonSelect) {
    reasonSelect.addEventListener("change", setCustomVisibility);
    setCustomVisibility();
  }
  if (dislikeToggle && panel) {
    dislikeToggle.addEventListener("click", () => {
      setSelectedFeedback("dislike");
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
      setSelectedFeedback(result.value);
      if (status) status.textContent = "Оценка сохранена";
    } catch (error) {
      if (status) status.textContent = error.message;
    }
  });
});

document.querySelectorAll("[data-autosubmit]").forEach((select) => {
  select.addEventListener("change", () => {
    const form = select.closest("form");
    if (form) form.submit();
  });
});
