import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    objectName: "monitoringPanel"
    signal helpRequested(var origin, string context)
    function number(v) { return v === null || v === undefined ? "sunulmuyor" : typeof v === "number" ? Number(v).toPrecision(5) : String(v) }
    function resultText(r) {
        if (!r || !r.run_id) return "Henüz izleme sonucu yok. Referans ve pencereyi seçip açıkça çalıştırın."
        let rows=["Yerel batch izleme · " + r.run_id, "Referans: " + r.reference.version + " · n=" + r.reference.n,
            "Pencere: " + r.window.version + " · n=" + r.window.n + " · zaman filtresinde dışlanan=" + r.window.excluded_by_window,
            r.spec.window_start + " → " + r.spec.window_end + " · as_of=" + r.spec.as_of,
            "Seçim: " + r.window.selection, "Eşikler: PSI=" + r.spec.psi_threshold + " · KS D=" + r.spec.ks_effect_threshold + " · alpha=" + r.spec.alpha + " · JS=" + r.spec.js_threshold + " · Wasserstein=" + r.spec.wasserstein_threshold + " (kaynak birimi)",
            "Eksiklik eşiği=" + r.spec.missing_threshold + " · min_n=" + r.spec.min_n + " · bin=" + r.spec.bins, "", "Şema ve özellikler"]
        for(let v of r.schema_drift) rows.push((v.alarm ? "UYARI · " : "Ölçüldü · ") + v.reference_column + " → " + v.window_column + " · " + (v.status || v.reference_type + " / " + v.window_type) + (v.metadata_difference && Object.keys(v.metadata_difference).length ? " · birim/ölçüm metadata farkı" : ""))
        for(let v of r.features) {
            let d=v.distribution, q=v.quality
            rows.push(v.window + " · " + d.status + " · alarm=" + d.alarm + " · PSI=" + number(d.psi) + " · Wasserstein=" + number(d.wasserstein) + " · JS=" + number(d.js_distance),
                "n referans/pencere=" + number(d.reference_n) + "/" + number(d.window_n) + " · dışlanan=" + number(d.reference_excluded) + "/" + number(d.window_excluded) + " · KS D=" + number(d.ks_effect) + " · düzeltilmiş p=" + number(d.ks_p_bonferroni),
                "Eksik/sonlu olmayan oran referans/pencere=" + number(q.reference_missing_rate) + "/" + number(q.window_missing_rate) + " · kalite alarmı=" + number(q.alarm))
        }
        rows.push("", "Veri sözleşmesi")
        for(let side of ["reference","window"]) {
            let q=r.data_quality[side]
            rows.push(side + " · " + q.contract_status + " · hata ihlali=" + number(q.error_violations) + " · uyarı ihlali=" + number(q.warning_violations))
            for(let v of q.rules || []) rows.push(v.rule_id + " · " + v.kind + " · " + v.severity + " · ihlal=" + v.violations)
            if(q.unsupported_foreign_key_rules && q.unsupported_foreign_key_rules.length) rows.push("FK monitoring desteklenmiyor: " + q.unsupported_foreign_key_rules.join(", "))
        }
        rows.push("", "Model / gerçek hedef")
        if(!r.models.length) rows.push("Model seçilmedi: yalnız veri izleme. Başarı ve kalibrasyon ölçülmedi.")
        for(let m of r.models) {
            let e=m.window_evaluation
            rows.push(m.role + " · " + m.run_id, "Hedef durumu: " + e.status + " · eşleşen n=" + e.n,
                "Metrikler: " + (e.metrics ? JSON.stringify(e.metrics) : "SUNULMUYOR — gerçek hedef yok veya yetersiz"),
                "Kalibrasyon: " + (e.calibration ? "reliability n=" + e.calibration.n + " · ortalama ECE=" + number(e.calibration.mean_ece) + " · class n=" + e.calibration.class_counts.join(", ") : "SUNULMUYOR"))
            if(e.label_delay) rows.push("Hedef gecikmesi: pending=" + e.label_delay.pending + " · overdue=" + e.label_delay.overdue + " · gözlenen ortalama saniye=" + number(e.label_delay.observed_mean_seconds))
            for(let c of m.performance_changes) rows.push(c.metric + " referans farkı=" + number(c.delta) + " · eşik=" + c.threshold + " · alarm=" + c.alarm)
            if(m.calibration_change) rows.push("ECE değişimi=" + number(m.calibration_change.delta) + " · alarm=" + m.calibration_change.alarm)
        }
        for(let p of r.prediction_drift) rows.push("Tahmin drift · " + p.role + " · PSI=" + number(p.distribution.psi) + " · Wasserstein=" + number(p.distribution.wasserstein) + " · JS=" + number(p.distribution.js_distance) + " · alarm=" + p.distribution.alarm)
        rows.push("Shadow: " + r.shadow.status + (r.shadow.n ? " · n=" + r.shadow.n + " · tahmin farkı=" + number(r.shadow.mean_absolute_prediction_difference) + " · performans karşılaştırılabilir=" + r.shadow.performance_available : ""),
            "Yeni eğitim / otomatik deploy / overwrite: YOK · fit çağrısı=" + r.fit_calls, "", "Yorum sınırları")
        for(let warning of r.limitations) rows.push("• " + warning)
        return rows.join("\n")
    }
    spacing: Theme.md
    UiCheckBox { id: expanded; objectName: "monitoringExpanded"; text: "Yerel batch model izleme"; Layout.fillWidth: true }
    ColumnLayout {
        visible: expanded.checked
        Layout.fillWidth: true
        UiLabel { text: "Referans/pencere ve eşikler kayıtlıdır. Drift performans kaybı kanıtı değildir; labels yoksa başarı metriği sunulmaz. Otomatik eğitim/deploy yok. API kapalı varsayılan; açılışta ağ isteği yok."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiLabel { text: "Kayıtlı dataset/ColumnId'ler (açık eşleme için)"; Layout.fillWidth: true }
        UiCombo { id: dataset; objectName: "monitoringDataset"; accessibleLabel: "Monitoring kaynak şeması"; model: monitoring.datasets; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
        UiLabel { text: dataset.currentIndex >= 0 ? JSON.stringify(monitoring.datasets[dataset.currentIndex].columns) : "Dataset yok"; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
        UiLabel { text: "Declarative monitoring recipe: reference/window DatasetVersion, features [{reference:ColumnId,window:ColumnId,kind:numeric|categorical,continuous:false}], window_start/window_end/as_of timezone ile. İsteğe bağlı champion/challenger record id veya use_champion_route:true; ColumnId mapping, labels/key/arrival. Bütün kaynak ≤10000 satır; sessiz sample yok."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiTextArea { id: recipe; objectName: "monitoringRecipe"; Accessible.name: "Monitoring referans pencere eşik recipe JSON"; wrapMode: Text.WrapAnywhere; textFormat: TextEdit.PlainText; property string helpContext: "model.monitor.batch"; text: '{"reference":"","window":"","features":[],"window_start":"2026-01-01T00:00:00Z","window_end":"2026-02-01T00:00:00Z","as_of":"2026-02-02T00:00:00Z"}'; Layout.fillWidth: true; Layout.preferredHeight: 180 }
        Flow {
            Layout.fillWidth: true; spacing: Theme.sm
            UiButton { objectName: "monitoringRun"; text: "Batch izlemeyi açıkça çalıştır ve kaydet"; helpContext: "model.monitor.batch"; enabled: !monitoring.busy; onClicked: monitoring.run(recipe.text) }
            UiButton { objectName: "monitoringCancel"; text: "İptal"; enabled: monitoring.busy; onClicked: monitoring.cancel() }
            UiButton { visible: false; text: "Bu ne işe yarar?"; helpContext: "model.monitor.batch"; onClicked: helpRequested(this, "model.monitor.batch") }
        }
        UiCombo { id: champion; objectName: "monitoringChampion"; accessibleLabel: "Yerel champion model kaydı"; model: monitoring.models; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
        UiLabel { text: "Model kayıt kimliği: " + (champion.currentValue || "") + " · Yeni eğitim mevcut model formunda kullanıcı başlatmalı. Seçmek dış deploy yapmaz; shadow sonuçları modeli otomatik değiştirmez."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiButton { objectName: "monitoringActivate"; text: "Seçili modeli yerel champion yap (audit kaydı)"; enabled: !monitoring.busy && !!champion.currentValue; onClicked: monitoring.selectChampion(champion.currentValue, false) }
        UiButton { objectName: "monitoringRollback"; text: "Önceki model referansına geri dön"; enabled: !monitoring.busy && !!monitoring.currentRoute.value && !!monitoring.currentRoute.value.previous_record_id; onClicked: monitoring.selectChampion(monitoring.currentRoute.value.previous_record_id, true) }
        UiLabel { text: monitoring.currentRoute.value ? "Yerel champion: " + monitoring.currentRoute.value.record_id + " · önceki: " + (monitoring.currentRoute.value.previous_record_id || "yok") + " · rollback=" + monitoring.currentRoute.value.rollback : "Yerel champion seçilmedi"; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
        UiCombo { id: saved; objectName: "monitoringSaved"; accessibleLabel: "Kaydedilmiş monitoring run"; model: monitoring.saved; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
        UiButton { objectName: "monitoringOpen"; text: "Kayıtlı raporu hash kontrolüyle aç"; enabled: !monitoring.busy && !!saved.currentValue; onClicked: monitoring.openReport(saved.currentValue) }
        UiLabel { objectName: "monitoringError"; text: monitoring.errorText; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ScrollView {
            id: monitorReportScroll
            Layout.fillWidth: true
            Layout.preferredHeight: 500
            contentWidth: availableWidth
            clip: true
            focusPolicy: Qt.StrongFocus
            Accessible.name: "Monitoring sonuç kaydırma alanı"
            UiLabel { objectName: "monitoringReport"; Accessible.name: "Monitoring aggregate raporu"; property string helpContext: "model.monitor.batch"; text: resultText(monitoring.report); width: monitorReportScroll.availableWidth; wrapMode: Text.WrapAnywhere; textFormat: Text.PlainText }
        }
    }
}
