from watcher.title_rules import is_in_role


def test_title_rule_includes_cre_analyst_titles():
    assert is_in_role("Investment Analyst")
    assert is_in_role("Commercial Mortgage Underwriter")
    assert is_in_role("Market Research Associate")
    assert is_in_role("Capital Markets Associate")


def test_title_rule_excludes_unrelated_analyst_titles():
    assert not is_in_role("Digital Workplace Analyst")
    assert not is_in_role("Marketing Analytics Manager")
    assert not is_in_role("Software Engineer")
