# Fixing Sheet Data Alignment

## Problem
If your Google Sheet has data in the wrong columns (mismatched rows/columns), this guide will help you fix it.

## Solution

The code has been updated to:
1. **Automatically create headers** in row 1 if they don't exist
2. **Ensure data is aligned** with headers (21 columns: A through U)
3. **Append data correctly** after the last row

## Steps to Fix Your Existing Sheet

### Option 1: Clear and Start Fresh (Recommended)

1. **Backup your existing data** (if needed):
   - Open your Google Sheet
   - File → Download → CSV
   - Save it locally

2. **Clear the sheet**:
   - Select all cells (Ctrl+A or Cmd+A)
   - Delete all content
   - Or create a new sheet tab

3. **Run the bot again**:
   - The bot will automatically create headers in row 1
   - New data will be properly aligned

### Option 2: Manual Fix

1. **Delete existing misaligned data**:
   - Select rows with misaligned data
   - Right-click → Delete rows

2. **Ensure row 1 has headers**:
   - Row 1 should have these headers (in order):
     - Index, Timestamp, Reel Link, Item Index, Item Type, Item Name, Brand/Category, City, State, Country, Lat, Lng, Distance_km, Price, Price_Source, Purchase_Link, Key_Specs/Features, Best_Time/Notes, Confidence, Source_Text, Processing_Status

3. **Run the bot**:
   - New data will be appended correctly below existing data

### Option 3: Use a New Sheet Tab

1. **Create a new sheet tab** in your Google Sheet:
   - Click the "+" button at the bottom
   - Name it "Sheet1" (or update your code to use a different name)

2. **Run the bot**:
   - Data will be written to the new clean sheet

## Verification

After running the bot, verify:
1. **Row 1** has headers (Index, Timestamp, Reel Link, etc.)
2. **Row 2+** have data aligned with headers:
   - Column A: Index (numbers: 1, 2, 3...)
   - Column B: Timestamp
   - Column C: Reel Link (URL)
   - Column D: Item Index
   - Column E: Item Type
   - etc.

## Expected Sheet Structure

```
Row 1 (Headers):
A: Index | B: Timestamp | C: Reel Link | D: Item Index | E: Item Type | F: Item Name | ... (through U)

Row 2 (Data):
A: 1 | B: 2025-11-09T... | C: https://instagram.com/reel/... | D: 1 | E: other | F: item name | ...

Row 3 (Data):
A: 2 | B: 2025-11-09T... | C: https://instagram.com/reel/... | D: 1 | E: place | F: Location name | ...
```

## After Fix

Once your sheet is fixed:
- All new data will be properly aligned
- Headers are automatically created if missing
- Data is appended row by row in the correct columns
- Index numbers are sequential (1, 2, 3...)

## Notes

- The bot automatically creates headers if they don't exist
- Data is always written to columns A through U (21 columns total)
- Each row represents one extracted item from a reel
- Multiple items from the same reel will be on separate rows

