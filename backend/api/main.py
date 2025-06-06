from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import instaloader
import os
import shutil
import uuid
import yt_dlp

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to clear the user's folder if it already exists
def clear_user_folder(username: str):
    folder_path = os.path.join(os.getcwd(), username)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    return folder_path



def save_instagram_cookies(username, password, cookie_file='cookies.txt'):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Go to login page
        page.goto("https://www.instagram.com/accounts/login/")
        page.wait_for_selector("input[name='username']", timeout=15000)

        # Fill in credentials
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")

        # Wait for navigation (after successful login)
        page.wait_for_timeout(10000)  # Allow time for login processing
        if "challenge" in page.url:
            raise Exception("2FA or challenge required. Cannot proceed automatically.")
        elif "accounts/onetap" in page.url:
            page.goto("https://www.instagram.com/")
            page.wait_for_timeout(3000)

        # Validate login by checking redirect to main page
        if not page.url.startswith("https://www.instagram.com/"):
            raise Exception("Login failed. Please check credentials.")

        # Save cookies in Netscape format
        cookies = context.cookies()
        with open(cookie_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for c in cookies:
                domain = c['domain']
                flag = "TRUE"
                path = c['path']
                secure = "TRUE" if c.get('secure') else "FALSE"
                expiry = str(int(c.get('expires', 0)))
                name = c['name']
                value = c['value']
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")

        browser.close()

@app.get("/")
async def root():
    return JSONResponse({"message": "Welcome to the Instagram Downloader API!"})

@app.post("/download-dp")
async def download_instagram_dp(username: str = Form(...)):
    loader = instaloader.Instaloader()
    folder_path = clear_user_folder(username)
    try:
        loader.download_profile(username, profile_pic_only=True)

        for file in os.listdir(folder_path):
            if file.endswith(".jpg"):
                return FileResponse(
                    path=os.path.join(folder_path, file),
                    filename=f"{username}_dp.jpg",
                    media_type='image/jpeg'
                )
        return JSONResponse({"error": "Profile picture not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/download-reel")
async def download_reel(url: str = Form(...)):

    try:
        # Create a temporary file path
        video_id = str(uuid.uuid4())
        output_path = f"{video_id}.mp4"

        # Download options
        ydl_opts = {
        'outtmpl': output_path,
        'format': 'mp4',
    }


        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return FileResponse(
            path=output_path,
            filename="instagram_reel.mp4",
            media_type='video/mp4',
            background=True  # Optional: auto delete if using tmp folder
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
    
# 👇 Add this to support dynamic port binding for deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Use PORT env var or default to 8000
    uvicorn.run("main:app", host="0.0.0.0", port=port)