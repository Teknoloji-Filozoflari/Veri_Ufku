import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function field(value) {
        return value === undefined || value === null ? "sunulmuyor / uygulanmaz" : String(value)
    }
    function reportText(r) {
        if (!r || !r.output) return "Henüz simülasyon/optimizasyon çalıştırılmadı."
        let o=r.output
        let rows=["Senaryo · "+r.spec.method+" · "+r.run_id,"Input varsayımları: "+r.spec.assumptions,"", "Durum: "+o.status+" · output birimi: "+o.output_unit]
        if(r.spec.method==="monte-carlo") {
            rows.push("Seed="+r.spec.seed+" · draw="+o.draws+" · "+o.rng+" · bağımlılık="+r.spec.dependence,"Ortalama="+o.mean+" · SD="+o.sd+" · ortalama Monte Carlo SE="+o.mean_mcse)
            for(let q of o.quantiles) rows.push("Quantile "+q.probability+" = "+q.value+" · yaklaşık MC SE="+q.mcse_approx)
            rows.push(o.quantile_method,"Belirsizlik türleri: "+JSON.stringify(o.uncertainty_types),o.uncertainty_scope,"Sensitivity")
            for(let v of o.sensitivity) rows.push(v.input+" · Spearman="+v.spearman+" · lokal türev="+v.derivative_at_sample_mean+" "+v.derivative_unit)
        } else {
            rows.push("Objective="+field(o.objective)+" · aday="+JSON.stringify(o.point),"Feasible="+o.feasibility.feasible+" · optimum="+o.optimal,"Solver="+(o.solver||"frozen model what-if")+" · raw status="+field(o.raw_status),"Gap="+field(o.mip_relative_gap)+" · bound="+field(o.objective_bound)+" · tolerance="+field(o.requested_tolerance),"Süre bütçesi="+r.spec.seconds+" s · gerçek iş süresi="+r.duration_seconds+" s")
            for(let c of o.feasibility.checks) rows.push(c.kind+" "+c.name+" · ihlal="+c.violation+" "+c.unit)
            if(o.model_domain) rows.push("Model fit aralıkları: "+JSON.stringify(o.model_domain.domain),o.model_domain.joint_support,"Geçerlilik alanı dışında: "+JSON.stringify(o.outside_model_domain||[]))
        }
        rows.push("", "Kayıtlı input/constraints: "+JSON.stringify(r.spec),"", "Yorum sınırları")
        for(let warning of r.limitations) rows.push("• "+warning)
        return rows.join("\n")
    }
    UiCheckBox { id: expanded; objectName: "scenarioExpanded"; text: "Simülasyon, senaryo ve optimizasyon"; Layout.fillWidth: true }
    ColumnLayout {
        visible: expanded.checked
        Layout.fillWidth: true
        UiLabel { text: "Varsayımlara bağlı yerel hesap. Feasible öneri gerçek dünyada uygulanabilirlik garantisi değildir. Kaynak kayıtlar değişmez; model eğitimi veya dış eylem yok."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiCombo { id: method; objectName: "scenarioMethod"; accessibleLabel: "Simülasyon veya solver yöntemi"; model: scenarios.methods; Layout.fillWidth: true }
        UiButton { objectName: "scenarioTemplate"; text: "Seçilen şablonu tarife yükle"; helpContext: "scenario.monte-carlo"; onClicked: recipe.text=scenarios.template(method.currentText) }
        UiLabel { text: "Normal/uniform/triangular dağılımlar; bağımsızlık açık seçilir. Correlated yol yalnız joint-normal ve PSD correlation. Algebra: offset + linear·x + 0.5 xᵀQx. LP/MILP linear; nonlinear bounded SLSQP yerel aday. Her katsayıda value/unit, her değişkende unit gerekli. Boyutsuz: dimensionless."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiTextArea { id: recipe; objectName: "scenarioRecipe"; Accessible.name: "Senaryo input objective constraints JSON tarifi"; property string helpContext: "scenario.monte-carlo"; textFormat: TextEdit.PlainText; wrapMode: Text.WrapAnywhere; text: scenarios.template("monte-carlo"); Layout.fillWidth: true; Layout.preferredHeight: 240 }
        Flow {
            Layout.fillWidth: true; spacing: Theme.sm
            UiButton { objectName: "scenarioRun"; text: "Senaryoyu açıkça hesapla ve kaydet"; helpContext: "scenario.monte-carlo"; enabled: !scenarios.busy; onClicked: scenarios.run(recipe.text) }
            UiButton { objectName: "scenarioCancel"; text: "İptal"; enabled: scenarios.busy; onClicked: scenarios.cancel() }
            UiButton { visible: false; text: "Bu ne işe yarar?"; helpContext: "scenario.linear"; onClicked: helpRequested(this,"scenario.linear") }
        }
        UiCombo { id: model; objectName: "scenarioModel"; accessibleLabel: "Senaryoya bağlanabilir frozen model"; model: scenarios.models; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
        UiButton { objectName: "scenarioModelTemplate"; text: "Seçili modelle what-if/optimize tarifi hazırla"; helpContext: "scenario.model-optimize"; enabled: !!model.currentValue && (method.currentText === "what-if" || method.currentText === "model-optimize"); onClicked: recipe.text=scenarios.modelTemplate(method.currentText, model.currentValue) }
        UiLabel { text: "Optional model referansı: "+(model.currentValue||"model yok")+". Model what-if/optimize: bütün Float64 özelliklerin eğitim ColumnId sırası ve kart birimleri. Sınırlar yalnız fit satırlarından kontrol edilir; final test kullanılmaz. Model seçimi tek başına hesap başlatmaz."; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
        UiCombo { id: saved; objectName: "scenarioSaved"; accessibleLabel: "Kaydedilmiş senaryo raporu"; model: scenarios.saved; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
        UiButton { objectName: "scenarioOpen"; text: "Kayıtlı senaryoyu hash kontrolüyle aç"; enabled: !scenarios.busy && !!saved.currentValue; onClicked: scenarios.openReport(saved.currentValue) }
        UiLabel { objectName: "scenarioError"; text: scenarios.errorText; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ScrollView {
            id: reportScroll
            Layout.fillWidth: true; Layout.preferredHeight: 500
            contentWidth: availableWidth
            activeFocusOnTab: true
            Accessible.name: "Senaryo sonuçları kaydırma alanı"
            UiLabel { objectName: "scenarioReport"; width: reportScroll.availableWidth; text: root.reportText(scenarios.report); textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere }
        }
    }
}
