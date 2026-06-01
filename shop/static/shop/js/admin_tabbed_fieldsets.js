(function () {
  function initTabbedFieldsets() {
    var fieldsets = Array.prototype.slice.call(document.querySelectorAll("fieldset.tabbed-fieldset"));
    if (fieldsets.length < 2) {
      return;
    }

    var firstFieldset = fieldsets[0];
    var container = document.createElement("div");
    container.className = "shop-admin-tabs";

    function activate(index) {
      fieldsets.forEach(function (fieldset, fieldsetIndex) {
        fieldset.classList.toggle("is-hidden", fieldsetIndex !== index);
      });
      Array.prototype.forEach.call(container.querySelectorAll(".shop-admin-tabs__button"), function (button, buttonIndex) {
        button.classList.toggle("is-active", buttonIndex === index);
      });
    }

    fieldsets.forEach(function (fieldset, index) {
      var titleNode = fieldset.querySelector("h2");
      var title = (titleNode && titleNode.textContent ? titleNode.textContent : "Section").trim();
      var button = document.createElement("button");
      button.type = "button";
      button.className = "shop-admin-tabs__button";
      button.textContent = title;
      button.addEventListener("click", function () {
        activate(index);
      });
      container.appendChild(button);
    });

    firstFieldset.parentNode.insertBefore(container, firstFieldset);
    activate(0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTabbedFieldsets);
  } else {
    initTabbedFieldsets();
  }
})();
