"""Explicit bounded acceptance selection; no whole-phase inference from a passing module."""

GROUPS = {
    "table": [
        "test_cleaning.py::test_fill_hand_values_counts_and_undo",
        "test_cleaning.py::test_dedup_order_equality_and_all_member_lineage",
        "test_charts.py::test_hand_histogram_box_missing_and_exact_summary",
        "test_charts.py::test_real_matplotlib_png_svg_persist_reopen_and_protected_export",
    ],
    "weighted": [
        "test_missing_sampling.py::test_hand_weighted_mean_semantics_and_reopen_exportable_identity",
        "test_missing_sampling.py::test_rubin_hand_calculation_and_barnard_rubin_not_average_se",
        "test_missing_sampling.py::test_survey_hand_two_strata_nested_psus_and_no_lonely_adjustment",
        "test_missing_sampling.py::test_fold_joint_fit_validation_values_never_learned_and_all_missing_rejected",
        "test_missing_sampling.py::test_bad_weights_rejected_without_mutation",
    ],
    "experiment-bayes": [
        "test_experiments.py::test_mean_welch_reference_baseline_guardrail_and_atomic_reopen",
        "test_experiments.py::test_srm_exact_fixture_suppresses_primary_inference",
        "test_bayes.py::test_conjugate_hand_calculations",
        "test_bayes.py::test_real_normal_conjugate_sampler_converges_and_loo",
        "test_bayes.py::test_sampler_cancellation_inside_actual_callback",
        "test_bayes.py::test_optional_backend_absence_controlled",
    ],
    "regression-calibration": [
        "test_uncertainty.py::test_calibration_exact_sklearn_frozen_reference_and_fit_spy",
        "test_uncertainty.py::test_native_template_safe_package_inference_and_empirical_coverage",
        "test_uncertainty.py::test_development_ignores_final_targets_and_features",
        "test_uncertainty.py::test_multiclass_order_calibration_normalization_and_no_binary_threshold",
        "test_uncertainty.py::test_shared_joint_partition_group_time_horizon",
    ],
    "spatial-time": [
        "test_geo.py::test_crs_reference_xy_and_metric_distance",
        "test_geo.py::test_spatial_block_plan_no_fold_overlap_and_moran_hand_formula",
        "test_geo.py::test_spatial_blocks_feed_existing_group_validation",
        "test_validation.py::test_actual_baselines_group_time_and_json_roundtrip",
        "test_validation.py::test_group_time_overlap_rejected_no_fallback",
        "test_time_series.py::test_future_targets_never_change_selection_features_or_forecast",
        "test_temporal.py",
    ],
    "causal-survival": [
        "test_causal.py::test_first_stage_known_effect_and_atomic_roundtrip",
        "test_causal.py::test_positivity_separation_visible",
        "test_causal.py::test_iv_against_independent_2sls_reference",
        "test_survival.py::test_hand_km_risk_counts_and_safe_roundtrip",
        "test_survival.py::test_cox_against_independent_partial_likelihood_and_baseline",
        "test_survival.py::test_model_predict_after_numeric_roundtrip_reject_extrapolation_and_code",
    ],
    "nlp-vision-audio": [
        "test_nlp.py::test_turkish_original_unicode_codepoints_utf16_emoji_combining",
        "test_nlp.py::test_training_pool_test_label_poison_and_train_only_vocabulary",
        "test_nlp.py::test_wrong_model_language_missing_model_safe_weights_and_hash",
        "test_nlp.py::test_embedding_cosine_reference_oov_and_relevance_required",
        "test_vision.py::test_real_adapter_cpu_tasks_safe_roundtrip_and_prediction",
        "test_vision.py::test_metric_hand_references_duplicate_matching_and_absent_classes",
        "test_vision.py::test_corrupt_large_alpha_and_annotation_mismatch",
        "test_audio.py::test_real_adapter_pipeline_safe_roundtrip_and_fit_ids",
        "test_audio.py::test_known_sine_psd_mfcc_resampling_and_quality",
        "test_audio.py::test_fold_poison_isolation_and_overlap_same_component",
        "test_audio.py::test_controlled_bad_audio_segments_channel_and_model_unavailable",
    ],
    "recommendation-graph": [
        "test_recommendation.py::test_hand_metrics_and_empty",
        "test_recommendation.py::test_methods_persist_new_ids_source_lineage",
        "test_recommendation.py::test_global_protected_future_and_timestamp_ties",
        "test_recommendation.py::test_local_only_source_missing_and_known_content_reference",
        "test_graphs.py::test_hand_centrality_components_degree",
        "test_graphs.py::test_shortest_reference_weight_and_unreachable",
        "test_graphs.py::test_multiedge_community_projection_and_identity",
    ],
    "workflow-repro": [
        "test_workflow.py",
        "test_repro.py::test_profile_reference_bundle_exact_and_reopen_hash",
        "test_repro.py::test_corruption_schema_and_environment_fail_closed",
        "test_repro.py::test_workflow_safe_model_artifact_and_numeric_policy",
        "test_repro.py::test_secret_redaction_and_data_rejection",
        "test_repro.py::test_changed_data_does_not_pass_numeric_tolerance",
    ],
    "guardrails": [
        "test_environment_distribution.py",
        "test_projects.py",
        "test_lifecycle.py",
        "test_search.py",
        "test_plugins.py",
        "test_jobs.py",
        "test_validation.py::test_test_feature_poison_never_changes_fit_and_hand_error",
        "test_validation.py::test_repeat_test_ledger_subsequent_choice_copy_and_reopen",
        "test_learning_lab.py",
    ],
    "numeric": ["test_release_benchmarks.py"],
}

