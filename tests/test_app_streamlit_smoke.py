from streamlit.testing.v1 import AppTest


def test_streamlit_quick_build_renders_without_errors():
    app = AppTest.from_file("app/streamlit_app.py").run(timeout=30)

    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["빠른 제작", "자동 제작", "수동 제작", "데이터 준비"]
    assert [title.value for title in app.title] == ["KoreanMapSTLmaker"]
    assert "샘플 모델 만들기" in [button.label for button in app.button]


def test_streamlit_sample_button_builds_downloadable_stl():
    app = AppTest.from_file("app/streamlit_app.py").run(timeout=30)

    sample_button = next(button for button in app.button if button.label == "샘플 모델 만들기")
    app = sample_button.click().run(timeout=120)

    assert not app.exception
    assert "3D 모델 제작이 완료되었습니다." in [message.value for message in app.success]
    assert "STL 다운로드" in [button.label for button in app.get("download_button")]
