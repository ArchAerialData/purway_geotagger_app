# Apple Developer Signing & Notarization Setup (Purway Geotagger)

This guide lists the exact credentials needed for macOS code signing and notarization, plus which computer is required for each step.

## What you need
- Apple Developer Program membership with **Account Holder** access.
- Team ID (10-character string).
- Developer ID Application certificate **and** private key (`.p12`).
- App Store Connect API key (`.p8`) + Key ID + Issuer ID (**Team** key; recommended for CI).
- A **Mac** for creating the CSR and exporting the `.p12` (Keychain Access is macOS-only).

## Step 1 — Find Team ID (any computer + browser)
1. Open `https://developer.apple.com/account/`
2. Sign in.
3. Open **Membership details** and copy the Team ID.

## Step 2 — Create a CSR (Mac required)
1. Open **Keychain Access** (`/Applications/Utilities`).
2. Choose **Keychain Access > Certificate Assistant > Request a Certificate from a Certificate Authority**.
3. Enter your email + Common Name, leave the CA Email Address blank.
4. Choose **Saved to disk**, then save the `.certSigningRequest`.

## Step 3 — Create a Developer ID Application certificate (any computer + browser; Account Holder)
1. Open `https://developer.apple.com/account/`
2. Go to **Certificates, Identifiers & Profiles > Certificates**.
3. Click **+** and select **Developer ID > Developer ID Application**.
4. Upload the CSR and download the `.cer`.

## Step 4 — Install the cert and export `.p12` (Mac required)
1. Double-click the `.cer` to install in Keychain.
2. In **Keychain Access > My Certificates**, select the Developer ID Application cert (with its private key).
3. **File > Export Items…** and choose `.p12`.
4. Set a strong export password and store it safely.

## Step 5 — Request App Store Connect API access (any computer + browser; Account Holder)
1. Open `https://appstoreconnect.apple.com/` and sign in.
2. Request access to the App Store Connect API (Account Holder required).
3. After access is granted, open **Users and Access > Integrations > App Store Connect API**, then select **Team Keys**.

## Step 6 — Create App Store Connect API key (any computer + browser)
1. In the **Keys** tab, click **+ / Generate API Key**.
2. Choose an **Access** role (this scopes what the key can do via the API).
3. Download the `.p8` file (one-time download).
4. Record the **Key ID** and **Issuer ID** shown in the UI.

## Step 7 — Provide secrets to GitHub Actions
- `MACOS_CERT_P12` (base64 of `.p12`)
- `MACOS_CERT_PASSWORD`
- `APPLE_KEY_ID`
- `APPLE_ISSUER_ID`
- `APPLE_API_KEY_P8` (base64 of `.p8`)

## Notes
- This repo's CI notarization flow uses `xcrun notarytool` with an App Store Connect API **Team** key and passes `--issuer`.
- The app must be **Developer ID signed** before notarization will succeed.

## References (Apple docs)
- Team ID: `https://developer.apple.com/help/glossary/team-id/`
- CSR creation: `https://developer.apple.com/help/account/create-certificates/create-a-certificate-signing-request`
- Developer ID certificates: `https://developer.apple.com/help/account/certificates/create-developer-id-certificates`
- App Store Connect API access: `https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api/`
- App Store Connect API key creation (Team Keys): `https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api/`
- Developer ID signing + notarization overview: `https://developer.apple.com/developer-id/`
