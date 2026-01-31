from purway_geotagger.util.timeparse import parse_csv_timestamp, parse_photo_timestamp_from_name

def test_parse_photo_timestamp():
    dt = parse_photo_timestamp_from_name("20230830_205100")
    assert dt is not None
    assert dt.year == 2023 and dt.month == 8 and dt.day == 30

def test_parse_csv_timestamp():
    dt = parse_csv_timestamp("2023-08-30 20:51:00")
    assert dt.year == 2023 and dt.minute == 51
