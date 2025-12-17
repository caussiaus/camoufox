from camoufox.sync_api import Camoufox

print("Starting Camoufox...")

with Camoufox(headless=False, geoip=True) as browser:
    page = browser.new_page()
    print("Opening Wikipedia...")
    page.goto('https://wikipedia.com')
    
    title = page.title()
    print(f"Page title: {title}")
    
    # Wait so you can see it in VNC
    import time
    time.sleep(10)
    
print("Done!")
