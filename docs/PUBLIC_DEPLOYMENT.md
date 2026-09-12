# Limited Public OpenAI Deployment

This guide configures live OpenAI analysis in `portfolio_app.py` without making
the separate `web_app.py` deployment public.

## Safety Model

The public live feature is disabled unless all of the following are true:

1. `ENABLE_PUBLIC_OPENAI_ANALYSIS=true` is set only in server-side secrets.
2. Google OpenID Connect is fully configured.
3. The signed-in Google identity includes a verified email claim.
4. The dedicated Supabase quota service is reachable.
5. A quota attempt is reserved atomically before any OpenAI request.
6. The OpenAI key is available only to the server.

If configuration, authentication, or quota storage fails, the app does not call
OpenAI. The saved fictional report remains available without sign-in.

## Default Limits

| Limit | Default |
|---|---:|
| Attempts per verified account | 3 total |
| Shared attempts | 10 per UTC day |
| Public demonstration allowance | 100 total |
| Resume length | 8,000 characters |
| Job-description length | 8,000 characters |
| Generation output | 3,000 tokens |
| Agent turns | 1 |

Attempts are reserved before an API request and remain counted when later
processing fails. This prevents repeated provider or validation failures from
bypassing the financial limits.

## 1. Prepare the Dedicated Quota Database

Create a dedicated Supabase project containing no unrelated or private data.
In its SQL editor, run the complete contents of:

```text
database/quota_schema.sql
```

The script:

- Creates separate per-account, daily, and overall counters
- Enables Row Level Security on every table
- Removes access for public and signed-in database roles
- Exposes only two server-authorized functions
- Uses row locks so concurrent submissions cannot exceed a limit

From the Supabase dashboard, privately record:

- The project URL, which ends in `.supabase.co`
- A current server-only secret key beginning with `sb_secret_`

Do not use a publishable key, do not place the secret key in the repository, and
do not paste it into chat, email, logs, or screenshots.

## 2. Configure Google Sign-In

Create a Google OAuth client for a web application. Add these exact authorized
redirect URIs:

```text
http://localhost:8501/oauth2callback
https://ramil-job-match-demo.streamlit.app/oauth2callback
```

During setup, keep the Google OAuth application in testing mode and add only the
owner's Google account as a test user. Record the client ID and client secret
privately.

The app requests only the standard `openid profile email` identity scope. It
does not request access to Google Drive, Gmail, or other Google account data.

## 3. Generate Independent Random Secrets

Run this command twice and save the two outputs privately:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use one output for `cookie_secret` and the other for `USER_HASH_SALT`. Never
reuse the OpenAI, Google, or Supabase credential for either value.

## 4. Prepare Local Secrets

Copy the safe template:

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

Fill the ignored `secrets.toml` file with the real values. For local testing,
set:

```text
redirect_uri = "http://localhost:8501/oauth2callback"
ENABLE_PUBLIC_OPENAI_ANALYSIS = "false"
```

Confirm that Git ignores it:

```bash
git check-ignore -v .streamlit/secrets.toml
```

Never display or commit the completed file.

## 5. Safe Cloud Rollout

Use this order:

1. Deploy the code while `ENABLE_PUBLIC_OPENAI_ANALYSIS` remains `false`.
2. Confirm that the existing three saved-example tabs still work publicly.
3. Add all real values to the public app's Streamlit Community Cloud secrets,
   still with the feature set to `false`.
4. Confirm that the separate OpenAI app remains private.
5. Change only `ENABLE_PUBLIC_OPENAI_ANALYSIS` to `true`.
6. Sign in with the owner's Google test account.
7. Submit empty fields first and verify that validation rejects them without
   consuming an attempt or calling OpenAI.
8. Run one fictional end-to-end analysis. This makes one paid generation call.
9. Verify that the account allowance changes from `3/3` to `2/3`.
10. Verify PDF and Markdown downloads and then inspect OpenAI and Supabase usage.
11. Confirm that the automated limit-denial tests pass before publishing the
    Google OAuth application.

Only after these checks pass should Google sign-in be opened beyond the owner's
test account.

## Stored Data

The quota database stores:

- A salted HMAC-SHA256 value derived from the Google issuer and subject
- Per-account attempt count
- Shared daily attempt count
- Overall public attempt count
- Counter update timestamps

It does not store Google email addresses, names, resumes, job descriptions, or
generated reports. Live documents and reports remain in the active Streamlit
session only. Submitted text is still sent to OpenAI and is subject to OpenAI's
API data-handling terms.

## Emergency Stop

To stop new public OpenAI requests immediately, change this public-app secret:

```text
ENABLE_PUBLIC_OPENAI_ANALYSIS=false
```

Then verify that the live tab disappears while the fictional saved example
remains available. If a credential may have been exposed, revoke and replace
that specific credential after disabling the feature.
