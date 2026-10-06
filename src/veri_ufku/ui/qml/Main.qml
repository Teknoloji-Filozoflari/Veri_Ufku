import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    width: 1200
    height: 800
    minimumWidth: 720
    minimumHeight: 560
    visible: true
    title: "Veri_Ufku"
    color: Theme.background
    font.pixelSize: Theme.body
    palette.window: Theme.background
    palette.windowText: Theme.text
    palette.text: Theme.text
    palette.buttonText: Theme.text
    palette.button: Theme.surface
    palette.base: Theme.surface
    palette.alternateBase: Theme.background
    palette.highlight: Theme.accent
    palette.highlightedText: Theme.onAccent
    palette.light: Theme.surface
    palette.mid: Theme.border
    palette.dark: Theme.secondary
    palette.placeholderText: Theme.secondary
    property int selectedSection: 0
    property bool showDemo: false
    property bool infoOpen: false
    readonly property bool dockInfo: width >= 1100 * Theme.scale
    readonly property bool advanced: preferences && preferences.view === "advanced"
    readonly property bool darkTheme: Theme.dark
    property var helpOrigin: null
    readonly property var sections: [
        qsTranslate("Shell", "Home"), qsTranslate("Shell", "Data"),
        qsTranslate("Shell", "Prepare"), qsTranslate("Shell", "Explore"),
        qsTranslate("Shell", "Compare"), qsTranslate("Shell", "Model"),
        qsTranslate("Shell", "Report"), qsTranslate("Shell", "Learn")
    ]
    readonly property var descriptions: [
        qsTranslate("Shell", "Choose where to start. File import and sample datasets will be available in a later phase. Display preferences and infrastructure trials are available now."),
        qsTranslate("Shell", "View your rows and columns. File import and the data table are not available yet."),
        qsTranslate("Shell", "Prepare your data with a preview before applying changes. Cleaning tools are not available yet."),
        qsTranslate("Shell", "Look for patterns with charts. Charts and statistics are not available yet."),
        qsTranslate("Shell", "Understand differences between groups. Comparison tools are not available yet."),
        qsTranslate("Shell", "Make predictions with a model and understand its limits. Modeling is not available yet."),
        qsTranslate("Shell", "Save and share your findings. Report generation is not available yet."),
        qsTranslate("Shell", "Learn at your own pace. The learning center is not available yet; this panel explains the current screen.")
    ]
    function navigate(index, origin) {
        selectedSection = index
        if (origin) origin.forceActiveFocus()
        workspace.contentItem.contentY = 0
    }
    function openInformation(origin) {
        helpOrigin = origin || helpButton
        infoOpen = true
        if (!dockInfo) infoDrawer.open()
        else dockPanel.focusFirst()
    }
    function closeInformation() {
        infoOpen = false
        infoDrawer.close()
        if (helpOrigin) helpOrigin.forceActiveFocus()
    }
    onDockInfoChanged: {
        if (infoOpen) {
            if (dockInfo) infoDrawer.close()
            else infoDrawer.open()
        }
    }
    onClosing: function(event) {
        if (bridge && !bridge.closed) {
            event.accepted = false
            bridge.shutdown()
        }
    }
    Shortcut { sequence: "F1"; onActivated: window.openInformation(helpButton) }
    Shortcut { sequence: "Escape"; enabled: window.infoOpen && window.dockInfo; onActivated: window.closeInformation() }

    header: Rectangle {
        color: Theme.surface
        implicitHeight: headerBody.implicitHeight + 2 * Theme.lg
        ColumnLayout {
            id: headerBody
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.lg
            spacing: Theme.md
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.xl
                Label { text: "Veri_Ufku"; font.pixelSize: Theme.subheading; font.bold: true }
                Label {
                    objectName: "datasetContext"
                    Layout.fillWidth: true
                    text: qsTranslate("Shell", "No project open · No dataset loaded")
                    color: Theme.secondary
                    wrapMode: Text.WordWrap
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.lg
                Column {
                    spacing: Theme.xs
                    Label { text: qsTranslate("Shell", "Theme"); font.pixelSize: Theme.small; color: Theme.secondary }
                    UiCombo {
                        id: themePicker
                        objectName: "themePicker"
                        width: Math.max(150, 150 * Theme.scale)
                        model: [qsTranslate("Shell", "System"), qsTranslate("Shell", "Light"), qsTranslate("Shell", "Dark")]
                        currentIndex: preferences ? ["system", "light", "dark"].indexOf(preferences.theme) : 0
                        Accessible.name: qsTranslate("Shell", "Theme")
                        onActivated: preferences.setTheme(["system", "light", "dark"][index])
                    }
                }
                Column {
                    spacing: Theme.xs
                    Label { text: qsTranslate("Shell", "View"); font.pixelSize: Theme.small; color: Theme.secondary }
                    UiCombo {
                        id: viewPicker
                        objectName: "viewPicker"
                        width: Math.max(170, 170 * Theme.scale)
                        model: [qsTranslate("Shell", "Beginner"), qsTranslate("Shell", "Advanced")]
                        currentIndex: window.advanced ? 1 : 0
                        Accessible.name: qsTranslate("Shell", "View")
                        onActivated: preferences.setView(index === 1 ? "advanced" : "beginner")
                    }
                }
                Column {
                    spacing: Theme.xs
                    Label { text: qsTranslate("Shell", "Text size"); font.pixelSize: Theme.small; color: Theme.secondary }
                    UiCombo {
                        objectName: "scalePicker"
                        width: 120 * Theme.scale
                        model: ["100%", "125%", "150%", "200%"]
                        currentIndex: preferences ? [1, 1.25, 1.5, 2].indexOf(preferences.textScale) : 0
                        Accessible.name: qsTranslate("Shell", "Text size")
                        onActivated: preferences.setTextScale([1, 1.25, 1.5, 2][index])
                    }
                }
            }
        }
        Rectangle { height: 1; anchors.bottom: parent.bottom; width: parent.width; color: Theme.border }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: Math.max(150, 130 * Theme.scale)
            color: Theme.surface
            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.md
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.sm
                    Repeater {
                        model: window.sections
                        UiButton {
                            id: navButton
                            required property int index
                            required property string modelData
                            objectName: "nav" + index
                            Layout.fillWidth: true
                            glyph: ["⌂", "▦", "◇", "⌕", "⇄", "△", "≡", "?"][index]
                            text: modelData
                            multiline: true
                            quiet: true
                            checked: window.selectedSection === index
                            Accessible.description: index ? qsTranslate("Shell", "Not available yet. Open the availability information.") : qsTranslate("Shell", "Home")
                            onClicked: window.navigate(index, this)
                            Keys.onDownPressed: nextItemInFocusChain().forceActiveFocus()
                            Keys.onUpPressed: nextItemInFocusChain(false).forceActiveFocus()
                            Shortcut { sequence: "Ctrl+" + (navButton.index + 1); onActivated: window.navigate(navButton.index, navButton) }
                        }
                    }
                    Label {
                        text: qsTranslate("Shell", "Planned areas show their availability.")
                        font.pixelSize: Theme.small
                        color: Theme.secondary
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
        ScrollView {
            id: workspace
            objectName: "workspace"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: workspace.availableWidth
                spacing: Theme.xl
                Item { Layout.preferredHeight: Theme.xs }
                GridLayout {
                    columns: workspace.availableWidth < 650 * Theme.scale ? 1 : 2
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    Label {
                        Layout.fillWidth: true
                        text: window.sections[window.selectedSection]
                        font.pixelSize: Theme.heading
                        font.bold: true
                        wrapMode: Text.WrapAnywhere
                    }
                    UiButton {
                        id: helpButton
                        objectName: "helpButton"
                        text: qsTranslate("Shell", "What is this for?")
                        glyph: "?"
                        multiline: true
                        Layout.maximumWidth: workspace.availableWidth < 650 * Theme.scale ? workspace.availableWidth - 2 * Theme.xl : workspace.availableWidth * 0.5
                        onClicked: window.openInformation(this)
                    }
                }
                StateNotice {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: preferences && preferences.errorText.length > 0
                    kind: "error"
                    heading: qsTranslate("Shell", "Display preferences")
                    detail: preferences ? preferences.errorText : ""
                }
                // Future sections contain honest availability information, no simulated data.
                StateNotice {
                    objectName: "availabilityNotice"
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection !== 0
                    kind: "unavailable"
                    heading: qsTranslate("Shell", "Not available yet")
                    detail: window.descriptions[window.selectedSection]
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 0
                    spacing: Theme.xl
                    Label { text: qsTranslate("Shell", "Start with your data"); font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Label {
                        text: qsTranslate("Shell", "A calm place to understand your data, one step at a time.")
                        color: Theme.secondary
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    GridLayout {
                        columns: workspace.availableWidth > 700 * Theme.scale ? 2 : 1
                        Layout.fillWidth: true
                        columnSpacing: Theme.lg
                        rowSpacing: Theme.lg
                        Frame {
                            Layout.fillWidth: true
                            padding: Theme.lg
                            background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: Theme.accent; border.width: 1 }
                            ColumnLayout {
                                width: parent.width
                                spacing: Theme.md
                                UiButton { objectName: "openFileButton"; primary: true; text: qsTranslate("Shell", "Open file"); glyph: "▤"; Layout.fillWidth: true; enabled: false; multiline: true; Accessible.description: qsTranslate("Shell", "File import is not available yet.") }
                                Label { text: qsTranslate("Shell", "File import is not available yet."); Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
                            }
                        }
                        Frame {
                            Layout.fillWidth: true
                            padding: Theme.lg
                            background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: Theme.border }
                            ColumnLayout {
                                width: parent.width
                                spacing: Theme.md
                                UiButton { objectName: "sampleButton"; primary: true; text: qsTranslate("Shell", "Try sample data"); glyph: "▦"; Layout.fillWidth: true; enabled: false; multiline: true; Accessible.description: qsTranslate("Shell", "Sample datasets are not available yet.") }
                                Label { text: qsTranslate("Shell", "Sample datasets are not available yet."); Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
                            }
                        }
                    }
                    StateNotice {
                        Layout.fillWidth: true
                        kind: "empty"
                        heading: qsTranslate("Shell", "No data loaded")
                        detail: qsTranslate("Shell", "Your source files stay unchanged. Data loading will be added in a later phase.")
                    }
                    Label { text: qsTranslate("Shell", "What would you like to do?"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Label { text: qsTranslate("Shell", "Planned goals · Not available yet"); color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: workspace.availableWidth > 700 * Theme.scale ? 2 : 1
                        rowSpacing: Theme.md
                        columnSpacing: Theme.md
                        Repeater {
                            model: [
                                {label: qsTranslate("Shell", "Understand my data"), section: 1, icon: "▦"},
                                {label: qsTranslate("Shell", "Tidy up my data"), section: 2, icon: "◇"},
                                {label: qsTranslate("Shell", "Find patterns"), section: 3, icon: "⌕"},
                                {label: qsTranslate("Shell", "Compare groups"), section: 4, icon: "⇄"},
                                {label: qsTranslate("Shell", "Make a prediction"), section: 5, icon: "△"},
                                {label: qsTranslate("Shell", "Find similar records"), section: 5, icon: "◇"},
                                {label: qsTranslate("Shell", "Spot unusual records"), section: 3, icon: "⌕"},
                                {label: qsTranslate("Shell", "Share my findings"), section: 6, icon: "≡"}
                            ]
                            UiButton {
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: Math.max(64, contentItem.implicitHeight + 32)
                                text: modelData.label
                                glyph: modelData.icon
                                multiline: true
                                Accessible.description: qsTranslate("Shell", "Not available yet. Open the availability information.")
                                onClicked: window.navigate(modelData.section, this)
                            }
                        }
                    }
                }
                // Results and errors remain visible in either view, even if trial controls are collapsed.
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    spacing: Theme.md
                    StateNotice {
                        objectName: "taskNotice"
                        Layout.fillWidth: true
                        kind: startupError || (bridge && bridge.errorText) ? "error" : (bridge && bridge.active ? "loading" : (bridge && bridge.stateCode === "canceled" ? "canceled" : "empty"))
                        heading: startupError ? qsTranslate("Shell", "Unavailable") : (bridge && bridge.jobId ? qsTranslate("Main", "Task infrastructure test") + " · " + bridge.stateText : qsTranslate("Shell", "Local workspace ready"))
                        detail: bridge && bridge.jobId ? qsTranslate("Shell", "Infrastructure trial · No dataset analysis") : qsTranslate("Shell", "Theme, view and text size are saved on this computer.")
                    }
                    Label { objectName: "stateLabel"; text: bridge ? bridge.stateText : qsTranslate("Main", "Unavailable"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Label { objectName: "resultLabel"; text: bridge ? bridge.resultText : ""; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Label { objectName: "errorLabel"; text: startupError || (bridge ? bridge.errorText : ""); visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; color: Theme.error }
                    ProgressBar {
                        objectName: "jobProgress"
                        Layout.fillWidth: true
                        indeterminate: bridge && bridge.active && bridge.progress < 0
                        value: bridge && bridge.progress >= 0 ? bridge.progress : 0
                        visible: bridge && bridge.active
                        Accessible.name: qsTranslate("Shell", "Task progress")
                    }
                    UiButton { objectName: "cancelButton"; text: qsTranslate("Main", "Cancel task"); glyph: "×"; visible: bridge && bridge.active; enabled: bridge && bridge.active && !bridge.closing; onClicked: bridge.cancel() }
                    UiButton {
                        objectName: "demoToggle"
                        text: qsTranslate("Shell", "Infrastructure trials")
                        glyph: window.showDemo ? "−" : "+"
                        checkable: true
                        checked: window.showDemo
                        onClicked: window.showDemo = !window.showDemo
                    }
                    Frame {
                        Layout.fillWidth: true
                        visible: window.showDemo
                        padding: Theme.lg
                        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
                        ColumnLayout {
                            width: parent.width
                            spacing: Theme.lg
                            Label { text: qsTranslate("Shell", "These trials check the app. They do not load or analyze data."); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Flow {
                                Layout.fillWidth: true
                                spacing: Theme.sm
                                UiButton { objectName: "cpuButton"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Run CPU test"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.cpu") }
                                UiButton { objectName: "ioButton"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Run I/O test"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.io") }
                                UiButton { objectName: "unknownButton"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Test unknown progress"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.unknown") }
                            }
                        }
                    }
                    Frame {
                        objectName: "technicalSettings"
                        Layout.fillWidth: true
                        visible: window.advanced
                        padding: Theme.lg
                        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
                        ColumnLayout {
                            width: parent.width
                            spacing: Theme.md
                            Label { text: qsTranslate("Shell", "Technical details"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Label { text: qsTranslate("Main", "Change the test configuration while a task is running to verify that old results are not applied."); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Label { objectName: "bindingLabel"; text: qsTranslate("Shell", "Session:") + " " + (bridge ? bridge.sessionVersion : "—"); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                            Label { text: qsTranslate("Main", "Task ID:") + " " + (bridge ? bridge.jobId : "—"); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                            Label { text: qsTranslate("Main", "Configuration revision:") + " " + (bridge ? bridge.revision : 0); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Flow {
                                Layout.fillWidth: true
                                spacing: Theme.sm
                                UiButton { objectName: "contextButton"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Change test configuration"); enabled: bridge && !bridge.closing; onClicked: bridge.changeConfiguration() }
                                UiButton { objectName: "failureButton"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Test error transfer"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.failure") }
                            }
                        }
                    }
                    UiButton { objectName: "closeButton"; text: qsTranslate("Main", "Close"); glyph: "×"; onClicked: window.close() }
                }
                Item { Layout.preferredHeight: Theme.xl }
            }
        }
        InfoPanel {
            id: dockPanel
            objectName: "dockedInformation"
            Layout.fillHeight: true
            Layout.preferredWidth: 320 * Theme.scale
            visible: window.dockInfo && window.infoOpen
            heading: window.sections[window.selectedSection]
            detail: window.descriptions[window.selectedSection]
            onCloseRequested: window.closeInformation()
        }
    }
    Drawer {
        id: infoDrawer
        objectName: "informationDrawer"
        edge: Qt.RightEdge
        y: window.header.height
        width: Math.min(400 * Theme.scale, window.width - 32)
        height: window.height - y
        modal: true
        focus: true
        dim: false
        interactive: true
        dragMargin: 0
        closePolicy: Popup.CloseOnEscape
        padding: 0
        onClosed: { if (!window.dockInfo && window.infoOpen) window.closeInformation() }
        InfoPanel {
            anchors.fill: parent
            heading: window.sections[window.selectedSection]
            detail: window.descriptions[window.selectedSection]
            onCloseRequested: window.closeInformation()
        }
    }
}
