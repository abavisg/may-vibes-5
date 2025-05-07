try:
    from poller.data_providers import twelvedata, finnhub
    from poller.parsers import twelvedata as twelvedata_parser, finnhub as finnhub_parser
    print("Import succeeded")
    print(f"twelvedata: {twelvedata}")
    print(f"finnhub: {finnhub}")
    print(f"twelvedata_parser: {twelvedata_parser}")
    print(f"finnhub_parser: {finnhub_parser}")
except Exception as e:
    print(f"Import failed: {e}") 