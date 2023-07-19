from src.app import app

if __name__ == "__main__":
    import sys 
    if "log" in sys.argv:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    debug = "debug" in sys.argv
    app.run(debug=debug)
