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
