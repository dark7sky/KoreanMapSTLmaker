from scripts import release_check


def test_release_checks_pass_without_pytest():
    report = release_check.run_release_checks(run_tests=False)

    assert report["passed"] is True
    assert {check["name"] for check in report["checks"]} == {
        "required_files",
        "master_plan_progress",
        "sample_registry",
        "sample_auto_build",
        "sample_model_build",
        "real_data_acceptance_evidence",
    }


def test_release_check_text_report_includes_status():
    report = {"passed": True, "checks": [{"name": "sample", "passed": True, "message": "ok"}]}

    text = release_check.format_text_report(report)

    assert "RELEASE_CHECK PASS" in text
    assert "[PASS] sample: ok" in text
