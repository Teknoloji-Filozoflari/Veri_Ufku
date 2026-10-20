// Shared keyboard focus visibility for buttons, pickers and search fields.
function reveal(control) {
    let container = control.parent
    while (container) {
        if (container.contentY !== undefined && container.contentHeight !== undefined) {
            const top = control.mapToItem(container.contentItem, 0, 0).y
            if (top < container.contentY) container.contentY = top
            else if (top + control.height > container.contentY + container.height)
                container.contentY = Math.max(0, Math.min(container.contentHeight - container.height, top + control.height - container.height))
            break
        }
        container = container.parent
    }
}

function findNamed(item, name) {
    if (item.objectName === name && item.visible && item.enabled) return item
    for (let child of item.children) {
        let found = findNamed(child, name)
        if (found) return found
    }
    return null
}
function retainPickerFocus(control) {
    if (!control.activeFocus || !control.objectName) return
    const name = control.objectName
    let root = control
    while (root.parent) root = root.parent
    Qt.callLater(function() {
        const replacement = findNamed(root, name)
        if (replacement) replacement.forceActiveFocus()
    })
}
