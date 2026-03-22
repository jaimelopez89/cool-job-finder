from src.geo import assign_geo_bucket, enforce_salary_threshold


def test_remote_bucket():
    assert assign_geo_bucket("Remote", remote=True) == "remote"


def test_remote_flag_wins():
    assert assign_geo_bucket("San Francisco, CA", remote=True) == "remote"


def test_finland_bucket():
    assert assign_geo_bucket("Helsinki, Finland") == "finland"


def test_espoo_is_finland():
    assert assign_geo_bucket("Espoo, Finland") == "finland"


def test_spain_bucket():
    assert assign_geo_bucket("Madrid, Spain") == "spain_latam"


def test_barcelona_is_spain():
    assert assign_geo_bucket("Barcelona") == "spain_latam"


def test_mexico_is_latam():
    assert assign_geo_bucket("Mexico City, Mexico") == "spain_latam"


def test_brazil_is_latam():
    assert assign_geo_bucket("São Paulo, Brazil") == "spain_latam"


def test_australia_bucket():
    assert assign_geo_bucket("Sydney, Australia") == "australia"


def test_melbourne_is_australia():
    assert assign_geo_bucket("Melbourne") == "australia"


def test_other_bucket():
    assert assign_geo_bucket("New York, NY") == "other"


def test_salary_below_general_minimum_caps_geography_fit():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="remote", salary_str="€100,000", thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 2
    assert "below" in flags.lower()


def test_salary_below_australia_minimum():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="australia", salary_str="€150,000", thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 2
    assert "below" in flags.lower()


def test_salary_above_threshold_unchanged():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="remote", salary_str="€140,000", thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 8
    assert flags == ""


def test_salary_unlisted_adds_flag_no_penalty():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="remote", salary_str=None, thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 8
    assert "confirm" in flags.lower()
