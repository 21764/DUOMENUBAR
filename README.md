# Duo Mobile Menu Bar App

A macOS menu bar application that displays TOTP (Time-based One-Time Password) codes from Duo Mobile running in PlayCover. Access your Duo authentication codes directly from your menu bar without needing to keep the Duo app open.

![macOS](https://img.shields.io/badge/macOS-12.0%2B-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-green)
![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-Required-orange)

## Features

- **Menu Bar Integration**: Displays Duo TOTP codes directly in the macOS menu bar
- **One-Click Copy**: Click any code to copy it to your clipboard
- **Auto-Refresh**: Codes automatically refresh every 30 seconds with countdown timer
- **Auto-Launch**: Automatically opens Duo Mobile via PlayCover on startup to populate the database
- **Auto-Close**: Closes Duo and PlayCover after retrieving codes (they're not needed once database is populated)
- **No Dock Icon**: Runs as a menu bar-only app without cluttering your dock
- **Native Notifications**: Get notified when a code is copied to clipboard

## Requirements

### Hardware
- Mac with Apple Silicon (M1/M2/M3)

### Software
- macOS 12.0 (Monterey) or later
- [PlayCover](https://playcover.io/) - For running iOS apps on macOS
- Duo Mobile IPA (decrypted) installed in PlayCover
- Python 3.9+
- [cliclick](https://github.com/BlueM/cliclick) - Command-line mouse control tool

### Python Dependencies
- `rumps` - macOS menu bar app framework
- `pyobjc-framework-Cocoa` - For hiding dock icon (usually included with rumps)

## Installation

### 1. Install PlayCover
Download and install PlayCover from [playcover.io](https://playcover.io/)

### 2. Install Duo Mobile in PlayCover
- Obtain a decrypted Duo Mobile IPA file
- Import it into PlayCover
- Enable **PlayChain** in PlayCover settings (required for keychain/database access)
- Launch Duo Mobile once and set up your accounts

### 3. Install cliclick
```bash
brew install cliclick
```

### 4. Install Python Dependencies
```bash
pip3 install rumps
```

### 5. Clone or Download This Repository
```bash
git clone https://github.com/21764/DUOMENUBAR.git
cd DUOMENUBAR
```

### 6. Grant Accessibility Permissions
The app needs accessibility permissions to control PlayCover:
1. Go to **System Settings** > **Privacy & Security** > **Accessibility**
2. Add Terminal (or your terminal app) to the allowed list
3. If running from an IDE, add that IDE as well

## Usage

### Running the App
```bash
python3 duo_menubar.py
```

Or double-click `start_duo_menubar.command` in Finder.

### Menu Bar Interface
- Click the Duo icon in your menu bar to see your TOTP codes
- Click any code to copy it to your clipboard
- The countdown timer shows when codes will refresh
- **Open PlayCover**: Manually open Duo in PlayCover
- **Refresh Accounts**: Re-read accounts from the database
- **Quit**: Exit the application

## How It Works

1. **Startup**: The app checks if Duo Mobile is running in PlayCover
2. **Auto-Launch**: If not running, it opens PlayCover and launches Duo Mobile using UI automation (AppleScript + cliclick)
3. **Database Read**: Reads TOTP secrets from PlayCover's encrypted keychain database (`PlayChain`)
4. **Auto-Close**: Once accounts are retrieved, Duo and PlayCover are closed automatically
5. **Code Generation**: Generates TOTP codes using the standard RFC 6238 algorithm
6. **Display**: Shows codes in the menu bar, refreshing every second

### Database Location
```
~/Library/Containers/io.playcover.PlayCover/PlayChain/com.duosecurity.DuoMobile.db
```

## Configuration

### Icon
The app uses `duo_icon_v3.png` as the menu bar icon. You can replace this with your own icon (recommended size: 18x22 pixels for standard, 36x44 for retina).

### PlayChain
**Important**: PlayChain must be enabled in PlayCover for the app to read the Duo database. Without PlayChain, the keychain data is not persisted.

## Troubleshooting

### "No Accounts Found"
- Ensure PlayChain is enabled in PlayCover
- Launch Duo Mobile manually from PlayCover at least once
- Click "Refresh Accounts" in the menu bar app

### Duo Says "Account Disabled"
- Duo Mobile must be launched from within PlayCover, not directly
- The app handles this automatically via UI automation

### Accessibility Permission Denied
- Grant accessibility permissions to Terminal/your IDE in System Settings
- Restart the app after granting permissions

### cliclick Not Found
```bash
brew install cliclick
```

### Codes Don't Match Duo App
- The app uses the "Raw/6" TOTP method (UTF-8 encoded secret)
- This matches Duo Mobile's implementation

## File Structure

```
DuoMenuBar/
├── duo_menubar.py          # Main application
├── start_duo_menubar.command  # Shell launcher script
├── duo_icon_v3.png         # Menu bar icon
├── duo-mobile.png          # Original icon source
├── README.md               # This file
└── .gitignore
```

## Security Notes

- TOTP secrets are stored in PlayCover's encrypted PlayChain database
- The app reads secrets locally and generates codes offline
- No network requests are made by this app
- Codes are only copied to clipboard when you click them

## Terminal Mode

If `rumps` is not installed, the app falls back to terminal mode:
```bash
python3 duo_menubar.py
```
This displays codes in the terminal with auto-refresh.

## License

MIT License - Feel free to modify and distribute.

## Acknowledgments

- [PlayCover](https://playcover.io/) - For making iOS apps run on macOS
- [rumps](https://github.com/jaredks/rumps) - Ridiculously Uncomplicated macOS Python Statusbar apps
- [cliclick](https://github.com/BlueM/cliclick) - Command-line mouse control
