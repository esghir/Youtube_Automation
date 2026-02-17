import sys
try:
    import customtkinter
    print("customtkinter imported successfully")
    import google.generativeai
    print("google.generativeai imported successfully")
    import PIL
    print("PIL imported successfully")
    import google.oauth2
    print("google.oauth2 imported successfully")
    import googleapiclient
    print("googleapiclient imported successfully")
    import requests
    print("requests imported successfully")
    print("All critical dependencies imported successfully!")
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)
