# Railway Deployment Steps

## 1. Before Deploying

**Generate your SECRET_KEY** (run this in terminal):
```bash
openssl rand -hex 32
```
Copy the output - you'll need it for the environment variables.

## 2. Update These Values in RAILWAY_ENV_VARS.txt

1. Replace `your_actual_gemini_api_key_here` with your Gemini API key
2. Replace `change_this_to_your_generated_32_byte_hex_secret` with the secret key you generated
3. Replace `your-frontend-domain.com` with your actual frontend domain
4. Replace `your-railway-app.up.railway.app` with your Railway app URL (you'll get this after first deploy)

## 3. Deploy to Railway

1. Push code to GitHub
2. Create new project in Railway from your GitHub repo
3. Go to Variables tab
4. Click "Raw Editor"
5. Copy ALL content from RAILWAY_ENV_VARS.txt
6. Paste into Raw Editor
7. Save

## 4. After Deployment

**IMPORTANT**: Delete these files immediately:
- `RAILWAY_ENV_VARS.txt` (contains sensitive keys)
- `DEPLOYMENT_STEPS.md` (this file)

## 5. Update ALLOWED_HOSTS

After Railway gives you your URL (like `resume-api.up.railway.app`):
1. Go back to Railway Variables
2. Update `ALLOWED_HOSTS` with your actual Railway URL

## 6. Which App File to Use?

- **For testing**: Use `app.py` (no auth required)
- **For production**: Use `app_secure.py` (requires auth)

To switch to secure version, update your Dockerfile:
```dockerfile
# Change the last line from:
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

# To:
CMD ["gunicorn", "app_secure:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

## 7. Test Your Deployment

```bash
curl https://your-railway-app.up.railway.app/health
```

Should return: `{"status":"healthy","version":"1.0.0"}`

## 8. Frontend Testing

If using `app_secure.py`, test auth first:
```bash
curl -X POST https://your-railway-app.up.railway.app/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-123"}'
```

---

**DELETE THIS FILE AND RAILWAY_ENV_VARS.txt AFTER DEPLOYMENT!**