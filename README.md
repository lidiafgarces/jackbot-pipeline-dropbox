# Dropbox Pipeline for Jackbot

This simple pipelines uses webhooks to get notified of new images uploaded to Dropbox. It then creates a new task and add it to Jackbot Platform.

This code is based on the 'Dropbox Webhooks' example provided in [dropbox/mdwebhook](https://github.com/dropbox/mdwebhook). Read more about webhooks and this example on [the Dropbox developers site](https://www.dropbox.com/developers/webhooks/tutorial).

## Running the sample yourself

This sample was built with Heroku in mind as a target, so the simplest way to run the sample is via `foreman`:

1. Copy `.env_sample` to `.env` and fill in the values.
2. Run `pip install -r requirements.txt` to install the necessary modules.
3. Launch the app via `foreman start` or deploy to Heroku.

You can also just set the required environment variables (using `.env_sample` as a guide) and run the app directly with `python app.py`.

Take into account that Dropbox's webhooks can't communicate with 'localhost'.

## Deploy on Heroku

You can deploy directly to Heroku with the button below. First you'll need to create an API app via the [App Console](https://www.dropbox.com/developers/apps). Make sure your app has access to files (not just datastores), and answer "Yes - My app only needs access to files it creates" to ensure your app gets created with "App folder" permissions.

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)
