"""Basic tests for WebAgent"""


def test_import_main():
    """Test that main module can be imported"""
    import main

    assert main is not None


def test_import_webagent():
    """Test that webagent package can be imported"""
    import webagent

    assert webagent is not None


def test_basic_assertion():
    """Basic test to ensure pytest is working"""
    assert True
