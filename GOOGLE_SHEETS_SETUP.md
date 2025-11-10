# Google Sheets Setup Guide

## Fixing "403 Permission Denied" Error

When you see this error:
```
Permission denied: Service account 'your-service-account@project.iam.gserviceaccount.com' does not have write access to the Google Sheet.
```

### Step 1: Find Your Service Account Email

1. Open your service account JSON file (e.g., `reelscout-477109-ea10a708a641.json`)
2. Look for the `client_email` field
3. Copy the email address (it looks like: `something@project-id.iam.gserviceaccount.com`)

### Step 2: Share Your Google Sheet

1. Open your Google Sheet:
   - URL format: `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID`
   - Or find it in your Google Drive

2. Click the **"Share"** button (top right corner)

3. In the "Add people and groups" field, paste your service account email

4. Set the permission to **"Editor"** (not Viewer or Commenter)

5. **Uncheck** "Notify people" (service accounts don't have email)

6. Click **"Share"**

### Step 3: Verify

1. You should see the service account email in the sharing list
2. Restart your Docker container
3. Try sending a reel link again

### Common Issues

**Q: I can't find the service account email in my JSON file**
- Make sure you're using the correct JSON file
- The email is in the `client_email` field

**Q: The service account email doesn't appear when I type it**
- This is normal - service accounts don't appear in autocomplete
- Just paste the full email and click Share

**Q: I still get permission errors**
- Make sure the sheet ID in your `.env` file is correct
- Make sure you shared the correct sheet (check the Sheet ID)
- Make sure the service account has "Editor" permissions (not Viewer)

## Getting Your Sheet ID

1. Open your Google Sheet in a browser
2. Look at the URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
3. Copy the part between `/d/` and `/edit`
4. This is your `GOOGLE_SHEET_ID` for the `.env` file

## Testing

After sharing the sheet, you can test by:
1. Restarting the Docker container
2. Sending a reel link to your Telegram bot
3. The bot should now successfully append data to your sheet

## Backup

Even if Google Sheets fails, the system automatically creates a local backup CSV file at:
- Docker: `/tmp/ai_agent/backup.csv`
- You can download it using the `/download` command in Telegram