GUI = {
    "table": [
        "test_cleaning_gui.py",
        "test_charts_gui.py::test_seven_forms_spawn_selection_zoom_export_and_reopen",
    ],
    "weighted": [
        "test_missing_sampling_gui.py::test_all_advanced_methods_real_qml_spawn_export_save_reopen[weighted_mean]"
    ],
    "experiment-bayes": [
        "test_experiments_gui.py::test_experiment_desktop_plan_calculate_export_reopen_help[experiment_mean-ITT]",
        "test_bayes_gui.py::test_bayes_gui_offline_templates[bayes_beta_binomial]",
    ],
    "regression-calibration": [
        "test_uncertainty_gui.py::test_actual_uncertainty_gui_safe_model_final_and_reopen[sigmoid-classification]",
        "test_uncertainty_gui.py::test_actual_uncertainty_gui_safe_model_final_and_reopen[interval-regression]",
        "test_uncertainty_gui.py::test_group_time_calibration_gui_and_coverage_scope",
    ],
    "spatial-time": [
        "test_geo_gui.py::test_qml_geo_operation_preview_apply_undo[geo_reproject]",
        "test_validation_gui.py::test_real_qml_group_time_repeat_final_and_reopen",
    ],
    "causal-survival": [
        "test_causal_gui.py::test_causal_qml_template[causal_randomized]",
        "test_survival_gui.py::test_survival_desktop_path[survival_km-normal]",
    ],
    "nlp-vision-audio": [
        "test_nlp_gui.py::test_real_nlp_gui[ner]",
        "test_vision_gui.py::test_real_gui_task_reopen_and_new_data[classification]",
        "test_audio_gui.py::test_real_audio_gui_reopen_new_data_prediction[classification]",
        "test_audio_gui.py::test_real_audio_gui_missing_speech_model_and_cancel",
    ],
    "recommendation-graph": [
        "test_recommendation_gui.py::test_real_recommendation_gui[popularity]",
        "test_graphs_gui.py::test_real_graph_compute_reopen_export[centrality]",
    ],
    "workflow-repro": [
        "test_workflow_gui.py::test_gui_typed_editor_dry_run_and_cli_equivalence",
        "test_repro_gui.py::test_gui_report_lineage_reference_bundle_rerun",
    ],
}

# Additional bounded path; does not replace or erase the initial long-sequence selection.
GUI["table-smoke"] = ["test_release_benchmark_gui.py"]
GUI["audio-smoke"] = [
    "test_audio_gui.py::test_real_audio_gui_reopen_new_data_prediction[classification]"
]
