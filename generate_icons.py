import os
from PIL import Image

base_dir = r"c:\Users\dell\Downloads\Medical Job Portal\Medical Job Portal\medical_job_portal"
logo_path = os.path.join(base_dir, "users", "static", "users", "images", "Black_and_White_Circular_Art___Design_Logo-removebg-preview.png")

if os.path.exists(logo_path):
    img = Image.open(logo_path)
    
    # 192x192
    img_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
    img_192.save(os.path.join(base_dir, "users", "static", "users", "images", "icon-192x192.png"))
    
    # 512x512
    img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    img_512.save(os.path.join(base_dir, "users", "static", "users", "images", "icon-512x512.png"))
    
    print("Icons generated successfully.")
else:
    print(f"Error: Logo file not found at {logo_path}")
