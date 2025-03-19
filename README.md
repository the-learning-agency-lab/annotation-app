# annotation-app

Recipes and scripts for running annotation tasks using the Prodigy annotation tool.

## Development

You can use the provided devcontainer files with VS Code, or you can manually set up the environment:

Use `./.env.example` as a template for your .env file and ensure these variables are set.

```{python}
pip install -r requirements.txt
pip install prodigy -f https://${PRODIGY_KEY}@download.prodi.gy
pip ipykernel pandas seaborn sqlalchemy # optional/development dependencies
```

## Deployment

Changes pushed to `main` will automatically trigger a build and re-deploy of the production environment. The production environment is hosted on Render.

Tips:

- Include "[skip render]" in your commit message to skip the automatic deployment.
- Use the `render.yaml` file to configure the deployment settings.
    - You will normally just need to change the `startCommand` to match the command you use to start the app locally.
- prodigy-production.json controls the Prodigy settings for the production environment.
- prodigy-local.json controls the Prodigy settings for the local environment (and will use a local SQLite database instead of the production database)

### Prodigy Start Command

The Prodigy start command is the command used to start the Prodigy server. It has th following form:

`prodigy [recipe_name] [dataset_name] [*recipe_args] -F [path_to_recipe_python_file]`

After testing the command locally, it should be set in the `render.yaml` file as the `startCommand`.

- If a dataset with `dataset_name` does not exist, Prodigy will create it.
- If recipe_name is a custom recipe, you must provide the path to the Python file containing the recipe with the `-F` flag.