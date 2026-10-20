import QtQuick

UiTextField {
    onTextEdited: imports.connectionEdited()
}
