# Sharing the traveler dashboard

## Run it locally

From the repository root (`project/`):

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The `http://localhost:8501` address works only on the computer running Streamlit.
For a quick in-person demo on the same Wi-Fi, start Streamlit with
`--server.address 0.0.0.0` and share that computer's local network address and
port 8501. The other people must be on the same network, and the dashboard must
stay running.

## Get a link that groupmates can open remotely

Deploy the app from GitHub with [Streamlit Community Cloud](https://share.streamlit.io/):

1. Push the dashboard files to the GitHub branch you want to deploy.
2. Sign in at Streamlit Community Cloud with GitHub and create an app.
3. Select repository `cynthiaqgao/project`, branch `Kyi-branch`, and entrypoint
   `app.py` (or choose the branch you merged the dashboard into).
4. Deploy, then copy the generated `*.streamlit.app` URL and share it.

The Phase 3 assignment requires that the instructor can open the app **without
signing in**. After deploying, set the app's sharing to public in Streamlit
Community Cloud (the GitHub repository itself can stay private), then open the
URL in an incognito window with your local server stopped to confirm it loads.

The repository is currently private. Anyone who needs to maintain or deploy the
app needs access to the GitHub repository. Set viewer access for groupmates in
the deployed app's sharing settings if you want to keep the app private; make it
public only if anyone with the link should be able to open it. Check the
repository and app visibility settings before sharing.

The app reads `phase2/outputs/listings.csv`, which is committed with the
dashboard so deployment has its data. The snapshot's collection date is unknown;
it is not a live Airbnb search or booking quote.
