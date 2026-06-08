(function () {
  function collectTabbedSections() {
    var fieldsets = Array.prototype.slice.call(document.querySelectorAll("fieldset.tabbed-fieldset"));
    var inlineGroups = Array.prototype.slice.call(document.querySelectorAll(".inline-group.tabbed-inline-group"));
    return fieldsets.concat(inlineGroups);
  }

  function initTabbedFieldsets() {
    var sections = collectTabbedSections();
    if (sections.length < 2) {
      return;
    }

    var firstSection = sections[0];
    var container = document.createElement("div");
    container.className = "shop-admin-tabs";

    function activate(index) {
      sections.forEach(function (section, sectionIndex) {
        section.classList.toggle("is-hidden", sectionIndex !== index);
      });
      Array.prototype.forEach.call(container.querySelectorAll(".shop-admin-tabs__button"), function (button, buttonIndex) {
        button.classList.toggle("is-active", buttonIndex === index);
      });
    }

    sections.forEach(function (section, index) {
      var titleNode = section.querySelector("h2, h3");
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

    firstSection.parentNode.insertBefore(container, firstSection);
    activate(0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTabbedFieldsets);
  } else {
    initTabbedFieldsets();
  }
})();
