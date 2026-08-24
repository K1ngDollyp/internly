import os
import urllib.request
import urllib.error
from app.core.config import settings

def upload_file_to_storage(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream", bucket: str = "evidence-files") -> str:
    """
    Uploads a file to Supabase Storage if SUPABASE_URL and SUPABASE_KEY are configured,
    otherwise saves to local/tmp upload directory.
    Returns the file URL (either public Supabase URL or local relative path).
    """
    supabase_url = getattr(settings, "SUPABASE_URL", None) or os.environ.get("SUPABASE_URL")
    supabase_key = getattr(settings, "SUPABASE_KEY", None) or os.environ.get("SUPABASE_KEY")

    if supabase_url and supabase_key:
        try:
            url = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{filename}"
            req = urllib.request.Request(url, data=file_bytes, method="POST")
            req.add_header("Authorization", f"Bearer {supabase_key}")
            req.add_header("apiKey", supabase_key)
            if content_type:
                req.add_header("Content-Type", content_type)

            with urllib.request.urlopen(req) as response:
                if response.status in (200, 201):
                    return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{filename}"
        except Exception as e:
            print(f"Supabase Storage upload warning, falling back to local storage: {e}")

    # Fallback to local storage
    upload_dir = "/tmp/uploads" if (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) else "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    dest_path = os.path.join(upload_dir, filename)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return f"/uploads/{filename}"
