(function () {
    'use strict';

    function syncMceStyle(el) {
        // TinyMCE сериализует контент из data-mce-style, поэтому после правки
        // style его нужно синхронизировать, иначе высота вернётся при сохранении.
        if (!el.hasAttribute('data-mce-style')) {
            return;
        }
        var style = el.getAttribute('style');
        if (style) {
            el.setAttribute('data-mce-style', style);
        } else {
            el.removeAttribute('data-mce-style');
        }
    }

    function stripHeights(editor, table) {
        var dom = editor.dom;
        var targets = [table].concat(dom.select('tr,td,th', table));
        editor.undoManager.transact(function () {
            targets.forEach(function (el) {
                dom.setStyle(el, 'height', null);
                dom.setStyle(el, 'min-height', null);
                el.removeAttribute('height');
                if (!el.getAttribute('style')) {
                    el.removeAttribute('style');
                }
                syncMceStyle(el);
            });
        });
        editor.nodeChanged();
    }

    tinymce.PluginManager.add('tableautoheight', function (editor) {
        function currentTable() {
            return editor.dom.getParent(editor.selection.getNode(), 'table');
        }

        editor.ui.registry.addButton('tableautoheight', {
            text: 'Авто-высота',
            tooltip: 'Высота таблицы по содержимому',
            onAction: function () {
                var table = currentTable();
                if (table) {
                    stripHeights(editor, table);
                }
            },
            onSetup: function (api) {
                function handler() {
                    api.setEnabled(!!currentTable());
                }
                editor.on('NodeChange', handler);
                handler();
                return function () {
                    editor.off('NodeChange', handler);
                };
            }
        });
    });
})();
