// ── Field chip management ─────────────────────────────────────────────────

function addField(name) {
  name = name.trim().replace(/\s+/g, "_");
  if (!name || currentFields.includes(name)) return;
  currentFields.push(name);

  const tag = document.createElement("span");
  tag.className = "tag";
  tag.dataset.field = name;
  tag.innerHTML =
    escHtml(name) +
    `<button onclick="removeField('${escHtml(name)}')" title="Remove">×</button>`;
  document.getElementById("tags-wrap").insertBefore(
    tag,
    document.getElementById("field-input")
  );
}

function removeField(name) {
  currentFields = currentFields.filter(f => f !== name);
  document.querySelector(`.tag[data-field="${CSS.escape(name)}"]`)?.remove();
}

/** Replace all current fields with a new list (used by agent auto-fill). */
function setFields(names) {
  currentFields = [];
  document.querySelectorAll(".tag").forEach(t => t.remove());
  names.forEach(n => addField(n));
}

function onFieldKeydown(e) {
  if (e.key === "Enter" || e.key === ",") {
    e.preventDefault();
    addField(e.target.value.replace(/,/g, ""));
    e.target.value = "";
  } else if (e.key === "Backspace" && e.target.value === "" && currentFields.length) {
    removeField(currentFields[currentFields.length - 1]);
  }
}
